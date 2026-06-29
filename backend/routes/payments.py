"""
payments.py — Razorpay payment gateway integration
Endpoints:
  POST /api/payments/create-order   — create a Razorpay order
  POST /api/payments/verify         — verify payment signature
  GET  /api/payments/key            — get the public Razorpay key for frontend
"""
import hmac
import hashlib
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Order, Settings

payments_bp = Blueprint('payments', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

def get_razorpay_client():
    try:
        import razorpay
        s = Settings.query.first()
        if not s or not s.razorpay_key_id or not s.razorpay_key_secret:
            return None
        return razorpay.Client(auth=(s.razorpay_key_id, s.razorpay_key_secret))
    except Exception:
        return None

@payments_bp.route('/key', methods=['GET'])
def get_key():
    """Return the public Razorpay key ID so the frontend can use the checkout widget."""
    s = Settings.query.first()
    if s and s.razorpay_key_id:
        return jsonify({'key_id': s.razorpay_key_id, 'configured': True, 'mode': 'test' if 'test' in s.razorpay_key_id else 'live'})
    return jsonify({'key_id': '', 'configured': False, 'mode': 'test'})


@payments_bp.route('/create-order', methods=['POST'])
@jwt_required()
def create_razorpay_order():
    """
    Create a Razorpay order for payment.
    Body: { "amount": 480.00, "order_id": 1 }    (amount in INR)
    Returns Razorpay order object needed by the frontend checkout widget.
    """
    data = request.get_json()
    amount_inr = float(data.get('amount', 0))
    our_order_id = data.get('order_id')

    client = get_razorpay_client()

    if not client:
        # ── MOCK MODE (no Razorpay keys configured) ─────────────────────────
        return jsonify({
            'mock': True,
            'razorpay_order_id': f'mock_order_{our_order_id}',
            'amount': int(amount_inr * 100),
            'currency': 'INR',
            'message': 'Razorpay not configured — payment simulated successfully',
        })

    # ── REAL RAZORPAY ────────────────────────────────────────────────────────
    try:
        rz_order = client.order.create({
            'amount':   int(amount_inr * 100),    # Razorpay uses paisa
            'currency': 'INR',
            'receipt':  f'spices_order_{our_order_id}',
            'notes': {
                'spicesapp_order_id': str(our_order_id),
            },
        })
        return jsonify({
            'mock': False,
            'razorpay_order_id': rz_order['id'],
            'amount':   rz_order['amount'],
            'currency': rz_order['currency'],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payments_bp.route('/verify', methods=['POST'])
@jwt_required()
def verify_payment():
    """
    Verify Razorpay payment signature after successful payment.
    Body: {
        "razorpay_order_id": "...",
        "razorpay_payment_id": "...",
        "razorpay_signature": "...",
        "order_id": 1
    }
    """
    data = request.get_json()
    our_order_id     = data.get('order_id')
    rz_order_id      = data.get('razorpay_order_id', '')
    rz_payment_id    = data.get('razorpay_payment_id', '')
    rz_signature     = data.get('razorpay_signature', '')

    # Mock mode — if no real Razorpay, just mark as paid
    if data.get('mock') or rz_order_id.startswith('mock_'):
        order = Order.query.get(our_order_id)
        if order:
            order.payment_status = 'paid'
            order.payment_id = 'MOCK_PAYMENT'
            db.session.commit()
        return jsonify({'success': True, 'message': 'Mock payment recorded'})

    # Real signature verification
    key_secret = current_app.config['RAZORPAY_KEY_SECRET'].encode()
    payload    = f'{rz_order_id}|{rz_payment_id}'.encode()
    expected   = hmac.new(key_secret, payload, hashlib.sha256).hexdigest()

    if expected != rz_signature:
        return jsonify({'success': False, 'error': 'Signature mismatch'}), 400

    # Mark order as paid
    order = Order.query.get(our_order_id)
    if order:
        order.payment_status = 'paid'
        order.payment_id     = rz_payment_id
        db.session.commit()

    return jsonify({'success': True, 'payment_id': rz_payment_id})
