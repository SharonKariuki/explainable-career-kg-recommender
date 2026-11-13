"""The administrators' site: user data, a read-only data catalogue and a system report.

Careers and skills are not edited here: they come from O*NET and ESCO and are
rebuilt with the pipeline (backend/pipeline), so the catalogue page shows them
read-only and says how to change them.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group

from core.models import GoogleAccount, SavedCareer, SkillProfile, SkillProgress
from core.roles import ASSIGN_ROLES, ROLES, SUPERADMIN, assign_role, is_last_superadmin, role_of

User = get_user_model()

# Roles are fixed in core/roles.py, so groups are not edited here, and accounts
# get the role-aware pages below in place of Django's.
admin.site.unregister(Group)
admin.site.unregister(User)


class AccountForm(UserChangeForm):
    role = forms.ChoiceField(
        choices=[('', 'No role (student)'), *((role, role) for role in ROLES)], required=False,
        help_text='Admins manage student accounts and see the report. Superadmins also assign roles, '
                  'edit staff accounts and delete users.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = role_of(self.instance) or ''

    def clean_role(self):
        role = self.cleaned_data['role']
        if role != SUPERADMIN and is_last_superadmin(self.instance):
            raise forms.ValidationError('This is the only Superadmin. Make another one before changing this role.')
        return role


@admin.register(User)
class AccountAdmin(UserAdmin):
    form = AccountForm
    list_display = ('username', 'email', 'first_name', 'role', 'is_active', 'date_joined')
    list_filter = ('is_active', 'groups')

    @admin.display(description='Role')
    def role(self, user):
        return role_of(user) or '-'

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        access = ('is_active', 'role') if request.user.has_perm(ASSIGN_ROLES) else ('is_active',)
        return (
            (None, {'fields': ('username', 'password')}),
            ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
            ('Access', {'fields': access}),
            ('Important dates', {'fields': ('last_login', 'date_joined')}),
        )

    def manages(self, request, obj):
        """Staff accounts are only changed by someone who can assign roles."""
        return obj is None or not (obj.is_staff or obj.is_superuser) or request.user.has_perm(ASSIGN_ROLES)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self.manages(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self.manages(request, obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and request.user.has_perm(ASSIGN_ROLES) and 'role' in form.changed_data:
            assign_role(obj, form.cleaned_data['role'])


@admin.register(SkillProfile)
class SkillProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill_count', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('updated_at',)

    @admin.display(description='Skills')
    def skill_count(self, profile):
        return len(profile.skills)


@admin.register(SavedCareer)
class SavedCareerAdmin(admin.ModelAdmin):
    list_display = ('user', 'career_code', 'saved_at')
    search_fields = ('user__username', 'career_code')
    list_filter = ('saved_at',)


@admin.register(SkillProgress)
class SkillProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill_id', 'status', 'updated_at')
    search_fields = ('user__username', 'skill_id')
    list_filter = ('status',)


@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject')
    search_fields = ('user__username', 'user__email')
