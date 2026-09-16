from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "education_level", "field_of_study", "updated_at")
    search_fields = ("user__username", "field_of_study")
