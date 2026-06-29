"""
Seed script — creates admin user, sample distributors, retailers, customers,
products with pricing, and initial inventory.
Run: python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, Product, PriceTier, Inventory

app = create_app()

def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ── Admin ─────────────────────────────────────────
        admin = User(name='SpicesMart Admin', email='admin@spicesmart.com', role='admin', phone='9000000000', address='HQ, Mumbai')
        admin.set_password('admin@123')
        db.session.add(admin)
        db.session.flush()

        # ── Distributors ──────────────────────────────────
        dist1 = User(name='Raj Distributors', email='raj@dist.com', role='distributor', phone='9111111111', parent_id=admin.id, address='Delhi')
        dist1.set_password('dist@123')
        dist2 = User(name='Priya Wholesale', email='priya@dist.com', role='distributor', phone='9222222222', parent_id=admin.id, address='Chennai')
        dist2.set_password('dist@123')
        db.session.add_all([dist1, dist2])
        db.session.flush()

        # ── Retailers ────────────────────────────────────
        ret1 = User(name='Kumar Spice Store', email='kumar@retail.com', role='retailer', phone='9333333333', parent_id=dist1.id, address='Connaught Place, Delhi')
        ret1.set_password('retail@123')
        ret2 = User(name='Meena Bazaar', email='meena@retail.com', role='retailer', phone='9444444444', parent_id=dist2.id, address='T Nagar, Chennai')
        ret2.set_password('retail@123')
        db.session.add_all([ret1, ret2])
        db.session.flush()

        # ── Customers ────────────────────────────────────
        cust1 = User(name='Anita Sharma', email='anita@customer.com', role='customer', phone='9555555555', parent_id=ret1.id, address='Lajpat Nagar, Delhi')
        cust1.set_password('customer@123')
        cust2 = User(name='Suresh Pillai', email='suresh@customer.com', role='customer', phone='9666666666', parent_id=ret2.id, address='Velachery, Chennai')
        cust2.set_password('customer@123')
        db.session.add_all([cust1, cust2])
        db.session.flush()

        # ── Products ─────────────────────────────────────
        products_data = [
            {
                'name': 'Turmeric Powder', 'unit': '500g', 'category': 'Powders',
                'description': 'Pure organic turmeric powder, rich in curcumin.',
                'sku': 'TUR-500', 'image_url': '/static/img/turmeric.jpg',
                'prices': {'distributor': 80, 'retailer': 110, 'customer': 150},
                'stock': 500,
            },
            {
                'name': 'Red Chilli Powder', 'unit': '250g', 'category': 'Powders',
                'description': 'Vibrant red chilli powder with bold flavour.',
                'sku': 'RCP-250', 'image_url': '/static/img/redchilli.jpg',
                'prices': {'distributor': 60, 'retailer': 85, 'customer': 120},
                'stock': 400,
            },
            {
                'name': 'Garam Masala', 'unit': '100g', 'category': 'Blends',
                'description': 'Premium blend of aromatic whole spices.',
                'sku': 'GM-100', 'image_url': '/static/img/garammasala.jpg',
                'prices': {'distributor': 90, 'retailer': 130, 'customer': 180},
                'stock': 300,
            },
            {
                'name': 'Coriander Powder', 'unit': '500g', 'category': 'Powders',
                'description': 'Freshly ground coriander seeds.',
                'sku': 'COR-500', 'image_url': '/static/img/coriander.jpg',
                'prices': {'distributor': 55, 'retailer': 75, 'customer': 100},
                'stock': 600,
            },
            {
                'name': 'Black Pepper Whole', 'unit': '250g', 'category': 'Whole Spices',
                'description': 'Premium whole black peppercorns.',
                'sku': 'BPW-250', 'image_url': '/static/img/blackpepper.jpg',
                'prices': {'distributor': 150, 'retailer': 210, 'customer': 280},
                'stock': 200,
            },
            {
                'name': 'Cardamom Green', 'unit': '100g', 'category': 'Whole Spices',
                'description': 'Aromatic green cardamom pods.',
                'sku': 'CARD-100', 'image_url': '/static/img/cardamom.jpg',
                'prices': {'distributor': 220, 'retailer': 300, 'customer': 400},
                'stock': 150,
            },
            {
                'name': 'Cumin Seeds', 'unit': '250g', 'category': 'Whole Spices',
                'description': 'Premium jeera / cumin seeds.',
                'sku': 'CUM-250', 'image_url': '/static/img/cumin.jpg',
                'prices': {'distributor': 70, 'retailer': 100, 'customer': 140},
                'stock': 350,
            },
            {
                'name': 'Mustard Seeds', 'unit': '500g', 'category': 'Whole Spices',
                'description': 'Small black mustard seeds for tempering.',
                'sku': 'MUS-500', 'image_url': '/static/img/mustard.jpg',
                'prices': {'distributor': 45, 'retailer': 65, 'customer': 90},
                'stock': 400,
            },
            {
                'name': 'Chaat Masala', 'unit': '100g', 'category': 'Blends',
                'description': 'Tangy chaat masala blend.',
                'sku': 'CM-100', 'image_url': '/static/img/chaatmasala.jpg',
                'prices': {'distributor': 65, 'retailer': 90, 'customer': 120},
                'stock': 250,
            },
            {
                'name': 'Saffron', 'unit': '1g', 'category': 'Premium',
                'description': 'Pure Kashmiri saffron strands.',
                'sku': 'SAF-1G', 'image_url': '/static/img/saffron.jpg',
                'prices': {'distributor': 450, 'retailer': 600, 'customer': 800},
                'stock': 50,
            },
        ]

        for pd in products_data:
            p = Product(
                name=pd['name'], description=pd['description'],
                unit=pd['unit'], category=pd['category'],
                image_url=pd['image_url'], sku=pd['sku'],
            )
            db.session.add(p)
            db.session.flush()

            for role, price in pd['prices'].items():
                db.session.add(PriceTier(product_id=p.id, role=role, price=price))

            # Stock for admin warehouse (central)
            db.session.add(Inventory(
                product_id=p.id, owner_id=admin.id,
                quantity=pd['stock'], low_stock_threshold=20
            ))
            # Stock for distributors (50% of admin stock each)
            for dist in [dist1, dist2]:
                db.session.add(Inventory(
                    product_id=p.id, owner_id=dist.id,
                    quantity=pd['stock'] // 2, low_stock_threshold=10
                ))
            # Stock for retailers (25% of admin stock each)
            for ret in [ret1, ret2]:
                db.session.add(Inventory(
                    product_id=p.id, owner_id=ret.id,
                    quantity=pd['stock'] // 4, low_stock_threshold=5
                ))

        db.session.commit()

        print("Database seeded successfully!")
        print("\n-- Login credentials --")
        print("Admin:       admin@spicesmart.com  / admin@123")
        print("Distributor: raj@dist.com          / dist@123")
        print("Distributor: priya@dist.com        / dist@123")
        print("Retailer:    kumar@retail.com      / retail@123")
        print("Retailer:    meena@retail.com      / retail@123")
        print("Customer:    anita@customer.com    / customer@123")
        print("Customer:    suresh@customer.com   / customer@123")

if __name__ == '__main__':
    seed()
