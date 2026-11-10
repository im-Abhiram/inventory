from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from .models import ProductionEntry
from .forms import ProductionEntryForm
from products.models import Product
from inventory.models import FactoryInventory, StockTransaction
from accounts.decorators import superadmin_required


@login_required
def production_list(request):
    search_query = request.GET.get('q', '').strip()
    product_id = request.GET.get('product', '').strip()
    shift_filter = request.GET.get('shift', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    entries = ProductionEntry.objects.select_related('product', 'created_by').all()

    if search_query:
        entries = entries.filter(
            Q(product__name__icontains=search_query) |
            Q(product__code__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    if product_id:
        entries = entries.filter(product_id=product_id)

    if shift_filter:
        entries = entries.filter(shift=shift_filter)

    if date_from:
        entries = entries.filter(production_date__gte=date_from)

    if date_to:
        entries = entries.filter(production_date__lte=date_to)

    total_quantity_produced = entries.aggregate(total=Sum('quantity'))['total'] or 0

    products = Product.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(entries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'production/production_list.html', {
        'page_obj': page_obj,
        'products': products,
        'shifts': ProductionEntry.SHIFT_CHOICES,
        'total_quantity_produced': total_quantity_produced,
        'search_query': search_query,
        'selected_product': product_id,
        'selected_shift': shift_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@superadmin_required
def production_create(request):
    if request.method == 'POST':
        form = ProductionEntryForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data.get('submission_token')
            if token and ProductionEntry.objects.filter(submission_token=token).exists():
                messages.warning(request, "This production entry was already submitted. Duplicate prevented.")
                return redirect('production:production_list')

            with transaction.atomic():
                entry = form.save(commit=False)
                entry.created_by = request.user
                entry.save()

                product = entry.product
                inv, _ = FactoryInventory.objects.get_or_create(product=product)
                inv.total_production += entry.quantity
                new_balance = inv.recalculate()
                inv.save()

                StockTransaction.objects.create(
                    product=product,
                    transaction_type=StockTransaction.TYPE_PRODUCTION,
                    quantity=entry.quantity,
                    balance_after=new_balance,
                    date=entry.production_date,
                    reference=f"PROD-{entry.id}",
                    notes=f"Shift: {entry.shift} | Workers: {entry.worker_count}. {entry.notes or ''}".strip(),
                    created_by=request.user
                )

                messages.success(
                    request,
                    f"Production of {entry.quantity} {product.unit} of '{product.name}' recorded. Factory stock updated to {new_balance}."
                )
                return redirect('production:production_list')
    else:
        form = ProductionEntryForm()

    return render(request, 'production/production_form.html', {'form': form})


@login_required
def production_detail(request, entry_id):
    entry = get_object_or_404(ProductionEntry.objects.select_related('product', 'created_by'), id=entry_id)
    return render(request, 'production/production_detail.html', {'entry': entry})



@superadmin_required
def production_edit(request, entry_id):
    entry = get_object_or_404(ProductionEntry.objects.select_related('product'), id=entry_id)
    old_product = entry.product
    old_quantity = entry.quantity

    if request.method == 'POST':
        form = ProductionEntryForm(request.POST, instance=entry)
        if form.is_valid():
            with transaction.atomic():
                new_entry = form.save(commit=False)
                new_product = new_entry.product
                new_quantity = new_entry.quantity

                if old_product == new_product:
                    diff = new_quantity - old_quantity
                    inv, _ = FactoryInventory.objects.get_or_create(product=old_product)
                    if diff < 0 and (inv.current_stock + diff < 0):
                        messages.error(request, f"Cannot reduce quantity by {abs(diff)}. Current stock is only {inv.current_stock}.")
                        return render(request, 'production/production_form.html', {'form': form, 'is_edit': True, 'entry': entry})

                    inv.total_production += diff
                    new_bal = inv.recalculate()
                    inv.save()

                    if diff != 0:
                        StockTransaction.objects.create(
                            product=old_product,
                            transaction_type=StockTransaction.TYPE_ADJUSTMENT_ADD if diff > 0 else StockTransaction.TYPE_ADJUSTMENT_SUB,
                            quantity=abs(diff),
                            balance_after=new_bal,
                            date=new_entry.production_date,
                            reference=f"EDIT-PROD-{entry.id}",
                            notes=f"Production #{entry.id} revised from {old_quantity} to {new_quantity}",
                            created_by=request.user
                        )
                else:
                    old_inv, _ = FactoryInventory.objects.get_or_create(product=old_product)
                    if old_inv.current_stock < old_quantity:
                        messages.error(request, f"Cannot switch product: current stock for {old_product.name} is only {old_inv.current_stock}.")
                        return render(request, 'production/production_form.html', {'form': form, 'is_edit': True, 'entry': entry})

                    old_inv.total_production -= old_quantity
                    old_inv.recalculate()
                    old_inv.save()

                    new_inv, _ = FactoryInventory.objects.get_or_create(product=new_product)
                    new_inv.total_production += new_quantity
                    new_bal = new_inv.recalculate()
                    new_inv.save()

                    StockTransaction.objects.create(
                        product=new_product,
                        transaction_type=StockTransaction.TYPE_PRODUCTION,
                        quantity=new_quantity,
                        balance_after=new_bal,
                        date=new_entry.production_date,
                        reference=f"EDIT-PROD-{entry.id}",
                        notes=f"Production #{entry.id} product changed to {new_product.name}",
                        created_by=request.user
                    )

                new_entry.save()
                messages.success(request, f"Production entry #{entry.id} updated successfully.")
                return redirect('production:production_detail', entry_id=entry.id)
    else:
        form = ProductionEntryForm(instance=entry)

    return render(request, 'production/production_form.html', {
        'form': form,
        'is_edit': True,
        'entry': entry
    })
