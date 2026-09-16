"""
Profile model.

A profile holds what a (usually cold-start) user tells the system about
themselves. Declared skills and interests are stored as the user typed them,
as JSON lists of strings. They are not normalised here: the semantic matcher
(Sprint 2/3) compares the raw text against graph skill nodes, and keeping the
original wording lets an explanation quote the user's own words back to them.

Occupations and skills are not stored in PostgreSQL. They live in the
knowledge graph and are referenced by identifier only.
"""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    class EducationLevel(models.TextChoices):
        SECONDARY = "secondary", "Secondary school"
        CERTIFICATE = "certificate", "Certificate"
        DIPLOMA = "diploma", "Diploma"
        BACHELORS = "bachelors", "Bachelor's degree"
        MASTERS = "masters", "Master's degree"
        DOCTORATE = "doctorate", "Doctorate"
        OTHER = "other", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    declared_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="Skills exactly as the user entered them, e.g. ['python', 'excel'].",
    )
    education_level = models.CharField(max_length=20, choices=EducationLevel.choices, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    institution = models.CharField(max_length=200, blank=True)
    interests = models.JSONField(
        default=list,
        blank=True,
        help_text="Career interests as free-text strings, e.g. ['cybersecurity'].",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profiles_profile"

    def __str__(self):
        return f"Profile of {self.user}"

    @property
    def skill_count(self):
        """Number of declared skills; three or fewer counts as a sparse profile."""
        return len(self.declared_skills or [])
