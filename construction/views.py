from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from decimal import Decimal
from .models import ClientProject, ClientInventory, ClientStockTransaction, DailyConstructionEntry, DailyMaterialUsage
from .forms import ClientProjectForm, DailyConstructionEntryForm, DailyMaterialUsageFormSet
from clients.models import Client
from products.models import Product
from accounts.decorators import superadmin_required


@login_required
def project_list(request):
    search_query = request.GET.get('q', '').strip()
    client_id = request.GET.get('client', '').strip()
    status_filter = request.GET.get('status', '').strip()

    projects = ClientProject.objects.select_related('client').all()

    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(client__name__icontains=search_query)
        )

    if client_id:
        projects = projects.filter(client_id=client_id)

    if status_filter:
        projects = projects.filter(status=status_filter)

    clients = Client.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(projects, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'construction/project_list.html', {
        'page_obj': page_obj,
        'clients': clients,
        'statuses': ClientProject.STATUS_CHOICES,
        'search_query': search_query,
        'selected_client': client_id,
        'selected_status': status_filter,
    })


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(ClientProject.objects.select_related('client'), id=project_id)
    active_tab = request.GET.get('tab', 'overview')

    material_inventories = project.material_inventories.select_related('product').all()
    daily_entries = project.daily_entries.prefetch_related('material_usages', 'material_usages__product').order_by('-date', '-created_at')
    dispatches = project.dispatches.prefetch_related('items', 'items__product').order_by('-dispatch_date')
    stock_transactions = project.stock_transactions.select_related('product', 'created_by').order_by('-date', '-created_at')[:20]

    total_workers_employed = daily_entries.aggregate(total=Sum('number_of_workers'))['total'] or 0
    total_materials_received = sum(inv.total_received for inv in material_inventories)
    total_materials_used = sum(inv.total_used for inv in material_inventories)
    total_materials_remaining = sum(inv.current_stock for inv in material_inventories)

    return render(request, 'construction/project_detail.html', {
        'project': project,
        'active_tab': active_tab,
        'material_inventories': material_inventories,
        'daily_entries': daily_entries,
        'dispatches': dispatches,
        'stock_transactions': stock_transactions,
        'total_workers_employed': total_workers_employed,
        'total_materials_received': total_materials_received,
        'total_materials_used': total_materials_used,
        'total_materials_remaining': total_materials_remaining,
    })


@superadmin_required
def project_create(request):
    if request.method == 'POST':
        form = ClientProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f"Project '{project.name}' for {project.client.name} created successfully.")
            return redirect('construction:project_detail', project_id=project.id)
    else:
        initial_client = request.GET.get('client')
        form = ClientProjectForm(initial={'client': initial_client} if initial_client else None)

    return render(request, 'construction/project_form.html', {
        'form': form,
        'title': 'Create Construction Project'
    })


@superadmin_required
def project_edit(request, project_id):
    project = get_object_or_404(ClientProject, id=project_id)
    if request.method == 'POST':
        form = ClientProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Project '{project.name}' updated successfully.")
            return redirect('construction:project_detail', project_id=project.id)
    else:
        form = ClientProjectForm(instance=project)

    return render(request, 'construction/project_form.html', {
        'form': form,
        'title': f'Edit Project: {project.name}',
        'project': project
    })


@superadmin_required
def daily_entry_create(request, project_id):
    project = get_object_or_404(ClientProject.objects.select_related('client'), id=project_id)

    if request.method == 'POST':
        form = DailyConstructionEntryForm(request.POST)
        formset = DailyMaterialUsageFormSet(request.POST, project=project)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.project = project
                entry.created_by = request.user
                entry.save()

                formset.instance = entry
                usages = formset.save(commit=False)

                for usage in usages:
                    usage.unit = usage.product.unit
                    usage.save()

                    # Deduct from ClientInventory at project site
                    client_inv, _ = ClientInventory.objects.get_or_create(
                        project=project,
                        product=usage.product
                    )
                    if client_inv.current_stock < usage.quantity_used:
                        raise ValueError(f"Site stock error: Not enough stock for {usage.product.name}")

                    client_inv.total_used += usage.quantity_used
                    new_client_stock = client_inv.recalculate()
                    client_inv.save()

                    # Create ClientStockTransaction
                    ClientStockTransaction.objects.create(
                        project=project,
                        product=usage.product,
                        transaction_type=ClientStockTransaction.TYPE_USAGE,
                        quantity=usage.quantity_used,
                        balance_after=new_client_stock,
                        date=entry.date,
                        reference=f"DAILY-{entry.id}",
                        notes=f"Used on site: {usage.notes or ''}".strip(),
                        created_by=request.user
                    )
                    # NOTE: Factory stock is NOT modified. It was reduced when dispatched.

                messages.success(
                    request,
                    f"Daily progress and material usage for {project.name} on {entry.date} recorded successfully."
                )
                return redirect('construction:project_detail', project_id=project.id)
    else:
        form = DailyConstructionEntryForm()
        formset = DailyMaterialUsageFormSet(project=project)

    # Available site stock for quick reference
    site_stock = ClientInventory.objects.filter(project=project).select_related('product')

    return render(request, 'construction/daily_entry_form.html', {
        'project': project,
        'form': form,
        'formset': formset,
        'site_stock': site_stock,
    })


@login_required
def daily_entry_detail(request, entry_id):
    entry = get_object_or_404(
        DailyConstructionEntry.objects.select_related('project', 'project__client', 'created_by').prefetch_related('material_usages', 'material_usages__product'),
        id=entry_id
    )
    return render(request, 'construction/daily_entry_detail.html', {'entry': entry})
