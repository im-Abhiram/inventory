import random
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import UserLoginForm, UserCreateForm, UserEditForm, UserPasswordChangeForm
from .decorators import superadmin_required, get_user_role


def generate_math_captcha():
    """Generates simple addition or subtraction calculation for human verification."""
    operator = random.choice(['+', '-'])
    if operator == '+':
        n1 = random.randint(1, 20)
        n2 = random.randint(1, 20)
        ans = n1 + n2
    else:
        n1 = random.randint(5, 30)
        n2 = random.randint(1, n1)
        ans = n1 - n2
    question = f"{n1} {operator} {n2}"
    return question, ans


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Security: Brute-force lockout protection (5 failed attempts within 5 minutes)
    failed_attempts = request.session.get('failed_login_count', 0)
    last_failed_time = request.session.get('last_failed_login_time', 0)
    current_time = time.time()

    if failed_attempts >= 5 and (current_time - last_failed_time) < 300:
        remaining_wait = int(300 - (current_time - last_failed_time))
        messages.error(
            request,
            f"Account temporarily locked due to multiple failed login attempts. Please wait {remaining_wait} seconds."
        )
        return render(request, 'accounts/login.html', {
            'form': UserLoginForm(),
            'locked_out': True,
            'remaining_wait': remaining_wait
        })

    # Generate or retrieve current math CAPTCHA
    if 'login_captcha_ans' not in request.session or request.GET.get('refresh_captcha'):
        q_str, ans = generate_math_captcha()
        request.session['login_captcha_q'] = q_str
        request.session['login_captcha_ans'] = ans

    captcha_question = request.session.get('login_captcha_q', '5 + 3')
    expected_captcha = request.session.get('login_captcha_ans')

    form = UserLoginForm(request.POST or None)
    if request.method == 'POST':
        user_answer = request.POST.get('captcha_answer', '').strip()

        # Step 1: Validate Math CAPTCHA
        captcha_valid = False
        try:
            if expected_captcha is not None and int(user_answer) == int(expected_captcha):
                captcha_valid = True
        except (ValueError, TypeError):
            captcha_valid = False

        if not captcha_valid:
            # Generate new CAPTCHA immediately on error
            new_q, new_ans = generate_math_captcha()
            request.session['login_captcha_q'] = new_q
            request.session['login_captcha_ans'] = new_ans
            captcha_question = new_q

            messages.error(request, "Security verification failed: Incorrect math calculation answer. Please try again.")
            return render(request, 'accounts/login.html', {
                'form': form,
                'captcha_question': captcha_question
            })

        # Step 2: Validate Credentials if CAPTCHA passed
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    # Reset security lockout counters
                    request.session['failed_login_count'] = 0
                    request.session.pop('last_failed_login_time', None)
                    request.session.pop('login_captcha_q', None)
                    request.session.pop('login_captcha_ans', None)

                    login(request, user)
                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                    next_url = request.GET.get('next')
                    return redirect(next_url if next_url else 'dashboard')
                else:
                    messages.error(request, "This account is inactive. Please contact your Super Administrator.")
            else:
                # Increment failed attempts counter
                request.session['failed_login_count'] = failed_attempts + 1
                request.session['last_failed_login_time'] = current_time
                messages.error(request, "Invalid username or password.")

        # Regenerate CAPTCHA after any failed attempt
        new_q, new_ans = generate_math_captcha()
        request.session['login_captcha_q'] = new_q
        request.session['login_captcha_ans'] = new_ans
        captcha_question = new_q

    return render(request, 'accounts/login.html', {
        'form': form,
        'captcha_question': captcha_question
    })


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
