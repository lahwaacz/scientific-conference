from django.contrib import admin

from .models import (
    Abstract,
    AccommodationInfo,
    AccommodationOption,
    Conference,
    ConferenceDay,
    ConferenceInfo,
    HikingRoute,
    HikingStop,
    Organizer,
    OrganizingCommittee,
    Participant,
    ParticipantSubmission,
    Session,
    Talk,
)


class TalkInline(admin.TabularInline):
    model = Talk
    extra = 1
    fields = ("title", "talk_type", "participant", "abstract", "start_time", "end_time")
    ordering = ("start_time",)


class SessionInline(admin.TabularInline):
    model = Session
    extra = 1
    fields = ("chair", "start_time", "end_time")
    ordering = ("start_time",)


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    # Conferences are managed ONLY here; deletion is forbidden (fork line 3)
    # because every other model cascades from this table. Only the slug is
    # editable here: logistics (title, dates, location, photo, badge title)
    # live on ConferenceInfo and are edited via the conference's SPA admin.
    fields = ("slug",)
    list_display = ("slug",)
    search_fields = ("slug",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConferenceDay)
class ConferenceDayAdmin(admin.ModelAdmin):
    list_display = ("conference", "date")
    list_filter = ("conference",)
    ordering = ("date",)
    inlines = [SessionInline, TalkInline]  # everything in one place


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("conference", "day", "chair", "start_time", "end_time")
    list_filter = ("conference", "day", "chair")
    inlines = [TalkInline]


@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    list_display = (
        "conference",
        "title",
        "talk_type",
        "get_participant_name",
        "start_time",
        "end_time",
        "session",
        "day",
    )
    list_filter = ("conference", "talk_type", "session", "day")
    search_fields = ("title", "participant__name", "abstract__title")

    def get_participant_name(self, obj):
        return obj.participant.name if obj.participant else None

    get_participant_name.short_description = "Participant"


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("conference", "name", "affiliation", "email")
    list_filter = ("conference",)
    search_fields = ("name",)


@admin.register(Abstract)
class AbstractAdmin(admin.ModelAdmin):
    list_display = ("conference", "title", "authors")
    list_filter = ("conference",)
    search_fields = ("title", "authors")


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("conference", "name", "department", "email")
    list_filter = ("conference",)
    search_fields = ("name", "department")


@admin.register(OrganizingCommittee)
class OrganizingCommitteeAdmin(admin.ModelAdmin):
    list_display = ("conference", "name", "department", "email")
    list_filter = ("conference",)
    search_fields = ("name", "department")


@admin.register(ParticipantSubmission)
class ParticipantSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        "conference",
        "name",
        "email",
        "abstract_title",
        "status",
        "submitted_at",
    ]
    list_filter = ["conference", "status", "submitted_at"]
    search_fields = ["name", "email", "abstract_title"]
    readonly_fields = ["submitted_at", "reviewed_at"]

    actions = ["publish_selected"]

    def publish_selected(self, request, queryset):
        for submission in queryset:
            if submission.status != "approved":
                submission.publish()
        self.message_user(request, f"{queryset.count()} submissions published")

    publish_selected.short_description = "Publish selected submissions"


@admin.register(AccommodationInfo)
class AccommodationInfoAdmin(admin.ModelAdmin):
    list_display = ("conference",)
    list_filter = ("conference",)


@admin.register(AccommodationOption)
class AccommodationOptionAdmin(admin.ModelAdmin):
    list_display = ("conference", "name", "info", "order")
    list_filter = ("conference",)


class HikingStopInline(admin.TabularInline):
    model = HikingStop
    extra = 1


@admin.register(HikingRoute)
class HikingRouteAdmin(admin.ModelAdmin):
    list_display = ("conference", "name")
    list_filter = ("conference",)
    inlines = [HikingStopInline]


@admin.register(ConferenceInfo)
class ConferenceInfoAdmin(admin.ModelAdmin):
    list_display = ("conference",)
    list_filter = ("conference",)
