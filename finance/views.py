import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
from .models import Payment, PaymentAllocation, ClientAccount, Expense, ExpenseCategory
from .forms import PaymentForm, ExpenseForm, ExpenseCategoryForm
from clients.models import Client
from dispatch.models import Dispatch
from accounts.decorators import accountant_or_admin_required, superadmin_required


def generate_payment_number():
    date_str = timezone.now().strftime('%Y%m%d')
    count = Payment.objects.filter(payment_number__startswith=f"PAY-{date_str}").count() + 1
    return f"PAY-{date_str}-{count:04d}"


@login_required
def payment_list(request):
    search_query = request.GET.get('q', '').strip()
    client_id = request.GET.get('client', '').strip()
    method_filter = request.GET.get('method', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    payments = Payment.objects.select_related('client', 'recorded_by').prefetch_related('allocations').all()

    if search_query:
        payments = payments.filter(
            Q(payment_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    if client_id:
        payments = payments.filter(client_id=client_id)

    if method_filter:
        payments = payments.filter(payment_method=method_filter)

    if date_from:
        payments = payments.filter(payment_date__gte=date_from)

    if date_to:
        payments = payments.filter(payment_date__lte=date_to)

    total_payments = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    clients = Client.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'finance/payment_list.html', {
        'page_obj': page_obj,
        'clients': clients,
        'methods': Payment.METHOD_CHOICES,
        'total_payments': total_payments,
        'search_query': search_query,
        'selected_client': client_id,
        'selected_method': method_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@accountant_or_admin_required
def payment_create(request):
    specific_dispatch_id = request.GET.get('dispatch')
    specific_dispatch = None
    initial_data = {}

    if specific_dispatch_id:
        specific_dispatch = get_object_or_404(Dispatch, id=specific_dispatch_id)
        initial_data['client'] = specific_dispatch.client
        initial_data['amount'] = specific_dispatch.outstanding_amount

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data.get('submission_token')
            if token and Payment.objects.filter(submission_token=token).exists():
                messages.warning(request, "This payment was already recorded. Duplicate submission prevented.")
                return redirect('finance:payment_list')

            with transaction.atomic():
                payment = form.save(commit=False)
                payment.payment_number = generate_payment_number()
                payment.recorded_by = request.user
                payment.save()

                # Recalculate client's account
                client = payment.client
                if hasattr(client, 'account'):
                    client.account.recalculate()

                # Allocate against dispatches
                remaining_payment = payment.amount
                
                # If specific dispatch was targeted, prioritize it
                target_dispatches = []
                if specific_dispatch and specific_dispatch.client == client:
                    target_dispatches.append(specific_dispatch)

                # Then remaining unpaid dispatches
                other_unpaid = client.dispatches.exclude(payment_status='Paid').order_by('dispatch_date', 'id')
                for d in other_unpaid:
                    if d not in target_dispatches:
                        target_dispatches.append(d)

                for disp in target_dispatches:
                    if remaining_payment <= Decimal('0.00'):
                        break
                    
                    due = disp.outstanding_amount
                    if due > Decimal('0.00'):
                        alloc_amount = min(due, remaining_payment)
                        PaymentAllocation.objects.create(
                            payment=payment,
                            dispatch=disp,
                            amount_allocated=alloc_amount
                        )
                        disp.paid_amount += alloc_amount
                        disp.update_payment_status()
                        remaining_payment -= alloc_amount

                messages.success(
                    request,
                    f"Payment {payment.payment_number} for ₹{payment.amount} recorded for {client.name}."
                )
                return redirect('finance:payment_receipt', payment_id=payment.id)
    else:
        form = PaymentForm(initial=initial_data)

    return render(request, 'finance/payment_form.html', {
        'form': form,
        'specific_dispatch': specific_dispatch,
    })


@login_required
def payment_detail(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related('client', 'recorded_by').prefetch_related('allocations', 'allocations__dispatch'), id=payment_id)
    return render(request, 'finance/payment_detail.html', {'payment': payment})


@login_required
def payment_receipt(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related('client', 'client__account', 'recorded_by').prefetch_related('allocations', 'allocations__dispatch'), id=payment_id)
    return render(request, 'finance/payment_receipt.html', {'payment': payment})


@login_required
def credit_management(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    clients = Client.objects.select_related('account').filter(is_active=True).order_by('name')

    if search_query:
        clients = clients.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    # Ensure accounts are fresh
    for c in clients:
        if hasattr(c, 'account'):
            c.account.recalculate()

    client_list_data = list(clients)
    if status_filter == 'exceeded':
        client_list_data = [c for c in client_list_data if c.is_credit_exceeded]
    elif status_filter == 'available':
        client_list_data = [c for c in client_list_data if not c.is_credit_exceeded]

    total_credit_limit = sum(c.credit_limit for c in client_list_data)
    total_outstanding = sum(c.outstanding_balance for c in client_list_data)
    total_exceeded = sum(1 for c in client_list_data if c.is_credit_exceeded)

    paginator = Paginator(client_list_data, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'finance/credit_management.html', {
        'page_obj': page_obj,
        'total_credit_limit': total_credit_limit,
        'total_outstanding': total_outstanding,
        'total_exceeded': total_exceeded,
        'search_query': search_query,
        'status_filter': status_filter,
    })


@superadmin_required
def update_credit_limit(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    if request.method == 'POST':
        new_limit = request.POST.get('credit_limit')
        if new_limit:
            try:
                client.credit_limit = Decimal(new_limit)
                client.save(update_fields=['credit_limit'])
                messages.success(request, f"Credit limit for {client.name} updated to ₹{client.credit_limit}.")
            except Exception:
                messages.error(request, "Invalid credit limit value.")
    return redirect('finance:credit_management')


@login_required
def expense_list(request):
    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    expenses = Expense.objects.select_related('category', 'recorded_by').all()

    if search_query:
        expenses = expenses.filter(
            Q(description__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    if category_id:
        expenses = expenses.filter(category_id=category_id)

    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)

    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)

    total_expense_amount = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    categories = ExpenseCategory.objects.all().order_by('name')

    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'finance/expense_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'total_expense_amount': total_expense_amount,
        'search_query': search_query,
        'selected_category': category_id,
        'date_from': date_from,
        'date_to': date_to,
    })


@accountant_or_admin_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, f"Expense of ₹{expense.amount} for '{expense.category.name}' recorded.")
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm()

    return render(request, 'finance/expense_form.html', {'form': form})


@accountant_or_admin_required
def expense_category_list(request):
    categories = ExpenseCategory.objects.all().order_by('name')
    form = ExpenseCategoryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cat = form.save()
        messages.success(request, f"Category '{cat.name}' created.")
        return redirect('finance:expense_category_list')

    return render(request, 'finance/expense_category_list.html', {
        'categories': categories,
        'form': form,
    })
