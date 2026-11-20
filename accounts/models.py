from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_SUPERADMIN = 'superadmin'
    ROLE_ACCOUNTANT = 'accountant'
    ROLE_OWNER = 'owner'

    ROLE_CHOICES = [
        (ROLE_SUPERADMIN, 'Super Admin'),
        (ROLE_ACCOUNTANT, 'Accountant'),
        (ROLE_OWNER, 'Owner'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_OWNER)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_superadmin(self):
        return self.role == self.ROLE_SUPERADMIN or self.user.is_superuser

    @property
    def is_accountant(self):
        return self.role == self.ROLE_ACCOUNTANT

    @property
    def is_owner(self):
        return self.role == self.ROLE_OWNER

    @property
    def can_manage_users(self):
        return self.is_superadmin

    @property
    def can_modify_inventory(self):
        return self.is_superadmin

    @property
    def can_record_production(self):
        return self.is_superadmin

    @property
    def can_record_dispatch(self):
        return self.is_superadmin

    @property
    def can_record_payments(self):
        return self.is_superadmin or self.is_accountant

    @property
    def can_record_expenses(self):
        return self.is_superadmin or self.is_accountant

    @property
    def is_read_only(self):
        return self.is_owner


class CompanySetting(models.Model):
    company_name = models.CharField(max_length=200, default='Thamarayyath Bricks & Construction Materials')
    phone = models.CharField(max_length=50, blank=True, default='+91 98765 43210')
    email = models.EmailField(blank=True, default='contact@thamarayyath.com')
    address = models.TextField(blank=True, default='Factory Road, Industrial Area')
    currency_symbol = models.CharField(max_length=10, default='₹')
    tax_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="GST / Tax ID")
    dispatch_terms = models.TextField(
        blank=True,
        default='Goods once delivered and accepted will not be returned. Payment due as per agreed credit terms.'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Application Setting'
        verbose_name_plural = 'Application Settings'

    def __str__(self):
        return self.company_name

    @classmethod
    def get_settings(cls):
        setting, _ = cls.objects.get_or_create(id=1)
        return setting


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = UserProfile.ROLE_SUPERADMIN if instance.is_superuser else UserProfile.ROLE_OWNER
        UserProfile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            if instance.is_superuser and instance.profile.role != UserProfile.ROLE_SUPERADMIN:
                instance.profile.role = UserProfile.ROLE_SUPERADMIN
            instance.profile.save()
        else:
            role = UserProfile.ROLE_SUPERADMIN if instance.is_superuser else UserProfile.ROLE_OWNER
            UserProfile.objects.create(user=instance, role=role)
