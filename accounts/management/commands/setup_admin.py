import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Create, recover, or promote a Super Admin with custom credentials (no predefined passwords).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Custom username for the Super Admin account'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the Super Admin account'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='',
            help='Optional email address for the Super Admin'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all existing user accounts in the database'
        )
        parser.add_argument(
            '--delete-user',
            type=str,
            help='Delete an existing user account by username (e.g., delete unwanted default demo admin)'
        )

    def handle(self, *args, **options):
        # 1. Handle user deletion if requested
        delete_username = options.get('delete_user')
        if delete_username:
            try:
                user_to_delete = User.objects.get(username=delete_username)
                user_to_delete.delete()
                self.stdout.write(self.style.SUCCESS(f"Successfully deleted user account: '{delete_username}'"))
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"User '{delete_username}' does not exist."))
            return

        # 2. Handle listing existing users
        if options.get('list'):
            self._list_users()
            return

        username = options.get('username')
        password = options.get('password')
        email = options.get('email', '')

        # 3. Interactive prompt if username or password not provided
        if not username:
            self.stdout.write(self.style.MIGRATE_HEADING("=== Custom Super Admin Setup / Recovery ==="))
            self.stdout.write("Existing users in database:")
            self._list_users()
            self.stdout.write("")
            username = input("Enter custom username for Super Admin: ").strip()
            if not username:
                raise CommandError("Username cannot be empty.")

        # Check if user already exists
        user_exists = User.objects.filter(username=username).exists()

        if not password:
            if user_exists:
                confirm = input(f"User '{username}' already exists. Reset password & make Super Admin? [Y/n]: ").strip().lower()
                if confirm in ['n', 'no']:
                    self.stdout.write(self.style.NOTICE("Aborted."))
                    return
            while True:
                p1 = getpass.getpass(f"Enter password for '{username}': ")
                if not p1:
                    self.stdout.write(self.style.ERROR("Password cannot be empty. Try again."))
                    continue
                p2 = getpass.getpass("Confirm password: ")
                if p1 != p2:
                    self.stdout.write(self.style.ERROR("Passwords do not match. Try again."))
                    continue
                password = p1
                break

        # 4. Create or update the user
        if user_exists:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            if email:
                user.email = email
            user.save()
            action_desc = "updated and promoted to Super Admin"
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True,
                is_superuser=True,
                is_active=True
            )
            action_desc = "created as Super Admin"

        # Ensure UserProfile exists and has ROLE_SUPERADMIN
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.ROLE_SUPERADMIN
        profile.save()

        self.stdout.write(self.style.SUCCESS(f"\n[OK] User '{username}' was successfully {action_desc}!"))
        self.stdout.write(self.style.SUCCESS("You can now log in at /accounts/login/ with your custom credentials.\n"))

    def _list_users(self):
        users = User.objects.all().order_by('username')
        if not users.exists():
            self.stdout.write("  (No user accounts found in database)")
            return

        self.stdout.write(f"  {'Username':<20} {'Role':<15} {'Superuser':<10} {'Active':<8} {'Email'}")
        self.stdout.write("  " + "-" * 70)
        for u in users:
            role = getattr(u, 'profile', None).role if hasattr(u, 'profile') else 'None'
            self.stdout.write(
                f"  {u.username:<20} {role:<15} {str(u.is_superuser):<10} {str(u.is_active):<8} {u.email}"
            )
