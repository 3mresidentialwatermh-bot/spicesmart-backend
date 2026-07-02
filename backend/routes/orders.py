from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Order, OrderItem, Product, Inventory, User
from email_utils import send_order_confirmation

orders_bp = Blueprint('orders', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

# ── Order routing: find who the buyer should buy from ──────────────────────────
def resolve_seller(buyer: User):
    """
    Hierarchy for customer:
      1. Retailer in same pincode
      2. Distributor in same pincode
      3. Original parent (usually admin)
      4. Admin fallback
    """
    if buyer.role == 'customer':
        if buyer.pincode:
            retailer = User.query.filter_by(role='retailer', pincode=buyer.pincode, is_active=True).first()
            if retailer:
                return retailer
            
            distributor = User.query.filter_by(role='distributor', pincode=buyer.pincode, is_active=True).first()
            if distributor:
                return distributor
                
        if buyer.parent_id:
            parent = User.query.get(buyer.parent_id)
            if parent:
                return parent
                
        return User.query.filter_by(role='admin').first()

    elif buyer.role == 'retailer':
        return User.query.get(buyer.parent_id)
    elif buyer.role == 'distributor':
        return User.query.filter_by(role='admin').first()
    return None


def get_stock(product_id, owner_id):
    inv = Inventory.query.filter_by(product_id=product_id, owner_id=owner_id).first()
    return inv


def deduct_stock(product_id, owner_id, qty):
    inv = get_stock(product_id, owner_id)
    if not inv or inv.quantity < qty:
        return False, f"Insufficient stock for product {product_id}"
    inv.quantity -= qty
    return True, None


def add_stock(product_id, owner_id, qty):
    inv = Inventory.query.filter_by(product_id=product_id, owner_id=owner_id).first()
    if not inv:
        inv = Inventory(product_id=product_id, owner_id=owner_id, quantity=0)
        db.session.add(inv)
    inv.quantity += qty


# ── Routes ─────────────────────────────────────────────────────────────────────
@orders_bp.route('/', methods=['POST'])
@jwt_required()
def place_order():
    u    = current_user()
    data = request.get_json()

    seller = resolve_seller(u)
    if not seller:
        return jsonify({'error': 'No supplier found in your hierarchy. Contact admin.'}), 400

    items_data = data.get('items', [])
    if not items_data:
        return jsonify({'error': 'Order must have at least one item'}), 400

    coupon_code = data.get('coupon_code', '').strip().upper()
    discount_amount = 0.0

    total = 0.0
    order_items = []

    for item in items_data:
        product = Product.query.get(item['product_id'])
        if not product or not product.is_active:
            return jsonify({'error': f'Product {item["product_id"]} not found'}), 404

        qty   = int(item['quantity'])
        price = product.get_price_for_role(u.role)

        # Check seller's stock
        ok, err = deduct_stock(product.id, seller.id, qty)
        if not ok:
            db.session.rollback()
            return jsonify({'error': err}), 400

        # Add stock to buyer
        add_stock(product.id, u.id, qty)

        total += price * qty
        order_items.append(OrderItem(
            product_id=product.id,
            quantity=qty,
            unit_price=price,
        ))

    if coupon_code:
        from models import Coupon
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        if coupon:
            discount_amount = total * float(coupon.discount_percent) / 100.0
            total -= discount_amount

    shipping_address = u.address
    shipping_city = u.city
    shipping_state = u.state
    shipping_pincode = u.pincode
    
    address_id = data.get('address_id')
    if address_id:
        from models import Address
        addr = Address.query.filter_by(id=address_id, user_id=u.id).first()
        if addr:
            shipping_address = addr.address
            shipping_city = addr.city
            shipping_state = addr.state
            shipping_pincode = addr.pincode

    order = Order(
        buyer_id=u.id,
        seller_id=seller.id,
        total_amount=total,
        payment_status='paid',   # mock payment
        payment_ref=f'MOCK-{u.id}-{len(order_items)}',
        notes=data.get('notes'),
        status='confirmed',
        coupon_code=coupon_code if discount_amount > 0 else None,
        discount_amount=discount_amount,
        shipping_address=shipping_address,
        shipping_city=shipping_city,
        shipping_state=shipping_state,
        shipping_pincode=shipping_pincode
    )
    db.session.add(order)
    db.session.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.session.add(oi)

    db.session.commit()
    
    try:
        send_order_confirmation(order)
    except Exception as e:
        print(f"Error sending confirmation email: {e}")
        
    return jsonify({'order': order.to_dict()}), 201


@orders_bp.route('/', methods=['GET'])
@jwt_required()
def list_orders():
    u    = current_user()
    mode = request.args.get('mode', 'placed')  # placed | received

    if u.role == 'admin':
        orders = Order.query.order_by(Order.created_at.desc()).all()
    elif mode == 'received':
        orders = Order.query.filter_by(seller_id=u.id).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(buyer_id=u.id).order_by(Order.created_at.desc()).all()

    return jsonify({'orders': [o.to_dict() for o in orders]})


@orders_bp.route('/<int:oid>', methods=['GET'])
@jwt_required()
def get_order(oid):
    u     = current_user()
    order = Order.query.get_or_404(oid)
    if u.role != 'admin' and order.buyer_id != u.id and order.seller_id != u.id:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'order': order.to_dict()})


