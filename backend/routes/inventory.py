from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Inventory, User, Product

inventory_bp = Blueprint('inventory', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

@inventory_bp.route('/', methods=['GET'])
@jwt_required()
def list_inventory():
    u = current_user()

    if u.role == 'admin':
        items = Inventory.query.all()
    else:
        items = Inventory.query.filter_by(owner_id=u.id).all()

    return jsonify({'inventory': [i.to_dict() for i in items]})

@inventory_bp.route('/alerts', methods=['GET'])
@jwt_required()
def low_stock_alerts():
    u = current_user()

    if u.role == 'admin':
        items = Inventory.query.all()
    else:
        items = Inventory.query.filter_by(owner_id=u.id).all()

    low = [i.to_dict() for i in items if i.quantity <= i.low_stock_threshold]
    return jsonify({'alerts': low, 'count': len(low)})

@inventory_bp.route('/adjust', methods=['POST'])
@jwt_required()
def adjust_stock():
    """Admin manually adjusts stock level for any owner."""
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    product_id = data['product_id']
    owner_id   = data.get('owner_id', u.id)
    qty        = data['quantity']          # can be negative to reduce
    threshold  = data.get('low_stock_threshold')

    inv = Inventory.query.filter_by(product_id=product_id, owner_id=owner_id).first()
    if not inv:
        inv = Inventory(product_id=product_id, owner_id=owner_id, quantity=0)
        db.session.add(inv)

    inv.quantity = max(0, inv.quantity + qty)
    if threshold is not None:
        inv.low_stock_threshold = threshold

    db.session.commit()
    return jsonify({'inventory': inv.to_dict()})

@inventory_bp.route('/set', methods=['POST'])
@jwt_required()
def set_stock():
    """Admin sets absolute stock level."""
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    product_id = data['product_id']
    owner_id   = data.get('owner_id', u.id)
    qty        = data['quantity']

    inv = Inventory.query.filter_by(product_id=product_id, owner_id=owner_id).first()
    if not inv:
        inv = Inventory(product_id=product_id, owner_id=owner_id, quantity=0)
        db.session.add(inv)

    inv.quantity = max(0, qty)
    db.session.commit()
    return jsonify({'inventory': inv.to_dict()})

@inventory_bp.route('/summary', methods=['GET'])
@jwt_required()
def inventory_summary():
    u = current_user()
    if u.role == 'admin':
        total_products = Product.query.filter_by(is_active=True).count()
        low_stock_count = sum(
            1 for i in Inventory.query.all() if i.quantity <= i.low_stock_threshold
        )
        total_stock = db.session.query(db.func.sum(Inventory.quantity)).scalar() or 0
    else:
        inv = Inventory.query.filter_by(owner_id=u.id).all()
        total_products  = len(inv)
        low_stock_count = sum(1 for i in inv if i.quantity <= i.low_stock_threshold)
        total_stock     = sum(i.quantity for i in inv)

    return jsonify({
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'total_stock': total_stock,
    })
