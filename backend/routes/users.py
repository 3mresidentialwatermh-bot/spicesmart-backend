from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User

users_bp = Blueprint('users', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

def require_admin():
    u = current_user()
    if not u or u.role != 'admin':
        return None, jsonify({'error': 'Admin access required'}), 403
    return u, None, None

@users_bp.route('/', methods=['GET'])
@jwt_required()
def list_users():
    u = current_user()
    if u.role == 'admin':
        users = User.query.all()
    elif u.role == 'distributor':
        # distributor sees their retailer children
        users = User.query.filter_by(parent_id=u.id).all()
    else:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'users': [x.to_dict() for x in users]})

@users_bp.route('/hierarchy', methods=['GET'])
@jwt_required()
def get_hierarchy():
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    def build_tree(user):
        return {
            **user.to_dict(),
            'children': [build_tree(c) for c in user.children]
        }

    admins = User.query.filter_by(role='admin').all()
    return jsonify({'hierarchy': [build_tree(a) for a in admins]})

@users_bp.route('/', methods=['POST'])
@jwt_required()
def create_user():
    u = current_user()
    if u.role not in ('admin', 'distributor'):
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    role = data.get('role', 'customer')

    # Distributors can only create retailers/customers
    if u.role == 'distributor' and role not in ('retailer', 'customer'):
        return jsonify({'error': 'Distributors can only create retailers or customers'}), 400

    if User.query.filter_by(email=data['email'].lower()).first():
        return jsonify({'error': 'Email already registered'}), 409

    new_user = User(
        name=data['name'],
        email=data['email'].strip().lower(),
        phone=data.get('phone'),
        role=role,
        parent_id=data.get('parent_id') or (u.id if u.role != 'admin' else None),
        address=data.get('address'),
    )
    new_user.set_password(data.get('password', 'spices@123'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'user': new_user.to_dict()}), 201

@users_bp.route('/<int:uid>', methods=['PUT'])
@jwt_required()
def update_user(uid):
    u = current_user()
    target = User.query.get_or_404(uid)

    # Allow user to edit themselves, or admin to edit anyone
    if u.id != uid and u.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    for field in ('name', 'phone', 'address'):
        if field in data:
            setattr(target, field, data[field])

    if 'role' in data and u.role == 'admin':
        target.role = data['role']
    if 'is_active' in data and u.role == 'admin':
        target.is_active = data['is_active']
    if 'parent_id' in data and u.role == 'admin':
        target.parent_id = data['parent_id']
    if data.get('password') and u.role == 'admin':
        target.set_password(data['password'])

    db.session.commit()
    return jsonify({'user': target.to_dict()})

@users_bp.route('/<int:uid>', methods=['DELETE'])
@jwt_required()
def delete_user(uid):
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    target = User.query.get_or_404(uid)
    target.is_active = False
    db.session.commit()
    return jsonify({'message': 'User deactivated'})

@users_bp.route('/distributors', methods=['GET'])
@jwt_required()
def get_distributors():
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    distributors = User.query.filter_by(role='distributor', is_active=True).all()
    return jsonify({'distributors': [d.to_dict() for d in distributors]})
