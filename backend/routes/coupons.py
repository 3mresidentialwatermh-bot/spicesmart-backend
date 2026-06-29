from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Coupon
from datetime import datetime

coupons_bp = Blueprint('coupons', __name__)

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'admin'

@coupons_bp.route('/', methods=['GET'])
@jwt_required()
def list_coupons():
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({'error': 'Unauthorized'}), 403
        
    coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return jsonify({'coupons': [c.to_dict() for c in coupons]})

@coupons_bp.route('/', methods=['POST'])
@jwt_required()
def create_coupon():
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    code = data.get('code', '').strip().upper()
    discount = data.get('discount_percent')
    
    if not code or not discount:
        return jsonify({'error': 'Code and discount percentage are required'}), 400
        
    if Coupon.query.filter_by(code=code).first():
        return jsonify({'error': 'Coupon code already exists'}), 400
        
    coupon = Coupon(
        code=code,
        discount_percent=discount,
        is_active=True
    )
    db.session.add(coupon)
    db.session.commit()
    
    return jsonify({'message': 'Coupon created', 'coupon': coupon.to_dict()}), 201

@coupons_bp.route('/<int:coupon_id>', methods=['DELETE'])
@jwt_required()
def delete_coupon(coupon_id):
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({'error': 'Unauthorized'}), 403
        
    coupon = Coupon.query.get(coupon_id)
    if not coupon:
        return jsonify({'error': 'Not found'}), 404
        
    db.session.delete(coupon)
    db.session.commit()
    
    return jsonify({'message': 'Coupon deleted'})

@coupons_bp.route('/validate', methods=['POST'])
@jwt_required()
def validate_coupon():
    data = request.json
    code = data.get('code', '').strip().upper()
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
        
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    
    if not coupon:
        return jsonify({'error': 'Invalid or inactive coupon code'}), 400
        
    return jsonify({
        'valid': True,
        'code': coupon.code,
        'discount_percent': float(coupon.discount_percent)
    })
