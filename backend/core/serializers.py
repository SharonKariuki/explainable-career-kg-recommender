import re

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import serializers

from core.models import GoogleAccount
from recommender.matching import SkillMatcher

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('That username is taken.')
        return value

    def validate(self, data):
        validate_password(data['password'], User(username=data['username'], email=data.get('email', '')))
        return data

    def create(self, data):
        return User.objects.create_user(data['username'], data.get('email', ''), data['password'])


MAX_SKILLS = 30


class SkillProfileSerializer(serializers.Serializer):
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=True), max_length=MAX_SKILLS,
    )
    updated_at = serializers.DateTimeField(read_only=True)

    def validate_skills(self, value):
        # Same cleaning the matcher applies: trimmed, no blanks, no repeats ignoring case.
        return SkillMatcher.clean(value)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if user is None:
            raise serializers.ValidationError('Incorrect username or password.')
        data['user'] = user
        return data


def unique_username(email):
    """A free username built from the email's local part: amina, amina2, amina3..."""
    base = re.sub(r'[^\w.@+-]', '', email.split('@')[0])[:140] or 'user'
    username, n = base, 1
    while User.objects.filter(username__iexact=username).exists():
        n += 1
        username = f'{base}{n}'
    return username


class GoogleLoginSerializer(serializers.Serializer):
    """Signs in with a Google ID token, creating the account on first use.

    Accounts are linked by Google's stable subject id, never by email: emails on
    password accounts are unverified, so matching on them would let anyone who
    typed someone else's address take over that person's Google sign-in.
    """

    credential = serializers.CharField(write_only=True)

    def validate(self, data):
        if not settings.GOOGLE_CLIENT_ID:
            raise serializers.ValidationError('Google sign-in is not set up.')
        try:
            claims = id_token.verify_oauth2_token(
                data['credential'], google_requests.Request(), settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            raise serializers.ValidationError('Google could not confirm that sign-in. Please try again.')
        if not claims.get('email_verified'):
            raise serializers.ValidationError('Your Google email address is not verified.')

        data['user'] = self.user_for(claims)
        if not data['user'].is_active:
            raise serializers.ValidationError('This account is disabled.')
        return data

    @staticmethod
    @transaction.atomic
    def user_for(claims):
        link = GoogleAccount.objects.select_related('user').filter(subject=claims['sub']).first()
        if link:
            return link.user
        user = User.objects.create_user(unique_username(claims['email']), claims['email'])  # no usable password
        GoogleAccount.objects.create(user=user, subject=claims['sub'])
        return user
