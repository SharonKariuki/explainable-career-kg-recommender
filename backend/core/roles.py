"""Role-based access to the administrators' site.

A role is a Django group with a fixed set of permissions, listed here and
written to the database after every migrate (sync_roles). An account holds at
most one role, and the admin site only ever asks whether the signed-in user has
a permission, never which role they hold.

Superadmin  everything, and the only role that can assign roles, edit staff
            accounts or delete users.
Admin       manages student accounts and their data, and reads the system
            report and the data catalogue.

An account made with createsuperuser passes every permission check, so it
counts as a Superadmin.
"""

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

SUPERADMIN = 'Superadmin'
ADMIN = 'Admin'

ASSIGN_ROLES = 'core.assign_roles'
VIEW_REPORT = 'core.view_system_report'
VIEW_CATALOGUE = 'core.view_data_catalogue'

# A Superadmin holds every permission in these apps.
SUPERADMIN_APPS = ('auth', 'authtoken', 'core')

ADMIN_PERMISSIONS = (
    'auth.view_user', 'auth.add_user', 'auth.change_user',
    'core.view_skillprofile', 'core.add_skillprofile', 'core.change_skillprofile', 'core.delete_skillprofile',
    'core.view_savedcareer', 'core.add_savedcareer', 'core.change_savedcareer', 'core.delete_savedcareer',
    'core.view_skillprogress', 'core.add_skillprogress', 'core.change_skillprogress', 'core.delete_skillprogress',
    'core.view_googleaccount',
    VIEW_REPORT, VIEW_CATALOGUE,
)

ROLES = (SUPERADMIN, ADMIN)  # most powerful first


def named_permissions(names):
    wanted = Q()
    for name in names:
        app_label, codename = name.split('.')
        wanted |= Q(content_type__app_label=app_label, codename=codename)
    found = list(Permission.objects.filter(wanted))
    if len(found) != len(names):
        raise LookupError(f'{len(names) - len(found)} of the role permissions do not exist')
    return found


def sync_roles(**kwargs):
    """Create the role groups and set their permissions; runs after every migrate."""
    for label in SUPERADMIN_APPS:  # their permissions may not be written yet when this runs
        create_permissions(apps.get_app_config(label), verbosity=0)
    Group.objects.get_or_create(name=SUPERADMIN)[0].permissions.set(
        Permission.objects.filter(content_type__app_label__in=SUPERADMIN_APPS))
    Group.objects.get_or_create(name=ADMIN)[0].permissions.set(named_permissions(ADMIN_PERMISSIONS))


def role_of(user):
    """The user's role, or None for an ordinary account."""
    if user.is_superuser:
        return SUPERADMIN
    held = set(user.groups.values_list('name', flat=True))
    return next((role for role in ROLES if role in held), None)


def is_last_superadmin(user):
    """Whether taking the Superadmin role from this user would leave nobody to assign roles."""
    others = get_user_model().objects.filter(is_active=True).exclude(pk=user.pk)
    return role_of(user) == SUPERADMIN and not others.filter(Q(is_superuser=True) | Q(groups__name=SUPERADMIN)).exists()


def assign_role(user, role):
    """Give the user exactly this role, or none. The role alone then decides what they may do."""
    if role and role not in ROLES:
        raise ValueError(f'unknown role: {role}')
    if role != SUPERADMIN and is_last_superadmin(user):
        raise ValueError('the only Superadmin cannot lose the role; make another Superadmin first')
    user.is_staff = bool(role)  # staff may sign in to the admin site
    user.is_superuser = False   # the role's permissions replace the all-access flag
    user.save(update_fields=['is_staff', 'is_superuser'])
    user.groups.set(Group.objects.filter(name=role) if role else [])
