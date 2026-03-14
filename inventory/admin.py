from django.contrib import admin
from .models import (
    Warehouse, ProductCategory, Product, StockLocation,
    Receipt, ReceiptLine, DeliveryOrder, DeliveryLine,
    InternalTransfer, TransferLine, StockAdjustment, StockLedger, OTPToken,
)

admin.site.register(Warehouse)
admin.site.register(ProductCategory)
admin.site.register(Product)
admin.site.register(StockLocation)

class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 1

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    inlines = [ReceiptLineInline]
    list_display = ['ref', 'supplier', 'warehouse', 'status', 'created_at']
    list_filter = ['status', 'warehouse']

class DeliveryLineInline(admin.TabularInline):
    model = DeliveryLine
    extra = 1

@admin.register(DeliveryOrder)
class DeliveryAdmin(admin.ModelAdmin):
    inlines = [DeliveryLineInline]
    list_display = ['ref', 'customer', 'warehouse', 'status', 'created_at']
    list_filter = ['status', 'warehouse']

class TransferLineInline(admin.TabularInline):
    model = TransferLine
    extra = 1

@admin.register(InternalTransfer)
class TransferAdmin(admin.ModelAdmin):
    inlines = [TransferLineInline]
    list_display = ['ref', 'from_warehouse', 'to_warehouse', 'status', 'created_at']

admin.site.register(StockAdjustment)
admin.site.register(StockLedger)
admin.site.register(OTPToken)
