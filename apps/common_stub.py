"""
Shared helper for Sprint 1 stub endpoints.

Every API route exists so that the URL structure is fixed early, but none of
them contains business logic yet. They all answer HTTP 501 with the sprint in
which the behaviour is scheduled.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class NotImplementedView(APIView):
    """Base view that answers every method with 501 Not Implemented."""

    planned_sprint = None
    description = ""

    def _not_implemented(self, request, *args, **kwargs):
        return Response(
            {
                "detail": "Not implemented.",
                "endpoint": self.description,
                "planned_sprint": self.planned_sprint,
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    get = post = put = patch = delete = _not_implemented
