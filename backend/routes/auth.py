from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User

auth_bp = Blueprint('auth', __name__)

def current_user():
    uid = get_jwt_identity()
    return User.query.get(int(uid))

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': token,
        'user': user.to_dict()
    })


@auth_bp.route('/register', methods=['POST'])
def register():
    """Customer self-registration with optional address fields."""
    data  = request.get_json()
    name    = (data.get('name', '') or '').strip()
    email   = (data.get('email', '') or '').strip().lower()
    phone   = (data.get('phone', '') or '').strip()
    password = data.get('password', '')
    address = (data.get('address', '') or '').strip()
    city    = (data.get('city', '') or '').strip()
    state   = (data.get('state', '') or '').strip()
    pincode = (data.get('pincode', '') or '').strip()

    if not name:
        return jsonify({'error': 'Full name is required'}), 400
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email address is required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email already exists'}), 409

    admin = User.query.filter_by(role='admin').first()
    user = User(
        name=name, email=email, phone=phone, role='customer',
        address=address, city=city, state=state, pincode=pincode,
        parent_id=admin.id if admin else None,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'message': f'Welcome to SpicesMart, {name}!',
    }), 201




@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()})

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    data = request.get_json()
    user = current_user()
    if not user.check_password(data.get('old_password', '')):
        return jsonify({'error': 'Current password is incorrect'}), 400
    user.set_password(data.get('new_password', ''))
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'})


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update the logged-in user's contact & address details."""
    user = current_user()
    data = request.get_json()

    updatable = ('name', 'phone', 'address', 'city', 'state', 'pincode', 'gstin')
    for field in updatable:
        if field in data:
            setattr(user, field, data[field].strip() if isinstance(data[field], str) else data[field])

    db.session.commit()
    return jsonify({'user': user.to_dict(), 'message': 'Profile updated successfully'})

