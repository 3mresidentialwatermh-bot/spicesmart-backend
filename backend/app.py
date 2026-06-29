from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": ["https://spicesmart1.vercel.app", "http://localhost:8080"]}}, supports_credentials=True)


    # Register blueprints
    from routes.auth      import auth_bp
    from routes.products  import products_bp
    from routes.pricing   import pricing_bp
    from routes.orders    import orders_bp
    from routes.inventory import inventory_bp
    from routes.users     import users_bp
    from routes.payments  import payments_bp
    from routes.settings  import settings_bp
    from routes.analytics import analytics_bp
    from routes.coupons   import coupons_bp

    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(products_bp,  url_prefix='/api/products')
    app.register_blueprint(pricing_bp,   url_prefix='/api/pricing')
    app.register_blueprint(orders_bp,    url_prefix='/api/orders')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    app.register_blueprint(users_bp,     url_prefix='/api/users')
    app.register_blueprint(payments_bp,  url_prefix='/api/payments')
    app.register_blueprint(settings_bp,  url_prefix='/api/settings')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(coupons_bp,   url_prefix='/api/coupons')

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

