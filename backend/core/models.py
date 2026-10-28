from django.conf import settings
from django.db import models


class SkillProfile(models.Model):
    """The skills a user has declared, in their own words."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_profile')
    skills = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}: {len(self.skills)} skills'


class GoogleAccount(models.Model):
    """Links a Google account, by its stable subject id, to the user it signs in as."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='google_account')
    subject = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f'{self.user.username}: Google'
