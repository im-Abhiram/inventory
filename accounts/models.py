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


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = UserProfile.ROLE_SUPERADMIN if instance.is_superuser else UserProfile.ROLE_OWNER
        UserProfile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            role = UserProfile.ROLE_SUPERADMIN if instance.is_superuser else UserProfile.ROLE_OWNER
            UserProfile.objects.create(user=instance, role=role)
