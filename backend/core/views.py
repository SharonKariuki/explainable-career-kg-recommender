from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core import services
from core.models import SkillProfile
from core.serializers import GoogleLoginSerializer, LoginSerializer, RegisterSerializer, SkillProfileSerializer

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


@api_view(['GET'])
def me(request):
    return Response({'username': request.user.username, 'email': request.user.email})


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
