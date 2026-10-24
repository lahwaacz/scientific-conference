from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission

from .models import Conference, ConferenceManagers


def can_manage_conference(user, conference):
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    if conference is None:
        return False
    return ConferenceManagers.objects.filter(conference=conference, user=user).exists()


class IsConferenceManager(BasePermission):
    """Conference-level authorization.

    Class views get ``conference`` from ConferenceScopedMixin (resolved in
    initial() before permissions run); DRF function views expose the URL
    kwargs through ``view.kwargs`` and are resolved here.
    """

    message = "You do not have access to this conference."

    def has_permission(self, request, view):
        conference = getattr(view, "conference", None)
        if conference is None:
            kwarg = getattr(view, "conference_url_kwarg", "conference_slug")
            slug = view.kwargs.get(kwarg)
            if not slug:
                return False
            conference = get_object_or_404(Conference, slug=slug)
        return can_manage_conference(request.user, conference)
