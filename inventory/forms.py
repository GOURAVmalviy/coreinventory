from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    Product, ProductCategory, Warehouse,
    Receipt, ReceiptLine,
    DeliveryOrder, DeliveryLine,
    InternalTransfer, TransferLine,
    StockAdjustment,
)


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username', 'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class OTPRequestForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter your registered email'}))


class OTPVerifyForm(forms.Form):
    token = forms.CharField(max_length=6, widget=forms.TextInput(attrs={'placeholder': '6-digit OTP', 'autocomplete': 'off'}))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'New Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'unit_of_measure', 'min_stock']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Steel Rods'}),
            'sku': forms.TextInput(attrs={'placeholder': 'e.g. STL-001'}),
            'unit_of_measure': forms.TextInput(attrs={'placeholder': 'kg / pcs / m'}),
        }


class InitialStockForm(forms.Form):
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True))
    initial_qty = forms.DecimalField(min_value=0, decimal_places=2, required=False, initial=0,
                                      widget=forms.NumberInput(attrs={'placeholder': '0', 'step': '0.01'}))


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'location', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Main Warehouse'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g. Bengaluru, KA'}),
        }


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['supplier', 'warehouse', 'scheduled_date', 'notes', 'status']
        widgets = {
            'supplier': forms.TextInput(attrs={'placeholder': 'e.g. Tata Steel'}),
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes...'}),
        }


class ReceiptLineForm(forms.ModelForm):
    class Meta:
        model = ReceiptLine
        fields = ['product', 'expected_qty', 'received_qty']
        widgets = {
            'expected_qty': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'received_qty': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


ReceiptLineFormSet = forms.inlineformset_factory(
    Receipt, ReceiptLine, form=ReceiptLineForm,
    extra=1, can_delete=True
)


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = DeliveryOrder
        fields = ['customer', 'warehouse', 'scheduled_date', 'notes', 'status']
        widgets = {
            'customer': forms.TextInput(attrs={'placeholder': 'e.g. Acme Corp'}),
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes...'}),
        }


class DeliveryLineForm(forms.ModelForm):
    class Meta:
        model = DeliveryLine
        fields = ['product', 'demand_qty', 'done_qty']
        widgets = {
            'demand_qty': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'done_qty': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


DeliveryLineFormSet = forms.inlineformset_factory(
    DeliveryOrder, DeliveryLine, form=DeliveryLineForm,
    extra=1, can_delete=True
)


class TransferForm(forms.ModelForm):
    class Meta:
        model = InternalTransfer
        fields = ['from_warehouse', 'to_warehouse', 'scheduled_date', 'notes', 'status']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes...'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('from_warehouse') == cleaned.get('to_warehouse'):
            raise forms.ValidationError('Source and destination warehouses must be different.')
        return cleaned


class TransferLineForm(forms.ModelForm):
    class Meta:
        model = TransferLine
        fields = ['product', 'quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


TransferLineFormSet = forms.inlineformset_factory(
    InternalTransfer, TransferLine, form=TransferLineForm,
    extra=1, can_delete=True
)


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['product', 'warehouse', 'counted_qty', 'reason']
        widgets = {
            'counted_qty': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'reason': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Reason for adjustment (optional)'}),
        }
