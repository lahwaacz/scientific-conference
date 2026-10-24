from dj_rest_auth.jwt_auth import CookieTokenRefreshSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from core.models import ConferenceManagers


class PasswordRevokingCookieTokenRefreshSerializer(CookieTokenRefreshSerializer):
    """Reject a refresh token whose password hash is no longer current."""

    def validate(self, attrs):
        attrs["refresh"] = self.extract_refresh_token()
        self._reject_if_password_changed(attrs["refresh"])
        return super().validate(attrs)

    @staticmethod
    def _reject_if_password_changed(raw_refresh):
        if not jwt_settings.CHECK_REVOKE_TOKEN:
            return
        try:
            refresh = RefreshToken(raw_refresh)
        except TokenError:
            return
        user_id = refresh.get(str(jwt_settings.USER_ID_CLAIM))
        if not user_id:
            return
        user = (
            get_user_model()
            .objects.filter(**{str(jwt_settings.USER_ID_FIELD): user_id})
            .first()
        )
        expected_hash = get_md5_hash_password(user.password) if user else None
        if (
            expected_hash is None
            or refresh.get(str(jwt_settings.REVOKE_TOKEN_CLAIM)) != expected_hash
        ):
            raise AuthenticationFailed(
                "The user's password has been changed.",
                code="password_changed",
            )


class CookieJWTSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        return AuthUserSerializer(obj["user"], context=self.context).data


class CookieJWTSerializerWithExpiration(CookieJWTSerializer):
    access_expiration = serializers.DateTimeField()
    refresh_expiration = serializers.DateTimeField()


class AuthUserSerializer(serializers.ModelSerializer):
    managed_conferences = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
            "managed_conferences",
        ]
        read_only_fields = fields

    def get_managed_conferences(self, obj):
        if obj.is_superuser:
            return []
        return list(
            ConferenceManagers.objects.filter(user=obj)
            .order_by("conference__slug")
            .values_list("conference__slug", flat=True)
        )
