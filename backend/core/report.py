"""Figures for the administrators' system report and data catalogue.

Everything is computed on request from the database and the loaded engine, so
the report always reflects the current data. Ranking every profile costs about
a tenth of a second each, so only the most recently updated profiles are ranked.
"""

from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from core import services
from core.models import GoogleAccount, SavedCareer, SkillProfile, SkillProgress
from recommender.engine import DEFAULT_PARAMS, get_engine

COLD_START_SKILLS = 3  # the methodology's cold-start profiles have three or fewer skills
RANKED_PROFILES = 200
TOP = 10


def system_report(now=None):
    now = now or timezone.now()
    users = get_user_model().objects.all()
    profiles = list(SkillProfile.objects.order_by('-updated_at'))
    with_skills = [p for p in profiles if p.skills]
    sizes = [len(p.skills) for p in with_skills]

    titles = {services.career_code(c): get_engine().kg.node(c)['label'] for c in get_engine().kg.careers()}
    first_choice = Counter()
    for p in with_skills[:RANKED_PROFILES]:
        _, ranked = services.rank(p.skills, top_k=1)
        if ranked:
            first_choice[ranked[0].title] += 1

    declared = Counter(s.casefold() for p in with_skills for s in p.skills)
    shown = {s.casefold(): s for p in with_skills for s in p.skills}
    matches = get_engine().matcher.match(list(shown.values())) if shown else []
    unmatched = sorted(
        ({'skill': m.query, 'profiles': declared[m.query.casefold()], 'nearest': m.node_label,
          'similarity': m.similarity} for m in matches if m.low_confidence),
        key=lambda u: (-u['profiles'], u['skill'].casefold()),
    )

    return {
        'users': {
            'total': users.count(),
            'last_7_days': users.filter(date_joined__gte=now - timedelta(days=7)).count(),
            'last_30_days': users.filter(date_joined__gte=now - timedelta(days=30)).count(),
            'google': GoogleAccount.objects.count(),
            'staff': users.filter(is_staff=True).count(),
        },
        'profiles': {
            'with_skills': len(with_skills),
            'cold_start': sum(1 for n in sizes if n <= COLD_START_SKILLS),
            'cold_start_limit': COLD_START_SKILLS,
            'mean_skills': round(sum(sizes) / len(sizes), 1) if sizes else 0,
        },
        'ranked_profiles': min(len(with_skills), RANKED_PROFILES),
        'first_choice': first_choice.most_common(TOP),
        'saved': [(titles.get(code, code), n) for code, n in
                  Counter(SavedCareer.objects.values_list('career_code', flat=True)).most_common(TOP)],
        'declared': [(shown[s], n) for s, n in declared.most_common(TOP)],
        'unmatched': unmatched[:TOP],
        'progress': {
            'learning': SkillProgress.objects.filter(status=SkillProgress.LEARNING).count(),
            'done': SkillProgress.objects.filter(status=SkillProgress.DONE).count(),
        },
        'engine': {**vars(DEFAULT_PARAMS), 'careers': len(titles), 'skills': len(get_engine().kg.skills()),
                   'edges': get_engine().kg.graph.number_of_edges()},
    }


def data_catalogue():
    """Every career with its domain and how many skills and tools it requires."""
    return services.catalogue()
