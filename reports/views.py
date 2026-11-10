import csv
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from products.models import Product, ProductCategory
from inventory.models import FactoryInventory, StockTransaction
from production.models import ProductionEntry
from clients.models import Client
from dispatch.models import Dispatch, DispatchItem
from construction.models import ClientProject, ClientInventory, DailyConstructionEntry, DailyMaterialUsage
from finance.models import Payment, Expense, ExpenseCategory, ClientAccount
from workers.models import Worker, WorkerAttendance


@login_required
def reports_index(request):
    return render(request, 'reports/reports_index.html')


@login_required
def inventory_report(request):
    status_filter = request.GET.get('status', '').strip()
    export_csv = request.GET.get('export', '') == 'csv'

    inventories = FactoryInventory.objects.select_related('product').all()

    if status_filter == 'low':
        inventories = inventories.filter(current_stock__lte=F('product__minimum_stock_level'), current_stock__gt=0)
    elif status_filter == 'out':
        inventories = inventories.filter(current_stock__lte=0)

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="factory_inventory_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Product Name', 'Code', 'Opening Stock', 'Production', 'Additions', 'Dispatch', 'Current Stock', 'Min Level', 'Status', 'Unit'])
        for inv in inventories:
            writer.writerow([
                inv.product.name,
                inv.product.code,
                inv.opening_stock,
                inv.total_production,
                inv.total_additions,
                inv.total_dispatch,
                inv.current_stock,
                inv.product.minimum_stock_level,
                inv.stock_status,
                inv.product.unit
            ])
        return response

    total_stock = sum(inv.current_stock for inv in inventories)
    low_stock_count = sum(1 for inv in inventories if inv.is_low_stock)

    return render(request, 'reports/inventory_report.html', {
        'inventories': inventories,
        'selected_status': status_filter,
        'total_stock': total_stock,
        'low_stock_count': low_stock_count,
    })


