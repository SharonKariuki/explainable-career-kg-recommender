"""
Custom user model.

Defined in Sprint 1, before the first migration, because swapping the user
model after tables exist is difficult in Django. It adds no fields yet; it
exists so that account-level attributes can be added later without a
disruptive migration.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Platform user. Login is by username; email is required and unique."""

    email = models.EmailField("email address", unique=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.username
