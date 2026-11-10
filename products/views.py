from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Product
from .forms import ProductForm
from accounts.decorators import superadmin_required


@login_required
def product_list(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    products = Product.objects.select_related('inventory').all().order_by('name')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)

    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'products/product_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status_filter,
    })


@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related('inventory'), id=product_id)
    recent_transactions = product.stock_transactions.select_related('created_by')[:10]
    recent_productions = product.production_entries.order_by('-production_date', '-created_at')[:5]
    recent_dispatches = product.dispatch_items.select_related('dispatch', 'dispatch__client').order_by('-dispatch__dispatch_date')[:5]

    return render(request, 'products/product_detail.html', {
        'product': product,
        'recent_transactions': recent_transactions,
        'recent_productions': recent_productions,
        'recent_dispatches': recent_dispatches,
    })


@superadmin_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect('products:product_detail', product_id=product.id)
    else:
        form = ProductForm()

    return render(request, 'products/product_form.html', {
        'form': form,
        'title': 'Add New Product'
    })


@superadmin_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('products:product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)

    return render(request, 'products/product_form.html', {
        'form': form,
        'title': f'Edit Product: {product.name}',
        'product': product
    })


@superadmin_required
def product_toggle_status(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        product.is_active = not product.is_active
        product.save(update_fields=['is_active'])
        status_text = "activated" if product.is_active else "deactivated"
        messages.success(request, f"Product '{product.name}' was {status_text}.")
    return redirect('products:product_list')
