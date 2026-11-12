from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.roles import ROLES, assign_role

CHOICES = {role.lower(): role for role in ROLES} | {'none': None}


class Command(BaseCommand):
    help = 'Give an existing account a role on the admin site: superadmin, admin or none.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('role', choices=sorted(CHOICES))

    def handle(self, *args, username, role, **options):
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            raise CommandError(f'There is no account called {username}.')
        try:
            assign_role(user, CHOICES[role])
        except ValueError as error:
            raise CommandError(str(error))
        self.stdout.write(self.style.SUCCESS(
            f'{username} is now a {CHOICES[role]}.' if CHOICES[role] else f'{username} no longer has a role.'))
