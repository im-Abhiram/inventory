from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
from .models import Client
from .forms import ClientForm
from accounts.decorators import superadmin_required
from construction.models import ClientProject, ClientInventory, DailyConstructionEntry


@login_required
def client_list(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    credit_filter = request.GET.get('credit', '').strip()

    clients = Client.objects.select_related('account').all().order_by('name')

    if search_query:
        clients = clients.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    if status_filter == 'active':
        clients = clients.filter(is_active=True)
    elif status_filter == 'inactive':
        clients = clients.filter(is_active=False)

    client_items = list(clients)
    if credit_filter == 'exceeded':
        client_items = [c for c in client_items if c.is_credit_exceeded]
    elif credit_filter == 'available':
        client_items = [c for c in client_items if not c.is_credit_exceeded]

    paginator = Paginator(client_items, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clients/client_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'credit_filter': credit_filter,
    })


@login_required
def client_detail(request, client_id):
    client = get_object_or_404(Client.objects.select_related('account'), id=client_id)
    active_tab = request.GET.get('tab', 'overview')

    # Ensure account balance is fresh
    if hasattr(client, 'account'):
        client.account.recalculate()

    dispatches = client.dispatches.select_related('project').prefetch_related('items', 'items__product').order_by('-dispatch_date', '-created_at')
    projects = client.projects.all().order_by('-created_at')
    material_inventories = ClientInventory.objects.filter(project__client=client).select_related('project', 'product')
    daily_entries = DailyConstructionEntry.objects.filter(project__client=client).select_related('project', 'created_by').prefetch_related('material_usages', 'material_usages__product').order_by('-date', '-created_at')
    payments = client.payments.select_related('recorded_by').prefetch_related('allocations', 'allocations__dispatch').order_by('-payment_date', '-created_at')

    return render(request, 'clients/client_detail.html', {
        'client': client,
        'active_tab': active_tab,
        'dispatches': dispatches,
        'projects': projects,
        'material_inventories': material_inventories,
        'daily_entries': daily_entries,
        'payments': payments,
    })


@superadmin_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client '{client.name}' created successfully.")
            return redirect('clients:client_detail', client_id=client.id)
    else:
        form = ClientForm()

    return render(request, 'clients/client_form.html', {
        'form': form,
        'title': 'Add New Client'
    })


@superadmin_required
def client_edit(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            if hasattr(client, 'account'):
                client.account.recalculate()
            messages.success(request, f"Client '{client.name}' updated successfully.")
            return redirect('clients:client_detail', client_id=client.id)
    else:
        form = ClientForm(instance=client)

    return render(request, 'clients/client_form.html', {
        'form': form,
        'title': f'Edit Client: {client.name}',
        'client': client
    })


@superadmin_required
def client_toggle_status(request, client_id):
    if request.method == 'POST':
        client = get_object_or_404(Client, id=client_id)
        client.is_active = not client.is_active
        client.save(update_fields=['is_active'])
        status_text = "activated" if client.is_active else "deactivated"
        messages.success(request, f"Client '{client.name}' was {status_text}.")
    return redirect('clients:client_list')
