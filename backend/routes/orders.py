from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Order, OrderItem, Product, Inventory, User

orders_bp = Blueprint('orders', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

# ── Order routing: find who the buyer should buy from ──────────────────────────
def resolve_seller(buyer: User):
    """
    Hierarchy:
      customer    → their parent retailer
      retailer    → their parent distributor
      distributor → admin (first admin found)
    """
    if buyer.role == 'customer':
        return User.query.get(buyer.parent_id)
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

    order = Order(
        buyer_id=u.id,
        seller_id=seller.id,
        total_amount=total,
        payment_status='paid',   # mock payment
        payment_ref=f'MOCK-{u.id}-{len(order_items)}',
        notes=data.get('notes'),
        status='confirmed',
    )
    db.session.add(order)
    db.session.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.session.add(oi)

    db.session.commit()
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
