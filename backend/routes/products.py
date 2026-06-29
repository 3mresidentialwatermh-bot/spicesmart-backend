from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Product, PriceTier, Inventory, User
from werkzeug.utils import secure_filename
import os, uuid, csv, io


products_bp = Blueprint('products', __name__)

def current_user():
    return User.query.get(int(get_jwt_identity()))

@products_bp.route('/', methods=['GET'])
@jwt_required()
def list_products():
    u = current_user()
    category = request.args.get('category')
    search   = request.args.get('search', '')

    q = Product.query.filter_by(is_active=True)
    if category:
        q = q.filter_by(category=category)
    if search:
        q = q.filter(Product.name.ilike(f'%{search}%'))

    products = q.all()
    return jsonify({'products': [p.to_dict(role=u.role) for p in products]})

@products_bp.route('/public', methods=['GET'])
def list_products_public():
    """Public product list — no auth required. Shows customer pricing."""
    category = request.args.get('category')
    search   = request.args.get('search', '')
    q = Product.query.filter_by(is_active=True)
    if category:
        q = q.filter_by(category=category)
    if search:
        q = q.filter(Product.name.ilike(f'%{search}%'))
    products = q.all()
    return jsonify({'products': [p.to_dict(role='customer') for p in products]})

@products_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    cats = db.session.query(Product.category).filter(
        Product.is_active == True, Product.category != None
    ).distinct().all()
    return jsonify({'categories': [c[0] for c in cats if c[0]]})


@products_bp.route('/<int:pid>', methods=['GET'])
@jwt_required()
def get_product(pid):
    u = current_user()
    p = Product.query.get_or_404(pid)
    return jsonify({'product': p.to_dict(role=u.role)})

@products_bp.route('/', methods=['POST'])
@jwt_required()
def create_product():
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    product = Product(
        name=data['name'],
        description=data.get('description'),
        unit=data.get('unit'),
        category=data.get('category'),
        image_url=data.get('image_url'),
        sku=data.get('sku'),
    )
    db.session.add(product)
    db.session.flush()  # get product.id

    # Create price tiers
    for role in ('distributor', 'retailer', 'customer'):
        price_val = data.get('prices', {}).get(role, 0)
        pt = PriceTier(product_id=product.id, role=role, price=price_val)
        db.session.add(pt)

    # Initialize inventory for admin (central warehouse)
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        inv = Inventory(
            product_id=product.id,
            owner_id=admin.id,
            quantity=data.get('initial_stock', 0),
            low_stock_threshold=data.get('low_stock_threshold', 10),
        )
        db.session.add(inv)

    db.session.commit()
    return jsonify({'product': product.to_dict()}), 201

@products_bp.route('/<int:pid>', methods=['PUT'])
@jwt_required()
def update_product(pid):
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    product = Product.query.get_or_404(pid)
    data = request.get_json()

    for field in ('name', 'description', 'unit', 'category', 'image_url', 'sku', 'is_active'):
        if field in data:
            setattr(product, field, data[field])

    # Update prices
    if 'prices' in data:
        for role, price_val in data['prices'].items():
            pt = PriceTier.query.filter_by(product_id=pid, role=role).first()
            if pt:
                pt.price = price_val
            else:
                db.session.add(PriceTier(product_id=pid, role=role, price=price_val))

    db.session.commit()
    return jsonify({'product': product.to_dict()})

@products_bp.route('/<int:pid>', methods=['DELETE'])
@jwt_required()
def delete_product(pid):
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    product = Product.query.get_or_404(pid)
    product.is_active = False
    db.session.commit()
    return jsonify({'message': 'Product deactivated'})


# ── IMAGE UPLOAD ────────────────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@products_bp.route('/upload-image', methods=['POST'])
@jwt_required()
def upload_image():
    """Upload a product image. Returns the URL to store in image_url field."""
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PNG, JPG, GIF or WEBP'}), 400

    ext      = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    url = f"/static/uploads/{filename}"
    return jsonify({'url': url, 'filename': filename}), 201

