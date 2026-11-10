from functools import wraps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'superadmin'
    if hasattr(user, 'profile'):
        return user.profile.role
    return 'owner'


def role_required(allowed_roles):
    """
    Decorator for views that checks if the logged in user belongs to allowed roles.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, "Access denied: You do not have permission to perform this action.")
            raise PermissionDenied("You do not have permission to access this resource.")
        return _wrapped_view
    return decorator


def superadmin_required(view_func):
    return role_required(['superadmin'])(view_func)


def accountant_or_admin_required(view_func):
    return role_required(['superadmin', 'accountant'])(view_func)


def not_owner_required(view_func):
    """
    Decorator that blocks Owner role from performing CUD (Create, Update, Delete) actions.
    Owner role is strictly read-only.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        role = get_user_role(request.user)
        if role == 'owner':
            messages.error(request, "Permission denied: Owner accounts have read-only access.")
            raise PermissionDenied("Owner accounts have read-only access.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

