import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a Django superuser from ADMIN_* environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME", "admin").strip()
        email = os.environ.get("ADMIN_EMAIL", "admin@example.com").strip()
        password = os.environ.get("ADMIN_PASSWORD", "").strip()

        if not username:
            raise CommandError("ADMIN_USERNAME must not be empty.")
        if not password:
            raise CommandError("ADMIN_PASSWORD must not be empty.")
        if password.casefold() in {"admin", "admin123", "password", "12345678"}:
            raise CommandError("ADMIN_PASSWORD is unsafe. Set a new strong password in the deployment environment.")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("ADMIN_PASSWORD is unsafe: " + " ".join(exc.messages)) from exc

        changed = created
        if user.email != email:
            user.email = email
            changed = True
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if not user.check_password(password):
            user.set_password(password)
            changed = True

        if changed:
            user.save()

        self.stdout.write(self.style.SUCCESS(f"superuser ready: {username}"))