@login_required
def stock_movement_report(request):
    product_id = request.GET.get('product', '').strip()
    type_filter = request.GET.get('type', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    export_csv = request.GET.get('export', '') == 'csv'

    transactions = StockTransaction.objects.select_related('product', 'created_by').all()

    if product_id:
        transactions = transactions.filter(product_id=product_id)
    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="stock_movements_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Product', 'Transaction Type', 'Quantity', 'Balance After', 'Reference', 'Notes', 'Created By'])
        for t in transactions:
            writer.writerow([
                t.date,
                t.product.name,
                t.get_transaction_type_display(),
                t.quantity,
                t.balance_after,
                t.reference or '',
                t.notes or '',
                t.created_by.username if t.created_by else ''
            ])
        return response

    products = Product.objects.filter(is_active=True).order_by('name')

    return render(request, 'reports/stock_movement_report.html', {
        'transactions': transactions[:100],
        'products': products,
        'types': StockTransaction.TRANSACTION_TYPES,
        'selected_product': product_id,
        'selected_type': type_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def production_report(request):
    product_id = request.GET.get('product', '').strip()
    shift_filter = request.GET.get('shift', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    export_csv = request.GET.get('export', '') == 'csv'

    entries = ProductionEntry.objects.select_related('product', 'created_by').all()

    if product_id:
        entries = entries.filter(product_id=product_id)
    if shift_filter:
        entries = entries.filter(shift=shift_filter)
    if date_from:
        entries = entries.filter(production_date__gte=date_from)
    if date_to:
        entries = entries.filter(production_date__lte=date_to)

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="production_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Product', 'Quantity', 'Unit', 'Shift', 'Workers', 'Notes', 'Created By'])
        for e in entries:
            writer.writerow([
                e.production_date,
                e.product.name,
                e.quantity,
                e.product.unit,
                e.shift,
                e.worker_count,
                e.notes or '',
                e.created_by.username if e.created_by else ''
            ])
        return response

    total_qty = entries.aggregate(total=Sum('quantity'))['total'] or 0
    products = Product.objects.filter(is_active=True).order_by('name')

    # Product breakdown
    product_breakdown = (
        entries.values('product__name', 'product__unit')
        .annotate(total_produced=Sum('quantity'), total_shifts=Count('id'))
        .order_by('-total_produced')
    )

    return render(request, 'reports/production_report.html', {
        'entries': entries[:100],
        'products': products,
        'shifts': ProductionEntry.SHIFT_CHOICES,
        'total_qty': total_qty,
        'product_breakdown': product_breakdown,
        'selected_product': product_id,
        'selected_shift': shift_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def financial_summary_report(request):
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
    export_csv = request.GET.get('export', '') == 'csv'

    dispatches = Dispatch.objects.filter(dispatch_date__gte=date_from, dispatch_date__lte=date_to)
    payments = Payment.objects.filter(payment_date__gte=date_from, payment_date__lte=date_to)
    expenses = Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)

    total_revenue_billed = dispatches.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_payments_collected = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_expenses_incurred = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    net_operating_cash = total_payments_collected - total_expenses_incurred

    category_expenses = (
        expenses.values('category__name')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="financial_summary_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Financial Summary', f'{date_from} to {date_to}'])
        writer.writerow([])
        writer.writerow(['Metric', 'Amount (INR)'])
        writer.writerow(['Total Invoiced / Dispatched', total_revenue_billed])
        writer.writerow(['Total Cash Payments Collected', total_payments_collected])
        writer.writerow(['Total Operating Expenses', total_expenses_incurred])
        writer.writerow(['Net Operating Cashflow', net_operating_cash])
        writer.writerow([])
        writer.writerow(['Expense Breakdown by Category'])
        writer.writerow(['Category', 'Total Spent'])
        for cat in category_expenses:
            writer.writerow([cat['category__name'], cat['total']])
        return response

    return render(request, 'reports/financial_summary_report.html', {
        'total_revenue_billed': total_revenue_billed,
        'total_payments_collected': total_payments_collected,
        'total_expenses_incurred': total_expenses_incurred,
        'net_operating_cash': net_operating_cash,
        'category_expenses': category_expenses,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def client_credit_report(request):
    export_csv = request.GET.get('export', '') == 'csv'
    clients = Client.objects.select_related('account').filter(is_active=True).order_by('name')

    for c in clients:
        if hasattr(c, 'account'):
            c.account.recalculate()

    client_data = list(clients)
    total_credit_limit = sum(c.credit_limit for c in client_data)
    total_outstanding = sum(c.outstanding_balance for c in client_data)

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="client_credit_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Client Name', 'Code', 'Phone', 'Credit Limit', 'Outstanding Balance', 'Available Credit', 'Credit Exceeded'])
        for c in client_data:
            writer.writerow([
                c.name,
                c.code,
                c.phone,
                c.credit_limit,
                c.outstanding_balance,
                c.available_credit,
                'YES' if c.is_credit_exceeded else 'NO'
            ])
        return response

    return render(request, 'reports/client_credit_report.html', {
        'clients': client_data,
        'total_credit_limit': total_credit_limit,
        'total_outstanding': total_outstanding,
    })


@login_required
def construction_report(request):
    project_id = request.GET.get('project', '').strip()
    status_filter = request.GET.get('status', '').strip()
    export_csv = request.GET.get('export', '') == 'csv'

    projects = ClientProject.objects.select_related('client').prefetch_related('material_inventories', 'material_inventories__product', 'daily_entries').all()

    if project_id:
        projects = projects.filter(id=project_id)

    if status_filter:
        projects = projects.filter(status=status_filter)

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="construction_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Project Name', 'Client', 'Location', 'Status', 'Start Date', 'Progress %', 'Total Worker Days'])
        for p in projects:
            writer.writerow([
                p.name,
                p.client.name,
                p.location or '',
                p.status,
                p.start_date,
                f"{p.latest_progress}%",
                p.total_worker_days
            ])
        return response

    all_projects = ClientProject.objects.all().order_by('name')

    return render(request, 'reports/construction_report.html', {
        'projects': projects,
        'all_projects': all_projects,
        'statuses': ClientProject.STATUS_CHOICES,
        'selected_project': project_id,
        'selected_status': status_filter,
    })



@login_required
def dispatch_report(request):
    client_id = request.GET.get('client', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    export_csv = request.GET.get('export', '') == 'csv'

    dispatches = Dispatch.objects.select_related('client', 'project', 'created_by').prefetch_related('items', 'items__product').all()

    if client_id:
        dispatches = dispatches.filter(client_id=client_id)
    if status_filter:
        dispatches = dispatches.filter(payment_status=status_filter)
    if date_from:
        dispatches = dispatches.filter(dispatch_date__gte=date_from)
    if date_to:
        dispatches = dispatches.filter(dispatch_date__lte=date_to)

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="dispatch_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Dispatch #', 'Date', 'Client', 'Project Site', 'Vehicle #', 'Driver', 'Total Amount', 'Paid Amount', 'Balance Due', 'Status'])
        for d in dispatches:
            writer.writerow([
                d.dispatch_number,
                d.dispatch_date,
                d.client.name,
                d.project.name if d.project else 'Direct Delivery',
                d.vehicle_number or '',
                d.driver_name or '',
                d.total_amount,
                d.paid_amount,
                d.outstanding_amount,
                d.payment_status
            ])
        return response

    clients = Client.objects.filter(is_active=True).order_by('name')
    total_amount = dispatches.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_paid = dispatches.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
    total_due = total_amount - total_paid

    return render(request, 'reports/dispatch_report.html', {
        'dispatches': dispatches[:100],
        'clients': clients,
        'statuses': Dispatch.PAYMENT_STATUS_CHOICES,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_due': total_due,
        'selected_client': client_id,
        'selected_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    })
