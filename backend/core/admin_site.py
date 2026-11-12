"""The administrators' site, with the system report and data catalogue pages.

Installed as Django's default admin site by core.apps.AjiraAdminConfig, so
every ModelAdmin registered in core/admin.py appears on it.
"""

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from core.report import data_catalogue, system_report


class AjiraAdminSite(admin.AdminSite):
    site_header = 'AjiraGuide administration'
    site_title = 'AjiraGuide admin'
    index_title = 'Administration'
    index_template = 'admin/ajira_index.html'

    def get_urls(self):
        return [
            path('report/', self.admin_view(self.report_view), name='report'),
            path('catalogue/', self.admin_view(self.catalogue_view), name='catalogue'),
        ] + super().get_urls()

    def report_view(self, request):
        context = {**self.each_context(request), 'title': 'System report', 'report': system_report()}
        return TemplateResponse(request, 'admin/ajira_report.html', context)

    def catalogue_view(self, request):
        context = {**self.each_context(request), 'title': 'Careers and skills', 'careers': data_catalogue()}
        return TemplateResponse(request, 'admin/ajira_catalogue.html', context)
