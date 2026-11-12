from django.conf import settings
from django.db import models


class SkillProfile(models.Model):
    """The skills a user has declared, in their own words, and an optional background.

    Interests, field of study and work experience feed the ranking through
    their similarity to career descriptions (see recommender/engine.py); the
    education level is shown back to the user but does not change the ranking.
    """

    EDUCATION_LEVELS = [
        ('secondary', 'Secondary school'),
        ('certificate', 'Certificate or diploma'),
        ('undergraduate', 'Undergraduate degree (in progress)'),
        ('bachelor', "Bachelor's degree"),
        ('postgraduate', 'Postgraduate degree'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_profile')
    skills = models.JSONField(default=list)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVELS, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    interests = models.TextField(max_length=1000, blank=True)
    experience = models.TextField(max_length=2000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def background_text(self):
        """The free text the ranking compares with career descriptions, or '' when there is none."""
        parts = [self.interests, f'Studied {self.field_of_study}.' if self.field_of_study else '', self.experience]
        return ' '.join(p.strip() for p in parts if p and p.strip())

    def __str__(self):
        return f'{self.user.username}: {len(self.skills)} skills'


class GoogleAccount(models.Model):
    """Links a Google account, by its stable subject id, to the user it signs in as."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='google_account')
    subject = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f'{self.user.username}: Google'


class SavedCareer(models.Model):
    """A career the user bookmarked, by its O*NET-SOC code."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_careers')
    career_code = models.CharField(max_length=20)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'career_code'], name='unique_saved_career')]
        ordering = ['-saved_at']

    def __str__(self):
        return f'{self.user.username}: {self.career_code}'


class SkillProgress(models.Model):
    """Where the user is with a skill from a roadmap. Skills not listed are still to do."""

    LEARNING = 'learning'
    DONE = 'done'
    STATUSES = [(LEARNING, 'Learning'), (DONE, 'Done')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_progress')
    skill_id = models.CharField(max_length=255)  # a knowledge-graph skill node
    status = models.CharField(max_length=10, choices=STATUSES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'skill_id'], name='unique_skill_progress')]

    def __str__(self):
        return f'{self.user.username}: {self.skill_id} {self.status}'


# ---- Recommendation history (the Recommendation, Explanation and Skill Gap entities of the ERD) ----

class RecommendationRun(models.Model):
    """A snapshot of the user's top recommendations, taken each time they save their profile."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendation_runs')
    created_at = models.DateTimeField(auto_now_add=True)
    skills = models.JSONField(default=list)
    background = models.TextField(blank=True)  # the text the ranking compared, '' when none
    params = models.JSONField(default=dict)    # the engine settings that produced the ranking

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user.username}: {self.created_at:%Y-%m-%d %H:%M}'


class Recommendation(models.Model):
    run = models.ForeignKey(RecommendationRun, on_delete=models.CASCADE, related_name='recommendations')
    rank = models.PositiveSmallIntegerField()
    career_code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    domain = models.CharField(max_length=50)
    score = models.FloatField()
    fit = models.CharField(max_length=10)
    components = models.JSONField(default=dict)

    class Meta:
        ordering = ['run', 'rank']
        constraints = [models.UniqueConstraint(fields=['run', 'rank'], name='unique_run_rank')]

    def __str__(self):
        return f'{self.rank}. {self.title}'


class RecommendationExplanation(models.Model):
    recommendation = models.OneToOneField(Recommendation, on_delete=models.CASCADE, related_name='explanation')
    sentences = models.JSONField(default=list)

    def __str__(self):
        return self.sentences[0] if self.sentences else ''


class SkillGap(models.Model):
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='skill_gaps')
    position = models.PositiveSmallIntegerField()
    skill_id = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    requirement = models.CharField(max_length=30)

    class Meta:
        ordering = ['recommendation', 'position']

    def __str__(self):
        return self.label
