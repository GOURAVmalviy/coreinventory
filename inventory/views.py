from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Q, Sum
import random, string

from .models import (
    Product, ProductCategory, Warehouse, StockLocation,
    Receipt, ReceiptLine,
    DeliveryOrder, DeliveryLine,
    InternalTransfer, TransferLine,
    StockAdjustment, StockLedger, OTPToken,
)
from .forms import (
    LoginForm, SignupForm, OTPRequestForm, OTPVerifyForm,
    ProductForm, InitialStockForm, WarehouseForm,
    ReceiptForm, ReceiptLineFormSet,
    DeliveryForm, DeliveryLineFormSet,
    TransferForm, TransferLineFormSet,
    StockAdjustmentForm,
)


# ─── Auth ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')
    return render(request, 'inventory/auth/login.html', {'form': form})


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Account created. Welcome to CoreInventory!')
        return redirect('dashboard')
    return render(request, 'inventory/auth/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def otp_request_view(request):
    form = OTPRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            token = ''.join(random.choices(string.digits, k=6))
            OTPToken.objects.create(user=user, token=token)
            # In production, send email. Here we print to console.
            from django.core.mail import send_mail
            send_mail(
                'CoreInventory Password Reset OTP',
                f'Your OTP is: {token}\nValid for 10 minutes.',
                'noreply@coreinventory.in',
                [email],
                fail_silently=True,
            )
            print(f'\n[DEV] OTP for {email}: {token}\n')
            request.session['otp_user_id'] = user.id
            messages.info(request, f'OTP sent (dev: check console). Token: {token}')
            return redirect('otp_verify')
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email.')
    return render(request, 'inventory/auth/otp_request.html', {'form': form})


def otp_verify_view(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('otp_request')
    form = OTPVerifyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        token = form.cleaned_data['token']
        try:
            otp = OTPToken.objects.filter(user_id=user_id, token=token, is_used=False).latest('created_at')
            if otp.is_valid():
                otp.is_used = True
                otp.save()
                user = otp.user
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                del request.session['otp_user_id']
                messages.success(request, 'Password reset successfully. Please log in.')
                return redirect('login')
            else:
                messages.error(request, 'OTP expired. Please request a new one.')
        except OTPToken.DoesNotExist:
            messages.error(request, 'Invalid OTP.')
    return render(request, 'inventory/auth/otp_verify.html', {'form': form})


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    products = Product.objects.filter(is_active=True).prefetch_related('stock_locations')
    total_products = products.count()
    low_stock = [p for p in products if p.is_low_stock()]
    out_of_stock = [p for p in products if p.is_out_of_stock()]

    pending_receipts = Receipt.objects.filter(status__in=['waiting', 'ready']).count()
    pending_deliveries = DeliveryOrder.objects.filter(status__in=['waiting', 'ready']).count()
    pending_transfers = InternalTransfer.objects.filter(status='ready').count()

    recent_receipts = Receipt.objects.select_related('warehouse').order_by('-created_at')[:5]
    recent_deliveries = DeliveryOrder.objects.select_related('warehouse').order_by('-created_at')[:5]
    recent_transfers = InternalTransfer.objects.select_related('from_warehouse', 'to_warehouse').order_by('-created_at')[:5]
    recent_ledger = StockLedger.objects.select_related('product', 'warehouse').order_by('-created_at')[:10]

    filter_type = request.GET.get('type', 'all')

    ctx = {
        'total_products': total_products,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'pending_receipts': pending_receipts,
        'pending_deliveries': pending_deliveries,
        'pending_transfers': pending_transfers,
        'recent_receipts': recent_receipts,
        'recent_deliveries': recent_deliveries,
        'recent_transfers': recent_transfers,
        'recent_ledger': recent_ledger,
        'filter_type': filter_type,
    }
    return render(request, 'inventory/dashboard.html', ctx)


# ─── Products ────────────────────────────────────────────────────────────────

@login_required
def product_list(request):
    q = request.GET.get('q', '')
    cat = request.GET.get('cat', '')
    products = Product.objects.filter(is_active=True).prefetch_related('stock_locations__warehouse').select_related('category')
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if cat:
        products = products.filter(category__id=cat)
    categories = ProductCategory.objects.all()
    return render(request, 'inventory/products/list.html', {
        'products': products, 'categories': categories, 'q': q, 'cat': cat
    })


@login_required
def product_create(request):
    form = ProductForm(request.POST or None)
    stock_form = InitialStockForm(request.POST or None)
    if request.method == 'POST' and form.is_valid() and stock_form.is_valid():
        product = form.save()
        warehouse = stock_form.cleaned_data['warehouse']
        qty = stock_form.cleaned_data.get('initial_qty') or 0
        if qty > 0:
            loc, _ = StockLocation.objects.get_or_create(product=product, warehouse=warehouse)
            loc.quantity = qty
            loc.save()
            StockLedger.objects.create(
                product=product, warehouse=warehouse,
                move_type='receipt', reference='INIT',
                quantity=qty, balance_after=qty,
                note='Initial stock', created_by=request.user
            )
        messages.success(request, f'Product {product.name} created.')
        return redirect('product_list')
    return render(request, 'inventory/products/form.html', {'form': form, 'stock_form': stock_form, 'title': 'New Product'})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('product_list')
    return render(request, 'inventory/products/form.html', {'form': form, 'product': product, 'title': 'Edit Product'})


# ─── Receipts ────────────────────────────────────────────────────────────────

@login_required
def receipt_list(request):
    status = request.GET.get('status', '')
    receipts = Receipt.objects.select_related('warehouse', 'created_by').prefetch_related('lines').order_by('-created_at')
    if status:
        receipts = receipts.filter(status=status)
    return render(request, 'inventory/receipts/list.html', {'receipts': receipts, 'status': status})


@login_required
def receipt_create(request):
    form = ReceiptForm(request.POST or None)
    formset = ReceiptLineFormSet(request.POST or None)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        receipt = form.save(commit=False)
        receipt.created_by = request.user
        receipt.save()
        formset.instance = receipt
        formset.save()
        messages.success(request, f'Receipt {receipt.ref} created.')
        return redirect('receipt_list')
    return render(request, 'inventory/receipts/form.html', {
        'form': form, 'formset': formset, 'title': 'New Receipt'
    })


@login_required
def receipt_detail(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    return render(request, 'inventory/receipts/detail.html', {'receipt': receipt})


@login_required
def receipt_validate(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    if receipt.status not in ('ready', 'waiting', 'draft'):
        messages.error(request, 'Cannot validate this receipt.')
        return redirect('receipt_detail', pk=pk)

    with transaction.atomic():
        for line in receipt.lines.all():
            qty = line.received_qty or line.expected_qty
            loc, _ = StockLocation.objects.get_or_create(
                product=line.product, warehouse=receipt.warehouse
            )
            loc.quantity += qty
            loc.save()
            StockLedger.objects.create(
                product=line.product, warehouse=receipt.warehouse,
                move_type='receipt', reference=receipt.ref,
                quantity=qty, balance_after=loc.quantity,
                note=f'Receipt from {receipt.supplier}', created_by=request.user
            )
        receipt.status = 'done'
        receipt.validated_at = timezone.now()
        receipt.save()

    messages.success(request, f'{receipt.ref} validated — stock updated.')
    return redirect('receipt_detail', pk=pk)


# ─── Deliveries ──────────────────────────────────────────────────────────────

@login_required
def delivery_list(request):
    status = request.GET.get('status', '')
    deliveries = DeliveryOrder.objects.select_related('warehouse', 'created_by').prefetch_related('lines').order_by('-created_at')
    if status:
        deliveries = deliveries.filter(status=status)
    return render(request, 'inventory/deliveries/list.html', {'deliveries': deliveries, 'status': status})


@login_required
def delivery_create(request):
    form = DeliveryForm(request.POST or None)
    formset = DeliveryLineFormSet(request.POST or None)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        delivery = form.save(commit=False)
        delivery.created_by = request.user
        delivery.save()
        formset.instance = delivery
        formset.save()
        messages.success(request, f'Delivery {delivery.ref} created.')
        return redirect('delivery_list')
    return render(request, 'inventory/deliveries/form.html', {
        'form': form, 'formset': formset, 'title': 'New Delivery Order'
    })


@login_required
def delivery_detail(request, pk):
    delivery = get_object_or_404(DeliveryOrder, pk=pk)
    return render(request, 'inventory/deliveries/detail.html', {'delivery': delivery})


@login_required
def delivery_validate(request, pk):
    delivery = get_object_or_404(DeliveryOrder, pk=pk)
    if delivery.status not in ('ready', 'waiting', 'draft'):
        messages.error(request, 'Cannot validate this delivery.')
        return redirect('delivery_detail', pk=pk)

    with transaction.atomic():
        for line in delivery.lines.all():
            qty = line.done_qty or line.demand_qty
            loc, _ = StockLocation.objects.get_or_create(
                product=line.product, warehouse=delivery.warehouse
            )
            loc.quantity = max(0, loc.quantity - qty)
            loc.save()
            StockLedger.objects.create(
                product=line.product, warehouse=delivery.warehouse,
                move_type='delivery', reference=delivery.ref,
                quantity=-qty, balance_after=loc.quantity,
                note=f'Delivery to {delivery.customer}', created_by=request.user
            )
        delivery.status = 'done'
        delivery.validated_at = timezone.now()
        delivery.save()

    messages.success(request, f'{delivery.ref} validated — stock decreased.')
    return redirect('delivery_detail', pk=pk)


# ─── Transfers ───────────────────────────────────────────────────────────────

@login_required
def transfer_list(request):
    status = request.GET.get('status', '')
    transfers = InternalTransfer.objects.select_related('from_warehouse', 'to_warehouse', 'created_by').prefetch_related('lines').order_by('-created_at')
    if status:
        transfers = transfers.filter(status=status)
    return render(request, 'inventory/transfers/list.html', {'transfers': transfers, 'status': status})


@login_required
def transfer_create(request):
    form = TransferForm(request.POST or None)
    formset = TransferLineFormSet(request.POST or None)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        transfer = form.save(commit=False)
        transfer.created_by = request.user
        transfer.save()
        formset.instance = transfer
        formset.save()
        messages.success(request, f'Transfer {transfer.ref} created.')
        return redirect('transfer_list')
    return render(request, 'inventory/transfers/form.html', {
        'form': form, 'formset': formset, 'title': 'New Internal Transfer'
    })


@login_required
def transfer_detail(request, pk):
    transfer = get_object_or_404(InternalTransfer, pk=pk)
    return render(request, 'inventory/transfers/detail.html', {'transfer': transfer})


@login_required
def transfer_validate(request, pk):
    transfer = get_object_or_404(InternalTransfer, pk=pk)
    if transfer.status not in ('ready', 'draft'):
        messages.error(request, 'Cannot validate this transfer.')
        return redirect('transfer_detail', pk=pk)

    with transaction.atomic():
        for line in transfer.lines.all():
            # Deduct from source
            src, _ = StockLocation.objects.get_or_create(product=line.product, warehouse=transfer.from_warehouse)
            src.quantity = max(0, src.quantity - line.quantity)
            src.save()
            StockLedger.objects.create(
                product=line.product, warehouse=transfer.from_warehouse,
                move_type='transfer_out', reference=transfer.ref,
                quantity=-line.quantity, balance_after=src.quantity,
                note=f'Transfer to {transfer.to_warehouse.name}', created_by=request.user
            )
            # Add to destination
            dst, _ = StockLocation.objects.get_or_create(product=line.product, warehouse=transfer.to_warehouse)
            dst.quantity += line.quantity
            dst.save()
            StockLedger.objects.create(
                product=line.product, warehouse=transfer.to_warehouse,
                move_type='transfer_in', reference=transfer.ref,
                quantity=line.quantity, balance_after=dst.quantity,
                note=f'Transfer from {transfer.from_warehouse.name}', created_by=request.user
            )
        transfer.status = 'done'
        transfer.validated_at = timezone.now()
        transfer.save()

    messages.success(request, f'{transfer.ref} validated — stock moved.')
    return redirect('transfer_detail', pk=pk)


# ─── Adjustments ─────────────────────────────────────────────────────────────

@login_required
def adjustment_list(request):
    adjustments = StockAdjustment.objects.select_related('product', 'warehouse', 'created_by').order_by('-created_at')
    return render(request, 'inventory/adjustments/list.html', {'adjustments': adjustments})


@login_required
def adjustment_create(request):
    form = StockAdjustmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        product = form.cleaned_data['product']
        warehouse = form.cleaned_data['warehouse']
        counted_qty = form.cleaned_data['counted_qty']

        loc, _ = StockLocation.objects.get_or_create(product=product, warehouse=warehouse)
        recorded_qty = loc.quantity

        with transaction.atomic():
            adj = form.save(commit=False)
            adj.recorded_qty = recorded_qty
            adj.created_by = request.user
            adj.save()

            loc.quantity = counted_qty
            loc.save()

            diff = counted_qty - recorded_qty
            StockLedger.objects.create(
                product=product, warehouse=warehouse,
                move_type='adjustment', reference=adj.ref,
                quantity=diff, balance_after=counted_qty,
                note=adj.reason or 'Manual count adjustment', created_by=request.user
            )

        messages.success(request, f'Adjustment {adj.ref} saved. Difference: {diff:+}')
        return redirect('adjustment_list')
    return render(request, 'inventory/adjustments/form.html', {'form': form, 'title': 'New Stock Adjustment'})


# ─── Move History ─────────────────────────────────────────────────────────────

@login_required
def move_history(request):
    q = request.GET.get('q', '')
    move_type = request.GET.get('type', '')
    ledger = StockLedger.objects.select_related('product', 'warehouse', 'created_by').order_by('-created_at')
    if q:
        ledger = ledger.filter(Q(reference__icontains=q) | Q(product__name__icontains=q))
    if move_type:
        ledger = ledger.filter(move_type=move_type)
    return render(request, 'inventory/history.html', {'ledger': ledger, 'q': q, 'move_type': move_type})


# ─── Settings ────────────────────────────────────────────────────────────────

@login_required
def settings_view(request):
    warehouses = Warehouse.objects.all()
    categories = ProductCategory.objects.all()
    wh_form = WarehouseForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_warehouse':
            wh_form = WarehouseForm(request.POST)
            if wh_form.is_valid():
                wh_form.save()
                messages.success(request, 'Warehouse added.')
                return redirect('settings')
        elif action == 'toggle_warehouse':
            wh = get_object_or_404(Warehouse, pk=request.POST.get('wh_id'))
            wh.is_active = not wh.is_active
            wh.save()
            return redirect('settings')
        elif action == 'add_category':
            name = request.POST.get('cat_name', '').strip()
            if name:
                ProductCategory.objects.get_or_create(name=name)
                messages.success(request, f'Category "{name}" added.')
                return redirect('settings')
    return render(request, 'inventory/settings.html', {
        'warehouses': warehouses, 'categories': categories, 'wh_form': wh_form
    })


# ─── Profile ─────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    if request.method == 'POST':
        u = request.user
        u.first_name = request.POST.get('first_name', u.first_name)
        u.last_name = request.POST.get('last_name', u.last_name)
        u.email = request.POST.get('email', u.email)
        u.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'inventory/profile.html', {'user': request.user})
