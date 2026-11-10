from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, F, Sum
from django.utils import timezone
from .models import FactoryInventory, StockTransaction, StockAdjustment, ProductPurchase
from .forms import StockAdjustmentForm, ProductPurchaseForm
from products.models import Product
from accounts.decorators import superadmin_required, accountant_or_admin_required


@login_required
def inventory_list(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_id = request.GET.get('category', '').strip()

    inventories = FactoryInventory.objects.select_related('product', 'product__category').all()

    if search_query:
        inventories = inventories.filter(
            Q(product__name__icontains=search_query) |
            Q(product__code__icontains=search_query)
        )

    if category_id:
        inventories = inventories.filter(product__category_id=category_id)

    if status_filter == 'low':
        inventories = inventories.filter(current_stock__lte=F('product__minimum_stock_level'), current_stock__gt=0)
    elif status_filter == 'out':
        inventories = inventories.filter(current_stock__lte=0)
    elif status_filter == 'in_stock':
        inventories = inventories.filter(current_stock__gt=F('product__minimum_stock_level'))

    total_stock_count = sum(inv.current_stock for inv in inventories)
    low_stock_count = sum(1 for inv in inventories if inv.is_low_stock)

    paginator = Paginator(inventories, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/inventory_list.html', {
        'page_obj': page_obj,
        'total_stock_count': total_stock_count,
        'low_stock_count': low_stock_count,
        'search_query': search_query,
        'status_filter': status_filter,
    })


@superadmin_required
def inventory_adjust(request):
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                product = form.cleaned_data['product']
                adj_type = form.cleaned_data['adjustment_type']
                qty = form.cleaned_data['quantity']
                date = form.cleaned_data['date']
                reason = form.cleaned_data['reason']

                inv, _ = FactoryInventory.objects.get_or_create(product=product)

                if adj_type == 'ADD':
                    inv.total_additions += qty
                    trans_type = StockTransaction.TYPE_ADJUSTMENT_ADD
                else:
                    if inv.current_stock < qty:
                        messages.error(request, f"Cannot deduct {qty}. Current stock is only {inv.current_stock}.")
                        return render(request, 'inventory/inventory_adjust.html', {'form': form})
                    inv.total_deductions += qty
                    trans_type = StockTransaction.TYPE_ADJUSTMENT_SUB

                new_balance = inv.recalculate()
                inv.save()

                adjustment = form.save(commit=False)
                adjustment.created_by = request.user
                adjustment.save()

                StockTransaction.objects.create(
                    product=product,
                    transaction_type=trans_type,
                    quantity=qty,
                    balance_after=new_balance,
                    date=date,
                    reference=f"ADJ-{adjustment.id}",
                    notes=reason,
                    created_by=request.user
                )

                messages.success(request, f"Stock adjustment of {qty} units for '{product.name}' recorded. New balance: {new_balance}.")
                return redirect('inventory:inventory_list')
    else:
        initial_product = request.GET.get('product')
        form = StockAdjustmentForm(initial={'product': initial_product} if initial_product else None)

    return render(request, 'inventory/inventory_adjust.html', {'form': form})


@login_required
def stock_transactions(request):
    search_query = request.GET.get('q', '').strip()
    product_id = request.GET.get('product', '').strip()
    type_filter = request.GET.get('type', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    transactions = StockTransaction.objects.select_related('product', 'created_by').all()

    if search_query:
        transactions = transactions.filter(
            Q(product__name__icontains=search_query) |
            Q(reference__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    if product_id:
        transactions = transactions.filter(product_id=product_id)

    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    if date_from:
        transactions = transactions.filter(date__gte=date_from)

    if date_to:
        transactions = transactions.filter(date__lte=date_to)

    products = Product.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/transaction_list.html', {
        'page_obj': page_obj,
        'products': products,
        'types': StockTransaction.TRANSACTION_TYPES,
        'search_query': search_query,
        'selected_product': product_id,
        'selected_type': type_filter,
        'date_from': date_from,
        'date_to': date_to,
    })



def generate_purchase_number():
    date_str = timezone.now().strftime('%Y%m%d')
    count = ProductPurchase.objects.filter(purchase_number__startswith=f"PUR-{date_str}").count() + 1
    return f"PUR-{date_str}-{count:04d}"


@login_required
def purchase_list(request):
    search_query = request.GET.get('q', '').strip()
    product_id = request.GET.get('product', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    purchases = ProductPurchase.objects.select_related('product', 'created_by').all()

    if search_query:
        purchases = purchases.filter(
            Q(purchase_number__icontains=search_query) |
            Q(supplier_name__icontains=search_query) |
            Q(invoice_number__icontains=search_query) |
            Q(vehicle_number__icontains=search_query)
        )

    if product_id:
        purchases = purchases.filter(product_id=product_id)

    if status_filter:
        purchases = purchases.filter(payment_status=status_filter)

    if date_from:
        purchases = purchases.filter(purchase_date__gte=date_from)

    if date_to:
        purchases = purchases.filter(purchase_date__lte=date_to)

    total_cost = purchases.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_qty = purchases.aggregate(total=Sum('quantity'))['total'] or 0

    products = Product.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(purchases, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/purchase_list.html', {
        'page_obj': page_obj,
        'products': products,
        'statuses': ProductPurchase.PAYMENT_STATUS_CHOICES,
        'total_cost': total_cost,
        'total_qty': total_qty,
        'search_query': search_query,
        'selected_product': product_id,
        'selected_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@superadmin_required
def purchase_create(request):
    if request.method == 'POST':
        form = ProductPurchaseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.purchase_number = generate_purchase_number()
                purchase.created_by = request.user
                purchase.total_amount = Decimal(str(purchase.quantity)) * purchase.unit_price
                purchase.save()

                # Increase Factory Stock
                inv, _ = FactoryInventory.objects.get_or_create(product=purchase.product)
                inv.total_additions += purchase.quantity
                new_bal = inv.recalculate()
                inv.save()

                # Record StockTransaction of type PURCHASE
                StockTransaction.objects.create(
                    product=purchase.product,
                    transaction_type=StockTransaction.TYPE_PURCHASE,
                    quantity=purchase.quantity,
                    balance_after=new_bal,
                    date=purchase.purchase_date,
                    reference=purchase.purchase_number,
                    notes=f"Vendor: {purchase.supplier_name} | Invoice: {purchase.invoice_number or 'N/A'}",
                    created_by=request.user
                )

                messages.success(
                    request,
                    f"Product purchase {purchase.purchase_number} of {purchase.quantity} {purchase.product.unit} recorded. Factory stock increased to {new_bal}."
                )
                return redirect('inventory:purchase_detail', purchase_id=purchase.id)
    else:
        initial_prod = request.GET.get('product')
        form = ProductPurchaseForm(initial={'product': initial_prod} if initial_prod else None)

    return render(request, 'inventory/purchase_form.html', {'form': form})


@login_required
def purchase_detail(request, purchase_id):
    purchase = get_object_or_404(ProductPurchase.objects.select_related('product', 'created_by'), id=purchase_id)
    return render(request, 'inventory/purchase_detail.html', {'purchase': purchase})
