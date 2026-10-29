from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core import services
from core.models import SavedCareer, SkillProfile, SkillProgress
from core.serializers import (
    AccountSerializer, DeleteAccountSerializer, GoogleLoginSerializer, LoginSerializer, PasswordChangeSerializer,
    RegisterSerializer, SkillProfileSerializer, SkillProgressSerializer,
)

DEFAULT_TOP = 10


def token_response(user, status_code=status.HTTP_200_OK):
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username}, status=status_code)


@api_view(['POST'])
@authentication_classes([])  # a stale token must not block signing in
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return token_response(serializer.save(), status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([])  # a stale token must not block signing in
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return token_response(serializer.validated_data['user'])


@api_view(['POST'])
@authentication_classes([])  # a stale token must not block signing in
@permission_classes([AllowAny])
def google_login(request):
    serializer = GoogleLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return token_response(serializer.validated_data['user'])


@api_view(['POST'])
def logout(request):
    request.auth.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def account(user):
    return {
        'username': user.username,
        'email': user.email,
        'has_password': user.has_usable_password(),
        'google': hasattr(user, 'google_account'),
        'date_joined': user.date_joined,
    }


@api_view(['GET', 'PATCH', 'DELETE'])
def me(request):
    user = request.user
    if request.method == 'PATCH':
        serializer = AccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.email = serializer.validated_data['email']
        user.save(update_fields=['email'])
    elif request.method == 'DELETE':
        DeleteAccountSerializer(data=request.data, context={'user': user}).is_valid(raise_exception=True)
        user.delete()  # cascades to the token, profile, saved careers and progress
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(account(user))


@api_view(['POST'])
def change_password(request):
    user = request.user
    serializer = PasswordChangeSerializer(data=request.data, context={'user': user})
    serializer.is_valid(raise_exception=True)
    user.set_password(serializer.validated_data['new_password'])
    user.save(update_fields=['password'])
    # A new token signs out anyone else holding the old one.
    Token.objects.filter(user=user).delete()
    return token_response(user)


# Every profile and recommendation view works on request.user only; no view
# takes a user or profile id, so one user cannot address another's data.

@api_view(['GET', 'PUT'])
def profile(request):
    skill_profile, _ = SkillProfile.objects.get_or_create(user=request.user)
    if request.method == 'PUT':
        serializer = SkillProfileSerializer(skill_profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        skill_profile.skills = serializer.validated_data['skills']
        skill_profile.save()
    return Response(SkillProfileSerializer(skill_profile).data)


def declared_skills(user):
    skill_profile = SkillProfile.objects.filter(user=user).first()
    return skill_profile.skills if skill_profile else []


@api_view(['GET'])
def recommendations(request):
    try:
        top = int(request.query_params.get('top', DEFAULT_TOP))
    except ValueError:
        raise ValidationError({'top': 'Must be a whole number.'})
    if not 1 <= top <= 50:
        raise ValidationError({'top': 'Must be between 1 and 50.'})

    skills = declared_skills(request.user)
    matches, ranked = services.rank(skills, top_k=top)
    return Response({
        'skills': skills,
        'matches': [services.match_summary(m) for m in matches],
        'recommendations': [services.recommendation_summary(r, i) for i, r in enumerate(ranked, 1)],
    })


@api_view(['GET'])
def recommendation_detail(request, career_code):
    matches, ranked = services.rank(declared_skills(request.user))
    for position, r in enumerate(ranked, 1):
        if services.career_code(r.career_id) == career_code:
            return Response(services.recommendation_detail(r, position, matches))
    raise NotFound('That career is not among your recommendations.')


# ---- Career catalogue ----

def match_info(recommendation, position):
    if recommendation is None:
        return None
    return {'rank': position, 'score': recommendation.score}


def ranking(user):
    """(matches, {career code: (position, recommendation)}) for the user's saved skills."""
    matches, ranked = services.rank(declared_skills(user))
    return matches, {services.career_code(r.career_id): (i, r) for i, r in enumerate(ranked, 1)}


def saved_codes(user):
    return set(SavedCareer.objects.filter(user=user).values_list('career_code', flat=True))


def with_match(summary, ranked, saved):
    position, r = ranked.get(summary['career_code'], (None, None))
    return {**summary, 'match': match_info(r, position), 'saved': summary['career_code'] in saved}


@api_view(['GET'])
def careers(request):
    """Every career, each with the user's match (or null) and whether they saved it."""
    _, ranked = ranking(request.user)
    saved = saved_codes(request.user)
    return Response({
        'skills': declared_skills(request.user),
        'careers': [with_match(c, ranked, saved) for c in services.catalogue()],
    })


@api_view(['GET'])
def career_detail(request, career_code):
    career = services.career_node_id(career_code)
    if career is None:
        raise NotFound('There is no such career.')
    matches, ranked = ranking(request.user)
    return Response(with_match(services.career_profile(career, matches), ranked, saved_codes(request.user)))


@api_view(['GET'])
def saved_careers(request):
    _, ranked = ranking(request.user)
    saved = list(SavedCareer.objects.filter(user=request.user))
    codes = {s.career_code for s in saved}
    items = []
    for s in saved:
        career = services.career_node_id(s.career_code)
        if career is not None:  # skip a code the dataset no longer has
            items.append({**with_match(services.career_summary(career), ranked, codes), 'saved_at': s.saved_at})
    return Response({'careers': items})


@api_view(['PUT', 'DELETE'])
def saved_career(request, career_code):
    if services.career_node_id(career_code) is None:
        raise NotFound('There is no such career.')
    if request.method == 'PUT':
        SavedCareer.objects.get_or_create(user=request.user, career_code=career_code)
        return Response({'career_code': career_code, 'saved': True})
    SavedCareer.objects.filter(user=request.user, career_code=career_code).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def skills(request):
    """Skill names for the skills screen to suggest while the user types."""
    return Response({'results': services.search_skills(request.query_params.get('q', ''))})


# ---- Roadmap progress ----

def progress_item(p):
    return {'skill_id': p.skill_id, 'label': services.skill_label(p.skill_id), 'status': p.status, 'updated_at': p.updated_at}


@api_view(['GET', 'PUT'])
def progress(request):
    if request.method == 'PUT':
        serializer = SkillProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill_id, new_status = serializer.validated_data['skill_id'], serializer.validated_data['status']
        if new_status == SkillProgressSerializer.TODO:
            SkillProgress.objects.filter(user=request.user, skill_id=skill_id).delete()
        else:
            SkillProgress.objects.update_or_create(user=request.user, skill_id=skill_id, defaults={'status': new_status})
    items = SkillProgress.objects.filter(user=request.user).order_by('-updated_at')
    return Response({'skills': [progress_item(p) for p in items if services.skill_label(p.skill_id)]})
