"""The administrators' site: user data, a read-only data catalogue and a system report.

Careers and skills are not edited here: they come from O*NET and ESCO and are
rebuilt with the pipeline (backend/pipeline), so the catalogue page shows them
read-only and says how to change them.
"""

from django.contrib import admin

from core.models import GoogleAccount, SavedCareer, SkillProfile, SkillProgress


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
