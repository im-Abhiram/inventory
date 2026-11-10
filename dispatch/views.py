import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
from .models import Dispatch, DispatchItem
from .forms import DispatchForm, DispatchItemFormSet
from products.models import Product
from clients.models import Client
from inventory.models import FactoryInventory, StockTransaction
from construction.models import ClientInventory, ClientStockTransaction
from accounts.decorators import superadmin_required


def generate_dispatch_number():
    date_str = timezone.now().strftime('%Y%m%d')
    count = Dispatch.objects.filter(dispatch_number__startswith=f"DSP-{date_str}").count() + 1
    return f"DSP-{date_str}-{count:04d}"


@login_required
def dispatch_list(request):
    search_query = request.GET.get('q', '').strip()
    client_id = request.GET.get('client', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    dispatches = Dispatch.objects.select_related('client', 'project', 'created_by').all()

    if search_query:
        dispatches = dispatches.filter(
            Q(dispatch_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(vehicle_number__icontains=search_query) |
            Q(driver_name__icontains=search_query)
        )

    if client_id:
        dispatches = dispatches.filter(client_id=client_id)

    if status_filter:
        dispatches = dispatches.filter(payment_status=status_filter)

    if date_from:
        dispatches = dispatches.filter(dispatch_date__gte=date_from)

    if date_to:
        dispatches = dispatches.filter(dispatch_date__lte=date_to)

    total_dispatched_amount = dispatches.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    clients = Client.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(dispatches, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dispatch/dispatch_list.html', {
        'page_obj': page_obj,
        'clients': clients,
        'statuses': Dispatch.PAYMENT_STATUS_CHOICES,
        'total_dispatched_amount': total_dispatched_amount,
        'search_query': search_query,
        'selected_client': client_id,
        'selected_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@superadmin_required
def dispatch_create(request):
    if request.method == 'POST':
        form = DispatchForm(request.POST)
        formset = DispatchItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                dispatch = form.save(commit=False)
                dispatch.dispatch_number = generate_dispatch_number()
                dispatch.created_by = request.user
                dispatch.total_amount = Decimal('0.00')
                dispatch.save()

                formset.instance = dispatch
                items = formset.save(commit=False)

                total_amount = Decimal('0.00')
                for item in items:
                    item_total = Decimal(str(item.quantity)) * item.unit_price
                    item.total_price = item_total
                    item.save()
                    total_amount += item_total

                    # Deduct from Factory Inventory
                    factory_inv, _ = FactoryInventory.objects.get_or_create(product=item.product)
                    if factory_inv.current_stock < item.quantity:
                        raise ValueError(f"Stock error: Not enough stock for {item.product.name}")

                    factory_inv.total_dispatch += item.quantity
                    new_factory_stock = factory_inv.recalculate()
                    factory_inv.save()

                    StockTransaction.objects.create(
                        product=item.product,
                        transaction_type=StockTransaction.TYPE_DISPATCH,
                        quantity=item.quantity,
                        balance_after=new_factory_stock,
                        date=dispatch.dispatch_date,
                        reference=dispatch.dispatch_number,
                        notes=f"Dispatched to {dispatch.client.name} | Vehicle: {dispatch.vehicle_number or 'N/A'}",
                        created_by=request.user
                    )

                    # If assigned to a client construction project, increase project site stock
                    if dispatch.project:
                        client_inv, _ = ClientInventory.objects.get_or_create(
                            project=dispatch.project,
                            product=item.product
                        )
                        client_inv.total_received += item.quantity
                        new_client_stock = client_inv.recalculate()
                        client_inv.save()

                        ClientStockTransaction.objects.create(
                            project=dispatch.project,
                            product=item.product,
                            transaction_type=ClientStockTransaction.TYPE_RECEIVED,
                            quantity=item.quantity,
                            balance_after=new_client_stock,
                            date=dispatch.dispatch_date,
                            reference=dispatch.dispatch_number,
                            notes=f"Received via dispatch {dispatch.dispatch_number}",
                            created_by=request.user
                        )

                dispatch.total_amount = total_amount
                dispatch.save()

                # Recalculate client's financial account
                if hasattr(dispatch.client, 'account'):
                    dispatch.client.account.recalculate()

                messages.success(
                    request,
                    f"Dispatch {dispatch.dispatch_number} for {dispatch.client.name} (₹{total_amount}) recorded successfully."
                )
                return redirect('dispatch:dispatch_detail', dispatch_id=dispatch.id)
    else:
        initial_client = request.GET.get('client')
        form = DispatchForm(initial={'client': initial_client} if initial_client else None)
        formset = DispatchItemFormSet()

    products = Product.objects.filter(is_active=True).values('id', 'name', 'selling_price', 'inventory__current_stock', 'unit')
    return render(request, 'dispatch/dispatch_form.html', {
        'form': form,
        'formset': formset,
        'products_data': list(products),
    })


@login_required
def dispatch_detail(request, dispatch_id):
    dispatch = get_object_or_404(
        Dispatch.objects.select_related('client', 'project', 'created_by').prefetch_related('items', 'items__product'),
        id=dispatch_id
    )
    return render(request, 'dispatch/dispatch_detail.html', {'dispatch': dispatch})


@login_required
def dispatch_receipt(request, dispatch_id):
    dispatch = get_object_or_404(
        Dispatch.objects.select_related('client', 'project', 'created_by').prefetch_related('items', 'items__product'),
        id=dispatch_id
    )
    return render(request, 'dispatch/dispatch_receipt.html', {'dispatch': dispatch})
