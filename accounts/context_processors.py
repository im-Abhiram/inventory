from .decorators import get_user_role


def user_role_context(request):
    if not request.user.is_authenticated:
        return {
            'user_role': None,
            'is_superadmin': False,
            'is_accountant': False,
            'is_owner': False,
            'can_write': False,
        }
    
    role = get_user_role(request.user)
    return {
        'user_role': role,
        'is_superadmin': (role == 'superadmin'),
        'is_accountant': (role == 'accountant'),
        'is_owner': (role == 'owner'),
        'can_write': (role in ['superadmin', 'accountant']),
    }

