"""Authentication backends that enforce AUTH_PASSWORD_LOGIN_ENABLED at call

time. The allauth backend subclasses Django's ModelBackend, so removing
ModelBackend from AUTHENTICATION_BACKENDS alone would leave password
authentication working through /api/auth/allauth/; both entries therefore
check the flag on every authenticate() call (which also keeps
override_settings working in tests).
"""

from allauth.account.auth_backends import AuthenticationBackend
from django.conf import settings
from django.contrib.auth.backends import ModelBackend


class FlagAwareModelBackend(ModelBackend):
    def authenticate(self, request, **credentials):
        if not settings.AUTH_PASSWORD_LOGIN_ENABLED:
            return None
        return super().authenticate(request, **credentials)


class FlagAwareAllauthBackend(AuthenticationBackend):
    def authenticate(self, request, **credentials):
        # allauth only reaches authenticate() for password logins (social
        # logins short-circuit through django_login), so gating here cannot
        # break a GitLab-only deployment.
        if not settings.AUTH_PASSWORD_LOGIN_ENABLED:
            return None
        return super().authenticate(request, **credentials)
