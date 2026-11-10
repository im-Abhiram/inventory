from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import UserLoginForm, UserCreateForm, UserEditForm, UserPasswordChangeForm
from .decorators import superadmin_required, get_user_role


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserLoginForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                    next_url = request.GET.get('next')
                    return redirect(next_url if next_url else 'dashboard')
                else:
                    messages.error(request, "This account is inactive. Please contact the administrator.")
            else:
                messages.error(request, "Invalid username or password.")

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')


@superadmin_required
def user_list(request):
    search_query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()

    users = User.objects.select_related('profile').all().order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if role_filter:
        users = users.filter(profile__role=role_filter)

    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/user_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
    })


@superadmin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm()

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Create New User'
    })


@superadmin_required
def user_edit(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{user_obj.username}' updated successfully.")
            return redirect('accounts:user_list')
    else:
        form = UserEditForm(instance=user_obj)

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': f'Edit User: {user_obj.username}',
        'user_obj': user_obj
    })


@superadmin_required
def user_change_password(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.POST)
        if form.is_valid():
            user_obj.set_password(form.cleaned_data['new_password'])
            user_obj.save()
            messages.success(request, f"Password for '{user_obj.username}' has been updated.")
            return redirect('accounts:user_list')
    else:
        form = UserPasswordChangeForm()

    return render(request, 'accounts/password_change.html', {
        'form': form,
        'user_obj': user_obj
    })


@superadmin_required
def user_toggle_status(request, user_id):
    if request.method == 'POST':
        user_obj = get_object_or_404(User, id=user_id)
        if user_obj == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            user_obj.is_active = not user_obj.is_active
            user_obj.save()
            status_text = "activated" if user_obj.is_active else "deactivated"
            messages.success(request, f"User '{user_obj.username}' was {status_text}.")
    return redirect('accounts:user_list')
