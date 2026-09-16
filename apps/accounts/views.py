"""Account endpoints. Stubs only in Sprint 1."""

from apps.common_stub import NotImplementedView


class RegisterView(NotImplementedView):
    description = "Register a new user account."
    planned_sprint = 5


class LoginView(NotImplementedView):
    description = "Authenticate a user and start a session."
    planned_sprint = 5


class LogoutView(NotImplementedView):
    description = "End the current session."
    planned_sprint = 5
