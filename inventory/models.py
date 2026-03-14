from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random, string


class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'Product Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=50, default='pcs')
    min_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def total_stock(self):
        return sum(loc.quantity for loc in self.stock_locations.all())

    def is_low_stock(self):
        return self.total_stock() < self.min_stock and self.total_stock() > 0

    def is_out_of_stock(self):
        return self.total_stock() == 0


class StockLocation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_locations')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_locations')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f'{self.product.name} @ {self.warehouse.name}: {self.quantity}'


class Receipt(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('ready', 'Ready'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ]
    ref = models.CharField(max_length=20, unique=True, editable=False)
    supplier = models.CharField(max_length=200)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ref:
            last = Receipt.objects.count()
            self.ref = f'RCP-{str(last + 1).zfill(4)}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ref


class ReceiptLine(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    expected_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.receipt.ref} - {self.product.name}'


class DeliveryOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('ready', 'Ready'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ]
    ref = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.CharField(max_length=200)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ref:
            last = DeliveryOrder.objects.count()
            self.ref = f'DEL-{str(last + 1).zfill(4)}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ref


class DeliveryLine(models.Model):
    delivery = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    demand_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    done_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.delivery.ref} - {self.product.name}'


class InternalTransfer(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ]
    ref = models.CharField(max_length=20, unique=True, editable=False)
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='transfers_out')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='transfers_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ref:
            last = InternalTransfer.objects.count()
            self.ref = f'TRF-{str(last + 1).zfill(4)}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ref


class TransferLine(models.Model):
    transfer = models.ForeignKey(InternalTransfer, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.transfer.ref} - {self.product.name}'


class StockAdjustment(models.Model):
    ref = models.CharField(max_length=20, unique=True, editable=False)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    recorded_qty = models.DecimalField(max_digits=12, decimal_places=2)
    counted_qty = models.DecimalField(max_digits=12, decimal_places=2)
    difference = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.ref:
            last = StockAdjustment.objects.count()
            self.ref = f'ADJ-{str(last + 1).zfill(4)}'
        self.difference = self.counted_qty - self.recorded_qty
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ref


class StockLedger(models.Model):
    MOVE_TYPE = [
        ('receipt', 'Receipt'),
        ('delivery', 'Delivery'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment', 'Adjustment'),
    ]
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    move_type = models.CharField(max_length=20, choices=MOVE_TYPE)
    reference = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)  # +/-
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} | {self.product.name} | {self.quantity:+}'


class OTPToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        from datetime import timedelta
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=10)

    def __str__(self):
        return f'{self.user.username} - {self.token}'
