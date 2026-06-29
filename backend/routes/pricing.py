from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, PriceTier, Product, User
import csv, io


pricing_bp = Blueprint('pricing', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

@pricing_bp.route('/', methods=['GET'])
@jwt_required()
def list_prices():
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    tiers = PriceTier.query.all()
    return jsonify({'prices': [t.to_dict() for t in tiers]})

@pricing_bp.route('/', methods=['POST'])
@jwt_required()
def set_price():
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    product_id = data['product_id']
    role       = data['role']
    price      = data['price']

    pt = PriceTier.query.filter_by(product_id=product_id, role=role).first()
    if pt:
        pt.price = price
    else:
        pt = PriceTier(product_id=product_id, role=role, price=price)
        db.session.add(pt)

    db.session.commit()
    return jsonify({'price': pt.to_dict()})

@pricing_bp.route('/bulk', methods=['POST'])
@jwt_required()
def bulk_set_prices():
    """Set all prices for multiple products at once from the pricing matrix."""
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    # data = [{"product_id": 1, "role": "retailer", "price": 150}, ...]
    for item in data:
        pt = PriceTier.query.filter_by(
            product_id=item['product_id'], role=item['role']
        ).first()
        if pt:
            pt.price = item['price']
        else:
            db.session.add(PriceTier(
                product_id=item['product_id'],
                role=item['role'],
                price=item['price']
            ))
    db.session.commit()
    return jsonify({'message': 'Prices updated'})


# ── BULK CSV PRICING UPLOAD ─────────────────────────────────────────────────
@pricing_bp.route('/upload-csv', methods=['POST'])
@jwt_required()
def upload_pricing_csv():
    """
    Update prices from a CSV file.
    Expected columns: name_or_sku, distributor_price, retailer_price, customer_price
    Matches products by SKU first, then by name.
    """
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file   = request.files['file']
    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream)

    updated, errors = [], []

    for i, row in enumerate(reader, start=2):
        identifier = (
            row.get('sku') or row.get('SKU') or
            row.get('name') or row.get('Name') or ''
        ).strip()

        if not identifier:
            errors.append({'row': i, 'error': 'No product name or SKU'})
            continue

        try:
            dist_price = float(row.get('distributor_price') or row.get('Distributor Price') or 0)
            ret_price  = float(row.get('retailer_price')    or row.get('Retailer Price')    or 0)
            cust_price = float(row.get('customer_price')    or row.get('Customer Price')    or 0)
        except ValueError as e:
            errors.append({'row': i, 'error': str(e)})
            continue

        # Find product
        product = Product.query.filter_by(sku=identifier).first()
        if not product:
            product = Product.query.filter(Product.name.ilike(f'%{identifier}%')).first()
        if not product:
            errors.append({'row': i, 'error': f'Product not found: {identifier}'})
            continue

        for role, price_val in [('distributor', dist_price), ('retailer', ret_price), ('customer', cust_price)]:
            if price_val > 0:
                pt = PriceTier.query.filter_by(product_id=product.id, role=role).first()
                if pt:
                    pt.price = price_val
                else:
                    db.session.add(PriceTier(product_id=product.id, role=role, price=price_val))

        updated.append(product.name)

    db.session.commit()
    return jsonify({
        'success': True,
        'updated': len(updated),
        'errors':  len(errors),
        'updated_products': updated,
        'error_details': errors,
    })


@pricing_bp.route('/sample-csv', methods=['GET'])
def pricing_sample_csv():
    """Download a sample pricing CSV template (no auth needed — public template)."""
    products = Product.query.filter_by(is_active=True).all()
    output   = io.StringIO()
    writer   = csv.writer(output)
    writer.writerow(['name', 'sku', 'distributor_price', 'retailer_price', 'customer_price'])
    for p in products:
        prices = {pt.role: pt.price for pt in p.prices}
        writer.writerow([
            p.name, p.sku or '',
            prices.get('distributor', 0),
            prices.get('retailer', 0),
            prices.get('customer', 0),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=pricing_template.csv'}
    )

