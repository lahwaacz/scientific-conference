from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import ValidationError


class NoSignupAccountAdapter(DefaultAccountAdapter):
    """Local accounts are provisioned by staff, not by self-service signup."""

    def is_open_for_signup(self, request):
        return False


class ConferenceSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        # Must re-enable it locally: the default delegates to the account
        # adapter, which is closed (NoSignupAccountAdapter above).
        return True

    def validate_disconnect(self, account, accounts):
        raise ValidationError("Cannot disconnect the university account.")

    def save_user(self, request, sociallogin, form=None):
        # Settings-configured apps (SOCIALACCOUNT_PROVIDERS APPS) have no DB
        # row; keeping one on the token would crash the save below with an
        # unsaved-FK error, mirroring allauth's own `if app.pk: token.app`.
        token = sociallogin.token
        if token is not None and token.app is not None and token.app.pk is None:
            token.app = None
        return super().save_user(request, sociallogin, form=form)
