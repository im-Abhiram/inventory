from .decorators import get_user_role
from .models import CompanySetting


def user_role_context(request):
    try:
        company_settings = CompanySetting.get_settings()
    except Exception:
        company_settings = None

    if not request.user.is_authenticated:
        return {
            'user_role': None,
            'is_superadmin': False,
            'is_accountant': False,
            'is_owner': False,
            'can_write': False,
            'company_settings': company_settings,
        }
    
    role = get_user_role(request.user)
    return {
        'user_role': role,
        'is_superadmin': (role == 'superadmin'),
        'is_accountant': (role == 'accountant'),
        'is_owner': (role == 'owner'),
        'can_write': (role in ['superadmin', 'accountant']),
        'company_settings': company_settings,
    }

