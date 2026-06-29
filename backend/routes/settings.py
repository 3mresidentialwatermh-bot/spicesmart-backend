import os
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Settings, User

settings_bp = Blueprint('settings', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@settings_bp.route('/', methods=['GET'])
def get_settings():
    """Get public settings (brand name, logo, razorpay key id)."""
    s = Settings.query.first()
    if not s:
        s = Settings(brand_name='SpicesMart')
        db.session.add(s)
        db.session.commit()
    
    return jsonify({
        'brand_name': s.brand_name,
        'brand_logo_url': s.brand_logo_url,
        'razorpay_key_id': s.razorpay_key_id,
        # Do not expose razorpay_key_secret here!
    })


@settings_bp.route('/', methods=['PUT'])
@jwt_required()
def update_settings():
    """Admin-only: update settings."""
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    s = Settings.query.first()
    if not s:
        s = Settings()
        db.session.add(s)

    data = request.get_json()
    if 'brand_name' in data:
        s.brand_name = data['brand_name']
    if 'razorpay_key_id' in data:
        s.razorpay_key_id = data['razorpay_key_id']
    if 'razorpay_key_secret' in data:
        s.razorpay_key_secret = data['razorpay_key_secret']

    db.session.commit()
    return jsonify({'message': 'Settings updated successfully', 'settings': s.to_dict()})


@settings_bp.route('/upload-logo', methods=['POST'])
@jwt_required()
def upload_logo():
    """Admin-only: upload brand logo."""
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty file provided'}), 400

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"brand_logo.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        url = f"/static/uploads/{filename}"
        
        s = Settings.query.first()
        if not s:
            s = Settings()
            db.session.add(s)
        
        s.brand_logo_url = url
        db.session.commit()

        return jsonify({'url': url, 'message': 'Logo updated successfully'})

    return jsonify({'error': 'Invalid file type'}), 400
