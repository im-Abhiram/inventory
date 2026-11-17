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


    def test_login_math_captcha_verification(self):
        # 1. GET login page establishes session captcha
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('captcha_question', response.context)
        correct_answer = self.client.session.get('login_captcha_ans')
        self.assertIsNotNone(correct_answer)

        # 2. POST with wrong captcha fails
        wrong_response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_test',
            'password': 'Password123!',
            'captcha_answer': str(int(correct_answer) + 99)
        })
        self.assertEqual(wrong_response.status_code, 200)
        self.assertFalse(wrong_response.wsgi_request.user.is_authenticated)

        # 3. POST with correct captcha succeeds
        new_answer = self.client.session.get('login_captcha_ans')
        correct_response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_test',
            'password': 'Password123!',
            'captcha_answer': str(new_answer)
        })
        self.assertEqual(correct_response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_session_settings_security_configuration(self):
        from django.conf import settings
        self.assertEqual(settings.SESSION_COOKIE_AGE, 3600)  # 1 hour
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
