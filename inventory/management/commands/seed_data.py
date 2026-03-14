from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import (
    Warehouse, ProductCategory, Product, StockLocation, StockLedger
)

class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def handle(self, *args, **kwargs):
        # Admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@coreinventory.in', 'admin123')
            admin.first_name = 'Admin'
            admin.last_name = 'User'
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created superuser: admin / admin123'))

        # Warehouses
        wh1, _ = Warehouse.objects.get_or_create(name='Main Warehouse', defaults={'location': 'Bengaluru, KA'})
        wh2, _ = Warehouse.objects.get_or_create(name='Warehouse B', defaults={'location': 'Mysuru, KA'})
        wh3, _ = Warehouse.objects.get_or_create(name='Production Rack', defaults={'location': 'In-plant, Bengaluru'})

        # Categories
        cats = ['Raw Material', 'Furniture', 'Electrical', 'Packaging', 'Safety', 'Tools']
        cat_objs = {}
        for c in cats:
            obj, _ = ProductCategory.objects.get_or_create(name=c)
            cat_objs[c] = obj

        # Products + stock
        products_data = [
            ('Steel Rods', 'STL-001', 'Raw Material', 'kg', 20, wh1, 77),
            ('Office Chairs', 'FRN-042', 'Furniture', 'pcs', 10, wh2, 8),
            ('Copper Wire', 'ELC-017', 'Electrical', 'm', 50, wh1, 340),
            ('Cardboard Boxes', 'PKG-003', 'Packaging', 'pcs', 100, wh2, 0),
            ('Safety Helmets', 'PPE-009', 'Safety', 'pcs', 20, wh1, 45),
            ('Drill Bits Set', 'TLS-031', 'Tools', 'set', 5, wh3, 12),
        ]
        admin_user = User.objects.get(username='admin')
        for name, sku, cat, uom, min_stock, wh, qty in products_data:
            p, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'category': cat_objs[cat],
                    'unit_of_measure': uom,
                    'min_stock': min_stock,
                }
            )
            if created or not StockLocation.objects.filter(product=p, warehouse=wh).exists():
                loc, _ = StockLocation.objects.get_or_create(product=p, warehouse=wh)
                loc.quantity = qty
                loc.save()
                if qty > 0:
                    StockLedger.objects.create(
                        product=p, warehouse=wh,
                        move_type='receipt', reference='SEED',
                        quantity=qty, balance_after=qty,
                        note='Initial seed data', created_by=admin_user
                    )

        self.stdout.write(self.style.SUCCESS('Sample data seeded successfully!'))
        self.stdout.write('Login at: http://127.0.0.1:8000/login/')
        self.stdout.write('Username: admin | Password: admin123')