@orders_bp.route('/<int:oid>/status', methods=['PUT'])
@jwt_required()
def update_status(oid):
    u     = current_user()
    order = Order.query.get_or_404(oid)

    # Only seller or admin can update order status
    if u.role != 'admin' and order.seller_id != u.id:
        return jsonify({'error': 'Access denied'}), 403

    data      = request.get_json()
    new_status = data.get('status')
    valid      = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    if new_status not in valid:
        return jsonify({'error': f'Invalid status. Choose from {valid}'}), 400

    order.status = new_status
    if new_status == 'shipped':
        order.tracking_number = data.get('tracking_number', order.tracking_number)
        order.courier = data.get('courier', order.courier)

    db.session.commit()
    return jsonify({'order': order.to_dict()})


@orders_bp.route('/stats', methods=['GET'])
@jwt_required()
def order_stats():
    u = current_user()

    if u.role == 'admin':
        total_orders  = Order.query.count()
        total_revenue = db.session.query(
            db.func.sum(Order.total_amount)
        ).filter(Order.payment_status == 'paid').scalar() or 0
        pending  = Order.query.filter_by(status='pending').count()
        shipped  = Order.query.filter_by(status='shipped').count()
        delivered = Order.query.filter_by(status='delivered').count()
    else:
        total_orders  = Order.query.filter_by(buyer_id=u.id).count()
        total_revenue = db.session.query(
            db.func.sum(Order.total_amount)
        ).filter_by(buyer_id=u.id, payment_status='paid').scalar() or 0
        pending   = Order.query.filter_by(buyer_id=u.id, status='pending').count()
        shipped   = Order.query.filter_by(buyer_id=u.id, status='shipped').count()
        delivered = Order.query.filter_by(buyer_id=u.id, status='delivered').count()

    return jsonify({
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'pending': pending,
        'shipped': shipped,
        'delivered': delivered,
    })

