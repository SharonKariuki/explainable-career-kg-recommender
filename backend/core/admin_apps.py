from django.contrib.admin.apps import AdminConfig


class AjiraAdminConfig(AdminConfig):
    """Django's admin, with AjiraGuide's report and catalogue pages (core/admin_site.py)."""

    default_site = 'core.admin_site.AjiraAdminSite'
