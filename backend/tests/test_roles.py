"""Role-based access to the admin site: what a Superadmin, an Admin and a student may do."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

from core.roles import ADMIN, ADMIN_PERMISSIONS, ASSIGN_ROLES, SUPERADMIN, assign_role, role_of

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'
User = get_user_model()


def account(username, role=None):
    user = User.objects.create_user(username, password=PASSWORD)
    if role:
        assign_role(user, role)
    return user


def signed_in(client, username, role):
    account(username, role)
    client.login(username=username, password=PASSWORD)
    return client


def account_form(user, **changes):
    return {'username': user.username, 'first_name': '', 'last_name': '', 'email': '', 'is_active': 'on',
            'date_joined_0': '2026-11-12', 'date_joined_1': '10:00:00', **changes}


def test_migrating_creates_the_two_roles_with_their_permissions():
    admin = {f'{p.content_type.app_label}.{p.codename}' for p in Group.objects.get(name=ADMIN).permissions.all()}
    assert admin == set(ADMIN_PERMISSIONS)
    superadmin = Group.objects.get(name=SUPERADMIN).permissions
    assert superadmin.filter(codename='assign_roles').exists() and superadmin.filter(codename='delete_user').exists()
    assert superadmin.count() > len(admin)


def test_a_role_is_held_through_its_group_not_the_superuser_flag():
    user = account('wanjiru', SUPERADMIN)
    assert user.is_staff and not user.is_superuser
    assert role_of(user) == SUPERADMIN and User.objects.get(pk=user.pk).has_perm(ASSIGN_ROLES)
    account('otieno', SUPERADMIN)
    assign_role(user, ADMIN)
    user = User.objects.get(pk=user.pk)
    assert role_of(user) == ADMIN and not user.has_perm(ASSIGN_ROLES) and user.has_perm('core.view_system_report')
    assign_role(user, None)
    user = User.objects.get(pk=user.pk)
    assert role_of(user) is None and not user.is_staff and not user.get_all_permissions()


def test_the_command_makes_a_superadmin_and_rejects_unknown_accounts():
    account('wanjiru')
    call_command('assign_role', 'wanjiru', 'superadmin')
    assert role_of(User.objects.get(username='wanjiru')) == SUPERADMIN
    with pytest.raises(CommandError, match='no account'):
        call_command('assign_role', 'nobody', 'admin')


def test_the_only_superadmin_cannot_lose_the_role(client):
    owner = User.objects.create_superuser('owner', 'owner@example.com', PASSWORD)
    with pytest.raises(CommandError, match='only Superadmin'):
        call_command('assign_role', 'owner', 'admin')
    client.login(username='owner', password=PASSWORD)
    response = client.post(f'/admin/auth/user/{owner.pk}/change/', account_form(owner, role=ADMIN))
    assert response.status_code == 200 and 'only Superadmin' in response.content.decode()
    assert role_of(User.objects.get(pk=owner.pk)) == SUPERADMIN


def test_a_superadmin_assigns_roles_and_deletes_accounts(client):
    client = signed_in(client, 'wanjiru', SUPERADMIN)
    amina = account('amina')
    assert 'name="role"' in client.get(f'/admin/auth/user/{amina.pk}/change/').content.decode()
    assert client.post(f'/admin/auth/user/{amina.pk}/change/', account_form(amina, role=ADMIN)).status_code == 302
    amina = User.objects.get(pk=amina.pk)
    assert role_of(amina) == ADMIN and amina.is_staff
    assert client.post(f'/admin/auth/user/{amina.pk}/delete/', {'post': 'yes'}).status_code == 302
    assert not User.objects.filter(pk=amina.pk).exists()


def test_an_admin_manages_students_and_reads_the_report(client):
    client = signed_in(client, 'baraka', ADMIN)
    amina = account('amina')
    index = client.get('/admin/').content.decode()
    assert 'System report' in index and 'Careers and skills' in index
    for url in ('/admin/report/', '/admin/catalogue/', '/admin/auth/user/', '/admin/core/skillprofile/'):
        assert client.get(url).status_code == 200, url
    response = client.post(f'/admin/auth/user/{amina.pk}/change/', account_form(amina, email='amina@example.com'))
    assert response.status_code == 302 and User.objects.get(pk=amina.pk).email == 'amina@example.com'


def test_an_admin_cannot_assign_roles_touch_staff_or_delete(client):
    client = signed_in(client, 'baraka', ADMIN)
    amina, owner = account('amina'), account('wanjiru', SUPERADMIN)
    assert 'name="role"' not in client.get(f'/admin/auth/user/{amina.pk}/change/').content.decode()
    client.post(f'/admin/auth/user/{amina.pk}/change/', account_form(amina, role=SUPERADMIN, is_staff='on'))
    amina = User.objects.get(pk=amina.pk)
    assert role_of(amina) is None and not amina.is_staff
    for staff in (owner, User.objects.get(username='baraka')):  # not even their own account
        assert client.post(f'/admin/auth/user/{staff.pk}/change/', account_form(staff, email='x@example.com')).status_code == 403
        assert client.post(f'/admin/auth/user/{staff.pk}/password/', {'password1': PASSWORD, 'password2': PASSWORD}).status_code == 403
    assert client.post(f'/admin/auth/user/{amina.pk}/delete/', {'post': 'yes'}).status_code == 403
    assert client.get('/admin/auth/group/').status_code == 404


def test_staff_without_a_role_see_no_report_or_catalogue(client):
    User.objects.create_user('temp', password=PASSWORD, is_staff=True)
    client.login(username='temp', password=PASSWORD)
    assert client.get('/admin/report/').status_code == 403 and client.get('/admin/catalogue/').status_code == 403
    assert 'System report' not in client.get('/admin/').content.decode()
