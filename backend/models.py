from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    phone      = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.String(20), nullable=False)   # admin | distributor | retailer | customer
    parent_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # Address / Contact
    address    = db.Column(db.Text)
    city       = db.Column(db.String(100))
    state      = db.Column(db.String(100))
    pincode    = db.Column(db.String(10))
    gstin      = db.Column(db.String(20))   # GST number for business users
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    children   = db.relationship('User', backref=db.backref('parent', remote_side=[id]))
    orders_placed   = db.relationship('Order', foreign_keys='Order.buyer_id',  backref='buyer')
    orders_received = db.relationship('Order', foreign_keys='Order.seller_id', backref='seller')
    inventory  = db.relationship('Inventory', backref='owner')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone or '',
            'role': self.role,
            'parent_id': self.parent_id,
            'parent_name': self.parent.name if self.parent else None,
            'address': self.address or '',
            'city': self.city or '',
            'state': self.state or '',
            'pincode': self.pincode or '',
            'gstin': self.gstin or '',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────
# Products
# ─────────────────────────────────────────────
class Product(db.Model):
    __tablename__ = 'products'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unit        = db.Column(db.String(50))          # e.g. 500g, 1kg
    category    = db.Column(db.String(100))         # Whole Spices, Blends, etc.
    image_url   = db.Column(db.String(500))
    sku         = db.Column(db.String(50), unique=True)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    prices      = db.relationship('PriceTier', backref='product', cascade='all, delete-orphan')
    inventory   = db.relationship('Inventory', backref='product', cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product')

    def get_price_for_role(self, role):
        # Admin (company) is the seller — show distributor rate as reference price
        effective_role = 'distributor' if role == 'admin' else role
        for pt in self.prices:
            if pt.role == effective_role:
                return float(pt.price)
        return 0.0

    def to_dict(self, role=None):
        d = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'unit': self.unit,
            'category': self.category,
            'image_url': self.image_url,
            'sku': self.sku,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'prices': {pt.role: float(pt.price) for pt in self.prices},
        }
        if role:
            d['my_price'] = self.get_price_for_role(role)
            d['price_label'] = '(Distributor Rate)' if role == 'admin' else ''
        return d


# ─────────────────────────────────────────────
# Price Tiers
# ─────────────────────────────────────────────
class PriceTier(db.Model):
    __tablename__ = 'price_tiers'

    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    role       = db.Column(db.String(20), nullable=False)  # distributor | retailer | customer
    price      = db.Column(db.Numeric(10, 2), nullable=False)

    __table_args__ = (db.UniqueConstraint('product_id', 'role', name='uq_product_role'),)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'role': self.role,
            'price': float(self.price),
        }


# ─────────────────────────────────────────────
# Inventory
# ─────────────────────────────────────────────
class Inventory(db.Model):
    __tablename__ = 'inventory'

    id                  = db.Column(db.Integer, primary_key=True)
    product_id          = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    owner_id            = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity            = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=10)
    updated_at          = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('product_id', 'owner_id', name='uq_product_owner'),)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'product_unit': self.product.unit if self.product else None,
            'owner_id': self.owner_id,
            'owner_name': self.owner.name if self.owner else None,
            'owner_role': self.owner.role if self.owner else None,
            'quantity': self.quantity,
            'low_stock_threshold': self.low_stock_threshold,
            'is_low': self.quantity <= self.low_stock_threshold,
        }


# ─────────────────────────────────────────────
# Orders
# ─────────────────────────────────────────────
class Order(db.Model):
    __tablename__ = 'orders'

    id             = db.Column(db.Integer, primary_key=True)
    buyer_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status         = db.Column(db.String(20), default='pending')   # pending|confirmed|shipped|delivered|cancelled
    total_amount   = db.Column(db.Numeric(12, 2), default=0)
    payment_status = db.Column(db.String(20), default='pending')   # pending|paid|failed
    payment_ref    = db.Column(db.String(100))
    notes          = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'buyer_id': self.buyer_id,
            'buyer_name': self.buyer.name if self.buyer else None,
            'buyer_role': self.buyer.role if self.buyer else None,
            'seller_id': self.seller_id,
            'seller_name': self.seller.name if self.seller else None,
            'seller_role': self.seller.role if self.seller else None,
            'status': self.status,
            'total_amount': float(self.total_amount),
            'payment_status': self.payment_status,
            'payment_ref': self.payment_ref,
            'notes': self.notes,
            'items': [i.to_dict() for i in self.items],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'product_unit': self.product.unit if self.product else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'subtotal': float(self.unit_price) * self.quantity,
        }

# ─────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────
class Settings(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    brand_name = db.Column(db.String(100), default='SpicesMart')
    brand_logo_url = db.Column(db.String(500), nullable=True)
    razorpay_key_id = db.Column(db.String(100), nullable=True)
    razorpay_key_secret = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            'brand_name': self.brand_name,
            'brand_logo_url': self.brand_logo_url,
            'razorpay_key_id': self.razorpay_key_id,
        }
