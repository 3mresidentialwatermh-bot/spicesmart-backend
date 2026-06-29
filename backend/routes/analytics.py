from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Order, OrderItem, Product, User
from sqlalchemy import func
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_analytics():
    u = current_user()
    if u.role not in ('admin', 'distributor', 'retailer'):
        return jsonify({'error': 'Access denied'}), 403

    # We only look at orders where this user is the seller
    base_query = db.session.query(Order).filter(Order.seller_id == u.id)

    # 1. Total Revenue & Orders
    totals = base_query.with_entities(
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total_amount).label('total_revenue')
    ).first()

    # 2. Revenue over the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # SQLite friendly date grouping (YYYY-MM-DD)
    date_func = func.date(Order.created_at)
    
    daily_sales = base_query.filter(Order.created_at >= thirty_days_ago)\
        .with_entities(date_func.label('day'), func.sum(Order.total_amount).label('revenue'))\
        .group_by('day').order_by('day').all()
        
    revenue_by_date = {day: float(rev) for day, rev in daily_sales if rev}

    # 3. Top Selling Products (by quantity)
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem, OrderItem.product_id == Product.id)\
     .join(Order, Order.id == OrderItem.order_id)\
     .filter(Order.seller_id == u.id)\
     .group_by(Product.id)\
     .order_by(func.sum(OrderItem.quantity).desc())\
     .limit(5).all()

    top_products_data = [{'name': name, 'quantity': int(qty)} for name, qty in top_products if qty]

    # 4. Sales by Customer Role (Distributor vs Retailer vs Customer)
    sales_by_role = db.session.query(
        User.role,
        func.sum(Order.total_amount).label('revenue')
    ).join(Order, Order.buyer_id == User.id)\
     .filter(Order.seller_id == u.id)\
     .group_by(User.role).all()

    sales_by_role_data = {role: float(rev) for role, rev in sales_by_role if rev}

    return jsonify({
        'total_orders': totals.total_orders or 0,
        'total_revenue': float(totals.total_revenue or 0),
        'revenue_by_date': revenue_by_date,
        'top_products': top_products_data,
        'sales_by_role': sales_by_role_data
    })
