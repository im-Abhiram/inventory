from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile


class AccountRoleTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Super Admin
        self.superadmin = User.objects.create_superuser(
            username='admin_test',
            email='admin@example.com',
            password='Password123!'
        )
        self.superadmin.profile.role = UserProfile.ROLE_SUPERADMIN
        self.superadmin.profile.save()

        # Accountant
        self.accountant = User.objects.create_user(
            username='accountant_test',
            password='Password123!'
        )
        self.accountant.profile.role = UserProfile.ROLE_ACCOUNTANT
        self.accountant.profile.save()

        # Owner
        self.owner = User.objects.create_user(
            username='owner_test',
            password='Password123!'
        )
        self.owner.profile.role = UserProfile.ROLE_OWNER
        self.owner.profile.save()

    def test_login(self):
        login_success = self.client.login(username='admin_test', password='Password123!')
        self.assertTrue(login_success)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_superadmin_can_access_user_management(self):
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)

    def test_accountant_cannot_access_user_management(self):
        self.client.login(username='accountant_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 403)

    def test_owner_cannot_access_user_management(self):
        self.client.login(username='owner_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 403)

    def test_superadmin_can_create_user(self):
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.post(reverse('accounts:user_create'), {
            'username': 'new_staff',
            'email': 'staff@example.com',
            'first_name': 'New',
            'last_name': 'Staff',
            'role': UserProfile.ROLE_ACCOUNTANT,
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.filter(username='new_staff').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.profile.role, UserProfile.ROLE_ACCOUNTANT)