@orders_bp.route('/<int:oid>/invoice', methods=['GET'])
@jwt_required()
def generate_invoice(oid):
    u = current_user()
    order = Order.query.get_or_404(oid)
    if u.role != 'admin' and order.buyer_id != u.id and order.seller_id != u.id:
        return jsonify({'error': 'Access denied'}), 403

    try:
        from fpdf import FPDF
        from flask import Response
        
        pdf = FPDF()
        pdf.add_page()
        
        import os
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        logo_path = os.path.join(base_dir, '..', 'frontend', 'static', 'icons', 'icon-192x192.png')
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=20)

        pdf.set_font('helvetica', 'B', 16)
        pdf.cell(0, 10, 'INVOICE', align='C', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)
        
        pdf.set_font('helvetica', '', 12)
        pdf.cell(100, 10, f'Order ID: #{order.id}')
        pdf.cell(0, 10, f'Date: {order.created_at.strftime("%Y-%m-%d")}', new_x="LMARGIN", new_y="NEXT")
        pdf.cell(100, 10, f'Status: {order.status.upper()}')
        pdf.cell(0, 10, f'Payment: {order.payment_status.upper()}', new_x="LMARGIN", new_y="NEXT")
        
        seller_gstin = order.seller.gstin if order.seller and order.seller.gstin else 'N/A'
        pdf.cell(100, 10, f'Seller GSTIN: {seller_gstin}', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(0, 10, 'Billed To:', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('helvetica', '', 12)
        
        buyer_name = order.buyer.name if order.buyer else 'Unknown'
        buyer_email = order.buyer.email if order.buyer else 'Unknown'
        buyer_gstin = order.buyer.gstin if order.buyer and order.buyer.gstin else 'N/A'
        
        pdf.cell(0, 10, f'Name: {buyer_name}', new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, f'Email: {buyer_email}', new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 10, f'Buyer GSTIN: {buyer_gstin}', new_x="LMARGIN", new_y="NEXT")
        
        if order.shipping_address:
            addr = order.shipping_address
            if order.shipping_city: addr += f", {order.shipping_city}"
            if order.shipping_state: addr += f", {order.shipping_state}"
            if order.shipping_pincode: addr += f" - {order.shipping_pincode}"
            pdf.cell(0, 10, f'Address: {addr}', new_x="LMARGIN", new_y="NEXT")
        elif order.buyer and order.buyer.address:
            pdf.cell(0, 10, f'Address: {order.buyer.address}', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)
        
        # Table Header
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(80, 10, 'Item', border=1)
        pdf.cell(30, 10, 'Qty', border=1, align='C')
        pdf.cell(40, 10, 'Price', border=1, align='R')
        pdf.cell(40, 10, 'Subtotal', border=1, align='R', new_x="LMARGIN", new_y="NEXT")
        
        # Table Rows
        pdf.set_font('helvetica', '', 12)
        subtotal = 0
        for item in order.items:
            st = float(item.unit_price) * item.quantity
            subtotal += st
            pname = item.product.name if item.product else 'Unknown'
            prod_name = pname[:30] + '...' if len(pname) > 30 else pname
            pdf.cell(80, 10, prod_name, border=1)
            pdf.cell(30, 10, str(item.quantity), border=1, align='C')
            pdf.cell(40, 10, f'Rs. {float(item.unit_price):.2f}', border=1, align='R')
            pdf.cell(40, 10, f'Rs. {st:.2f}', border=1, align='R', new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(5)
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(150, 10, 'Subtotal:', align='R')
        pdf.cell(40, 10, f'Rs. {subtotal:.2f}', align='R', new_x="LMARGIN", new_y="NEXT")
        
        if order.discount_amount and float(order.discount_amount) > 0:
            pdf.set_text_color(0, 150, 0)
            pdf.cell(150, 10, f'Discount ({order.coupon_code}):', align='R')
            pdf.cell(40, 10, f'- Rs. {float(order.discount_amount):.2f}', align='R', new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        
        pdf.cell(150, 10, 'Total Amount:', align='R')
        pdf.cell(40, 10, f'Rs. {float(order.total_amount):.2f}', align='R', new_x="LMARGIN", new_y="NEXT")
        
        if order.tracking_number:
            pdf.ln(10)
            pdf.set_font('helvetica', 'I', 11)
            pdf.cell(0, 10, f'Shipping via {order.courier or "Courier"}: {order.tracking_number}', new_x="LMARGIN", new_y="NEXT")
        
        pdf_content = bytes(pdf.output())
        
        return Response(
            pdf_content,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment;filename=Invoice_{order.id}.pdf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate PDF: {str(e)}'}), 500