@products_bp.route('/bulk-upload-images', methods=['POST'])
@jwt_required()
def bulk_upload_images():
    """Admin-only: Upload multiple images and match by filename (SKU.jpg)."""
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    files = request.files.getlist('images')
    if not files:
        return jsonify({'error': 'No files provided'}), 400

    matched = 0
    errors = []

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            base_name, ext = file.filename.rsplit('.', 1)
            sku = base_name.upper()
            
            product = Product.query.filter_by(sku=sku).first()
            if product:
                safe_filename = secure_filename(f"{sku}.{ext}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_filename)
                file.save(filepath)
                product.image_url = f"/static/uploads/{safe_filename}"
                matched += 1
            else:
                errors.append(f"No product found for SKU: {sku} (from {file.filename})")
        else:
            errors.append(f"Invalid file: {file.filename}")

    db.session.commit()
    
    return jsonify({
        'message': f'Successfully matched {matched} images to products.',
        'matched': matched,
        'errors': errors
    })

# ── BULK CSV PRODUCT IMPORT ─────────────────────────────────────────────────
@products_bp.route('/bulk-import', methods=['POST'])
@jwt_required()
def bulk_import():
    """
    Import products from a CSV file.
    Expected CSV columns (header row required):
      name, sku, unit, category, description, distributor_price, retailer_price, customer_price, initial_stock
    Returns summary of created / updated / failed rows.
    """
    u = current_user()
    if u.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No CSV file provided'}), 400

    file = request.files['file']
    stream   = io.StringIO(file.stream.read().decode('utf-8-sig'))  # handle BOM
    reader   = csv.DictReader(stream)

    created, updated, errors = [], [], []

    for i, row in enumerate(reader, start=2):   # row 1 = header
        name = (row.get('name') or row.get('Name') or '').strip()
        if not name:
            errors.append({'row': i, 'error': 'Missing product name'})
            continue

        try:
            dist_price = float(row.get('distributor_price') or row.get('Distributor Price') or 0)
            ret_price  = float(row.get('retailer_price')    or row.get('Retailer Price')    or 0)
            cust_price = float(row.get('customer_price')    or row.get('Customer Price')    or 0)
            init_stock = int(float(row.get('initial_stock') or row.get('Initial Stock')     or 0))
        except ValueError as e:
            errors.append({'row': i, 'error': f'Invalid number: {e}'})
            continue

        sku      = (row.get('sku')         or row.get('SKU')         or '').strip()
        unit     = (row.get('unit')        or row.get('Unit')        or '').strip()
        category = (row.get('category')    or row.get('Category')    or 'Spices').strip()
        desc     = (row.get('description') or row.get('Description') or '').strip()

        # Find existing product by SKU or name
        product = None
        if sku:
            product = Product.query.filter_by(sku=sku).first()
        if not product:
            product = Product.query.filter(Product.name.ilike(name)).first()

        if product:
            product.unit     = unit or product.unit
            product.category = category or product.category
            product.description = desc or product.description
            updated.append(name)
        else:
            product = Product(name=name, sku=sku, unit=unit, category=category, description=desc)
            db.session.add(product)
            db.session.flush()

            # Initial stock for admin
            admin_users = User.query.filter_by(role='admin').all()
            for admin in admin_users:
                db.session.add(Inventory(
                    product_id=product.id, owner_id=admin.id,
                    quantity=init_stock, low_stock_threshold=10
                ))
            created.append(name)

        # Update price tiers
        for role, price_val in [('distributor', dist_price), ('retailer', ret_price), ('customer', cust_price)]:
            pt = PriceTier.query.filter_by(product_id=product.id, role=role).first()
            if pt:
                pt.price = price_val
            else:
                db.session.add(PriceTier(product_id=product.id, role=role, price=price_val))

    db.session.commit()

    return jsonify({
        'success': True,
        'created': len(created),
        'updated': len(updated),
        'errors':  len(errors),
        'created_products': created,
        'updated_products': updated,
        'error_details': errors,
    })


# ── SAMPLE CSV TEMPLATE ─────────────────────────────────────────────────────
@products_bp.route('/sample-csv', methods=['GET'])
def sample_csv():
    """
    Download a unified CSV template for bulk import of products AND pricing.
    No auth needed — public template.
    - New SKU → creates product + sets all 3 price tiers + initial stock
    - Existing SKU → updates name / prices / stock (no data lost)
    """
    from flask import Response
    sample = (
        "name,sku,unit,category,description,distributor_price,retailer_price,customer_price,initial_stock\n"
        "Turmeric Powder,TUR-500,500g,Powders,Pure turmeric powder - high curcumin content,80,110,150,500\n"
        "Red Chilli Powder,RCP-250,250g,Powders,Hot red chilli powder - vibrant color,60,85,120,400\n"
        "Garam Masala,GM-100,100g,Blends,Classic aromatic garam masala blend,120,160,180,300\n"
        "Cardamom Green,CDM-50,50g,Premium,Fresh green cardamom pods,350,420,500,200\n"
        "Mustard Seeds,MUS-500,500g,Whole Spices,Black mustard seeds for tempering,40,55,80,600\n"
        "Coriander Powder,COR-250,250g,Powders,Fine ground coriander seeds,45,65,100,500\n"
    )
    return Response(
        sample,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=spicesmart_bulk_upload_template.csv'}
    )


