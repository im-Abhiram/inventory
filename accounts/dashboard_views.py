import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta, datetime
from decimal import Decimal

from .decorators import get_user_role
from products.models import Product
from inventory.models import FactoryInventory
from production.models import ProductionEntry
from clients.models import Client
from dispatch.models import Dispatch, DispatchItem
from construction.models import ClientProject, ClientInventory, DailyConstructionEntry, DailyMaterialUsage
from finance.models import Payment, Expense, ClientAccount
from workers.models import WorkerAttendance


@login_required
def dashboard_view(request):
    role = get_user_role(request.user)
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    if role == 'accountant':
        # --- Accountant Dashboard ---
        # Outstanding credit
        all_accounts = ClientAccount.objects.select_related('client').filter(client__is_active=True)
        total_outstanding = sum((acc.current_balance or Decimal('0.00')) for acc in all_accounts if (acc.current_balance or Decimal('0.00')) > Decimal('0.00'))
        
        # Today's payments
        today_payments = Payment.objects.filter(payment_date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Monthly payments
        month_payments = Payment.objects.filter(payment_date__gte=start_of_month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Total expenses
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        month_expenses = Expense.objects.filter(expense_date__gte=start_of_month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Client balances
        clients_with_balance = [acc for acc in all_accounts if (acc.current_balance or Decimal('0.00')) > Decimal('0.00')]
        clients_with_balance.sort(key=lambda x: (x.current_balance or Decimal('0.00')), reverse=True)

        recent_payments = Payment.objects.select_related('client', 'recorded_by').order_by('-payment_date', '-created_at')[:10]

        context = {
            'role': role,
            'total_outstanding': total_outstanding,
            'today_payments': today_payments,
            'month_payments': month_payments,
            'total_expenses': total_expenses,
            'month_expenses': month_expenses,
            'clients_with_balance': clients_with_balance[:10],
            'recent_payments': recent_payments,
        }
        return render(request, 'accounts/dashboard_accountant.html', context)

    elif role == 'owner':
        # --- Owner Dashboard (Read-Only with Date Filter) ---
        filter_mode = request.GET.get('period', 'this_month')
        date_from_str = request.GET.get('date_from', '')
        date_to_str = request.GET.get('date_to', '')

        if filter_mode == 'today':
            filter_from = today
            filter_to = today
        elif filter_mode == 'this_week':
            filter_from = today - timedelta(days=today.weekday())
            filter_to = today
        elif filter_mode == 'custom' and date_from_str and date_to_str:
            try:
                filter_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                filter_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            except ValueError:
                filter_from = start_of_month
                filter_to = today
        else:
            filter_mode = 'this_month'
            filter_from = start_of_month
            filter_to = today

        # Business stats in filtered range
        prod_qty = ProductionEntry.objects.filter(production_date__gte=filter_from, production_date__lte=filter_to).aggregate(total=Sum('quantity'))['total'] or 0
        disp_rev = Dispatch.objects.filter(dispatch_date__gte=filter_from, dispatch_date__lte=filter_to).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        disp_count = Dispatch.objects.filter(dispatch_date__gte=filter_from, dispatch_date__lte=filter_to).count()
        pay_received = Payment.objects.filter(payment_date__gte=filter_from, payment_date__lte=filter_to).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        exp_incurred = Expense.objects.filter(expense_date__gte=filter_from, expense_date__lte=filter_to).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Overall current snapshots
        factory_stock_total = FactoryInventory.objects.aggregate(total=Sum('current_stock'))['total'] or 0
        client_stock_total = ClientInventory.objects.aggregate(total=Sum('current_stock'))['total'] or 0
        active_projects_count = ClientProject.objects.filter(status='Active').count()
        total_outstanding = ClientAccount.objects.aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')

        context = {
            'role': role,
            'filter_mode': filter_mode,
            'filter_from': filter_from,
            'filter_to': filter_to,
            'prod_qty': prod_qty,
            'disp_rev': disp_rev,
            'disp_count': disp_count,
            'pay_received': pay_received,
            'exp_incurred': exp_incurred,
            'net_cashflow': pay_received - exp_incurred,
            'factory_stock_total': factory_stock_total,
            'client_stock_total': client_stock_total,
            'active_projects_count': active_projects_count,
            'total_outstanding': total_outstanding,
        }
        return render(request, 'accounts/dashboard_owner.html', context)

    else:
        # --- Super Admin Dashboard (Dynamic Date Filtering + Accurate KPIs + Charts + Activities) ---
        filter_mode = request.GET.get('period', 'this_month')
        date_from_str = request.GET.get('date_from', '')
        date_to_str = request.GET.get('date_to', '')

        if filter_mode == 'today':
            filter_from = today
            filter_to = today
        elif filter_mode == 'this_week':
            filter_from = today - timedelta(days=today.weekday())
            filter_to = today
        elif filter_mode == 'all_time':
            filter_from = today - timedelta(days=365 * 10)
            filter_to = today
        elif filter_mode == 'custom' and date_from_str and date_to_str:
            try:
                filter_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                filter_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            except ValueError:
                filter_from = start_of_month
                filter_to = today
        else:
            filter_mode = 'this_month'
            filter_from = start_of_month
            filter_to = today

        # 1. Products & Factory Stock
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()

        # Ensure all products have synced FactoryInventory
        for prod in Product.objects.all():
            inv, _ = FactoryInventory.objects.get_or_create(product=prod)
            inv.recalculate()
            inv.save(update_fields=['current_stock'])

        total_factory_stock = FactoryInventory.objects.aggregate(total=Sum('current_stock'))['total'] or 0
        total_opening_stock = FactoryInventory.objects.aggregate(total=Sum('opening_stock'))['total'] or 0
        all_time_production = FactoryInventory.objects.aggregate(total=Sum('total_production'))['total'] or 0
        all_time_dispatch = FactoryInventory.objects.aggregate(total=Sum('total_dispatch'))['total'] or 0

        # 2. Production
        period_production = ProductionEntry.objects.filter(
            production_date__gte=filter_from, production_date__lte=filter_to
        ).aggregate(total=Sum('quantity'))['total'] or 0
        today_production = ProductionEntry.objects.filter(production_date=today).aggregate(total=Sum('quantity'))['total'] or 0

        # 3. Dispatches
        period_dispatches_qs = Dispatch.objects.filter(dispatch_date__gte=filter_from, dispatch_date__lte=filter_to)
        period_dispatch_count = period_dispatches_qs.count()
        period_dispatch_amount = period_dispatches_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        period_dispatch_qty = DispatchItem.objects.filter(
            dispatch__dispatch_date__gte=filter_from, dispatch__dispatch_date__lte=filter_to
        ).aggregate(total=Sum('quantity'))['total'] or 0

        today_dispatches_qs = Dispatch.objects.filter(dispatch_date=today)
        today_dispatch_count = today_dispatches_qs.count()
        today_dispatch_amount = today_dispatches_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        today_dispatch_qty = DispatchItem.objects.filter(dispatch__dispatch_date=today).aggregate(total=Sum('quantity'))['total'] or 0

        # 4. Clients & Projects
        total_clients = Client.objects.count()
        active_clients = Client.objects.filter(is_active=True).count()
        active_projects = ClientProject.objects.filter(status='Active').count()
        total_projects = ClientProject.objects.count()

        # Recalculate client material inventory for accuracy
        for cinv in ClientInventory.objects.all():
            cinv.recalculate()
            cinv.save(update_fields=['current_stock'])
        total_client_material_stock = ClientInventory.objects.aggregate(total=Sum('current_stock'))['total'] or 0

        # 5. Site Usage & Workers
        period_usage = DailyMaterialUsage.objects.filter(
            entry__date__gte=filter_from, entry__date__lte=filter_to
        ).aggregate(total=Sum('quantity_used'))['total'] or 0
        today_usage = DailyMaterialUsage.objects.filter(entry__date=today).aggregate(total=Sum('quantity_used'))['total'] or 0

        total_workers = WorkerAttendance.objects.filter(date=today).count()
        from workers.models import Worker
        total_registered_workers = Worker.objects.filter(is_active=True).count()
        today_workers = WorkerAttendance.objects.filter(date=today, status__in=['Present', 'Half Day']).count()

        # 6. Finance & Outstanding Credit
        all_accounts = ClientAccount.objects.select_related('client').filter(client__is_active=True)
        for acc in all_accounts:
            acc.recalculate()
        total_outstanding = sum(
            (acc.current_balance or Decimal('0.00'))
            for acc in all_accounts
            if (acc.current_balance or Decimal('0.00')) > Decimal('0.00')
        )

        period_payments = Payment.objects.filter(
            payment_date__gte=filter_from, payment_date__lte=filter_to
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        today_payments = Payment.objects.filter(payment_date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        period_expenses = Expense.objects.filter(
            expense_date__gte=filter_from, expense_date__lte=filter_to
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Recent activities
        recent_productions = ProductionEntry.objects.select_related('product', 'created_by').order_by('-production_date', '-created_at')[:5]
        recent_dispatches = Dispatch.objects.select_related('client', 'project').order_by('-dispatch_date', '-created_at')[:5]
        recent_payments = Payment.objects.select_related('client', 'recorded_by').order_by('-payment_date', '-created_at')[:5]
        recent_construction_entries = DailyConstructionEntry.objects.select_related('project', 'project__client').order_by('-date', '-created_at')[:5]

        # Chart Data: Dynamic range based on selected filter
        chart_days = min(14, max(7, (filter_to - filter_from).days + 1)) if filter_mode != 'all_time' else 14
        chart_labels = []
        production_data = []
        dispatch_data = []
        for i in range(chart_days - 1, -1, -1):
            day = filter_to - timedelta(days=i)
            chart_labels.append(day.strftime('%d %b'))
            p_sum = ProductionEntry.objects.filter(production_date=day).aggregate(s=Sum('quantity'))['s'] or 0
            d_sum = DispatchItem.objects.filter(dispatch__dispatch_date=day).aggregate(s=Sum('quantity'))['s'] or 0
            production_data.append(int(p_sum))
            dispatch_data.append(int(d_sum))

        # Product-wise Inventory
        products_stock = FactoryInventory.objects.select_related('product').filter(product__is_active=True).order_by('-current_stock')[:6]
        stock_product_names = [p.product.name for p in products_stock]
        stock_product_values = [p.current_stock for p in products_stock]

        context = {
            'role': 'superadmin',
            'filter_mode': filter_mode,
            'filter_from': filter_from,
            'filter_to': filter_to,
            'total_products': total_products,
            'active_products': active_products,
            'total_factory_stock': total_factory_stock,
            'total_opening_stock': total_opening_stock,
            'all_time_production': all_time_production,
            'all_time_dispatch': all_time_dispatch,
            'period_production': period_production,
            'today_production': today_production,
            'period_dispatch_count': period_dispatch_count,
            'period_dispatch_qty': period_dispatch_qty,
            'period_dispatch_amount': period_dispatch_amount,
            'today_dispatch_count': today_dispatch_count,
            'today_dispatch_qty': today_dispatch_qty,
            'today_dispatch_amount': today_dispatch_amount,
            'total_clients': total_clients,
            'active_clients': active_clients,
            'active_projects': active_projects,
            'total_projects': total_projects,
            'total_client_material_stock': total_client_material_stock,
            'period_usage': period_usage,
            'today_usage': today_usage,
            'today_workers': today_workers,
            'total_registered_workers': total_registered_workers,
            'total_outstanding': total_outstanding,
            'period_payments': period_payments,
            'today_payments': today_payments,
            'period_expenses': period_expenses,
            'total_expenses': total_expenses,
            'recent_productions': recent_productions,
            'recent_dispatches': recent_dispatches,
            'recent_payments': recent_payments,
            'recent_construction_entries': recent_construction_entries,
            'chart_labels_json': json.dumps(chart_labels),
            'production_data_json': json.dumps(production_data),
            'dispatch_data_json': json.dumps(dispatch_data),
            'stock_product_names_json': json.dumps(stock_product_names),
            'stock_product_values_json': json.dumps(stock_product_values),
        }
        return render(request, 'accounts/dashboard_superadmin.html', context)
