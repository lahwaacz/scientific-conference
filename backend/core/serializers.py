import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import (
    Abstract,
    AccommodationOption,
    Conference,
    ConferenceDay,
    HikingRoute,
    HikingStop,
    Participant,
    ParticipantSubmission,
    Person,
    Role,
    Session,
    Talk,
)

User = get_user_model()

CONTRIBUTION_TYPES = ("talk", "poster", "attend")


def _allowed_contribution_types(conference):
    if conference is None:
        return CONTRIBUTION_TYPES
    return conference.allowed_contribution_types


def _validate_contribution_type(serializer, data, instance=None):
    allowed = _allowed_contribution_types(serializer.context.get("conference"))
    if not allowed:
        raise serializers.ValidationError(
            {"contribution_type": "Registration is not accepting contributions."}
        )

    current = instance.contribution_type if instance is not None else None
    supplied = "contribution_type" in data
    contribution_type = data.get("contribution_type", current)
    if contribution_type is None:
        contribution_type = allowed[0]
        data["contribution_type"] = contribution_type

    if contribution_type not in allowed and contribution_type != current:
        raise serializers.ValidationError(
            {
                "contribution_type": (
                    "This contribution type is not available for this conference."
                )
            }
        )

    if (instance is None or (supplied and contribution_type != current)) and (
        contribution_type in ("talk", "poster")
    ):
        title = data.get("abstract_title")
        if title is None and instance is not None:
            title = instance.abstract_title
        if not (title or "").strip():
            raise serializers.ValidationError(
                {"abstract_title": "Title is required for a talk or poster."}
            )

    return data


class ParticipantSerializer(serializers.ModelSerializer):
    abstract_id = serializers.IntegerField(source="abstract.id", read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Participant
        fields = [
            "id",
            "name",
            "affiliation",
            "email",
            "abstract_id",
            "photo",
            "contribution_type",
        ]


class AbstractSerializer(serializers.ModelSerializer):
    authors_string = serializers.CharField(source="authors")
    talk_id = serializers.IntegerField(source="talk.id", read_only=True)

    class Meta:
        model = Abstract
        fields = [
            "id",
            "title",
            "text",
            "authors_string",
            "department",
            "talk_id",
        ]


class TalkSerializer(serializers.ModelSerializer):
    participant = ParticipantSerializer(read_only=True)
    abstract = AbstractSerializer(read_only=True)
    abstract_id = serializers.IntegerField(source="abstract.id", read_only=True)

    session = serializers.PrimaryKeyRelatedField(
        queryset=Session.objects.all(), required=False, allow_null=True
    )
    day = serializers.PrimaryKeyRelatedField(
        queryset=ConferenceDay.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Talk
        fields = [
            "id",
            "title",
            "talk_type",
            "start_time",
            "end_time",
            "participant",
            "abstract",
            "session",
            "day",
            "abstract_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        conference = self.context.get("conference")
        if conference is not None:
            self.fields["session"].queryset = Session.objects.filter(
                conference=conference
            )
            self.fields["day"].queryset = ConferenceDay.objects.filter(
                conference=conference
            )


class SessionSerializer(serializers.ModelSerializer):
    talks = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = ["id", "day", "chair", "start_time", "end_time", "talks"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        conference = self.context.get("conference")
        if conference is not None:
            self.fields["day"].queryset = ConferenceDay.objects.filter(
                conference=conference
            )

    def get_talks(self, session):
        qs = session.talks.all().order_by("start_time")
        return TalkSerializer(qs, many=True).data


class ConferenceDaySerializer(serializers.ModelSerializer):
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = ConferenceDay
        fields = ["id", "date", "timeline"]

    def get_timeline(self, day):
        items = []

        for t in Talk.objects.filter(day=day, session__isnull=True).order_by(
            "start_time"
        ):
            items.append(
                {
                    "type": t.talk_type,
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "data": TalkSerializer(t).data,
                }
            )

        for session in day.sessions.all():
            talks = session.talks.all().order_by("start_time")
            if talks.exists():
                start = talks.first().start_time
                end = talks.last().end_time
            else:
                start = session.start_time
                end = session.end_time

            if start:
                items.append(
                    {
                        "type": "session",
                        "start_time": start,
                        "end_time": end,
                        "data": SessionSerializer(session).data,
                    }
                )

        items.sort(
            key=lambda x: (
                x["start_time"] is None,
                x["start_time"] or datetime.time.min,
            )
        )
        return items


class PersonSerializer(serializers.ModelSerializer):
    # Public read shape: backs the AllowAny list view, so it deliberately
    # omits the auth-user fields (staff usernames must not leak publicly).
    roles = serializers.SlugRelatedField(
        slug_field="name", many=True, queryset=Role.objects.all(), required=False
    )

    class Meta:
        model = Person
        fields = ["id", "name", "affiliation", "email", "photo", "roles"]


class PersonAdminSerializer(PersonSerializer):
    # Staff shape for admin-gated writes and detail reads: adds the
    # reference-only auth-user link (writable pk, read-only username).
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    user_username = serializers.CharField(
        source="user.username", read_only=True, allow_null=True
    )

    class Meta(PersonSerializer.Meta):
        fields = [*PersonSerializer.Meta.fields, "user", "user_username"]


class AccommodationOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationOption
        fields = ["id", "name", "description", "url", "photo", "order"]


# Serializes the Conference row; the class name keeps the /accommodation/ contract.
class AccommodationInfoSerializer(serializers.ModelSerializer):
    description = serializers.CharField(
        source="accommodation_description", required=False, allow_blank=True
    )
    options = AccommodationOptionSerializer(
        many=True, read_only=True, source="accommodation_options"
    )

    class Meta:
        model = Conference
        fields = ["id", "description", "options"]


class AccommodationOptionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationOption
        fields = ["id", "name", "description", "url", "photo", "order"]


class ParticipantSubmissionSerializer(serializers.ModelSerializer):
    stay_duration = serializers.ReadOnlyField()
    linked_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = ParticipantSubmission
        fields = [
            "id",
            "name",
            "email",
            "affiliation",
            "photo",
            "contribution_type",
            "abstract_title",
            "abstract_text",
            "additional_authors",
            "additional_affiliations",
            "arrival_date",
            "departure_date",
            "stay_duration",
            "status",
            "submitted_at",
            "reviewed_at",
            "admin_notes",
            "published_participant",
            "published_abstract",
            "info",
            "is_student",
            "tracking_token",
            "participant_reference",
            "linked_user",
        ]
        read_only_fields = [
            "submitted_at",
            "reviewed_at",
            "published_participant",
            "published_abstract",
            "stay_duration",
            "tracking_token",
            "participant_reference",
        ]

    def validate(self, data):
        arrival = data.get("arrival_date") or (
            self.instance.arrival_date if self.instance else None
        )
        departure = data.get("departure_date") or (
            self.instance.departure_date if self.instance else None
        )

        if departure and arrival and departure <= arrival:
            raise serializers.ValidationError(
                {"departure_date": "Departure date must be after arrival date"}
            )

        new_type = data.get("contribution_type")
        if (
            self.instance is not None
            and self.instance.status == "approved"
            and new_type
            and new_type != self.instance.contribution_type
            and new_type != "talk"
            and self.instance.published_abstract is not None
        ):
            talk = getattr(self.instance.published_abstract, "talk", None)
            if talk is not None and talk.is_scheduled:
                raise serializers.ValidationError(
                    {
                        "contribution_type": (
                            "Unschedule the talk before changing this submission "
                            "to poster or just attend."
                        )
                    }
                )
        return _validate_contribution_type(self, data, self.instance)

    @transaction.atomic
    def update(self, instance, validated_data):
        old_photo = None
        if "photo" in validated_data:
            photo = validated_data.pop("photo")

            if photo is None and instance.photo:
                old_photo = instance.photo
                instance.photo = None
            elif photo:
                if instance.photo:
                    old_photo = instance.photo
                instance.photo = photo

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if instance.status == "approved" and instance.published_participant:
            try:
                instance.sync_published_data()
            except DjangoValidationError as exc:
                detail = getattr(exc, "message_dict", None) or {
                    "contribution_type": exc.messages
                }
                raise serializers.ValidationError(detail) from exc

        if old_photo:
            old_photo.delete(save=False)

        return instance


class ParticipantSubmissionCreateSerializer(ParticipantSubmissionSerializer):
    """Anonymous create view: `status`, `admin_notes` and `linked_user` are
    read-only so an unauthenticated poster cannot pre-approve a submission,
    inject internal notes or claim someone else's account."""

    # The child MUST redeclare the field: read_only_fields only feed
    # extra_kwargs, and extra_kwargs are applied solely to auto-built fields
    # (DRF's get_fields takes the declared-fields branch and skips them), so
    # the parent's writable declaration would survive into the public create.
    linked_user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(ParticipantSubmissionSerializer.Meta):
        fields = [*ParticipantSubmissionSerializer.Meta.fields]
        read_only_fields = [
            *ParticipantSubmissionSerializer.Meta.read_only_fields,
            "status",
            "admin_notes",
        ]


class ParticipantTrackingSerializer(serializers.ModelSerializer):
    """Participant-facing read serializer for the tracking endpoint.

    Exposes only what a participant may inspect about their own submission:
    no admin notes, no tracking token, no linked user, no published rows."""

    class Meta:
        model = ParticipantSubmission
        fields = [
            "participant_reference",
            "name",
            "email",
            "affiliation",
            "photo",
            "contribution_type",
            "abstract_title",
            "abstract_text",
            "additional_authors",
            "additional_affiliations",
            "arrival_date",
            "departure_date",
            "stay_duration",
            "status",
            "submitted_at",
            "reviewed_at",
            "info",
            "is_student",
        ]
        read_only_fields = fields


class ParticipantTrackingUpdateSerializer(serializers.ModelSerializer):
    """Participant-facing write serializer for the tracking endpoint.

    Editing an approved submission reverts it to pending (and clears
    reviewed_at) so the admin re-reviews before republication; the published
    Participant/Abstract rows are deliberately left untouched."""

    class Meta:
        model = ParticipantSubmission
        fields = [
            "participant_reference",
            "name",
            "email",
            "affiliation",
            "photo",
            "contribution_type",
            "abstract_title",
            "abstract_text",
            "additional_authors",
            "additional_affiliations",
            "arrival_date",
            "departure_date",
            "status",
            "submitted_at",
            "reviewed_at",
            "info",
            "is_student",
        ]
        read_only_fields = [
            "participant_reference",
            "status",
            "submitted_at",
            "reviewed_at",
        ]

    def validate(self, data):
        arrival = data.get("arrival_date") or (
            self.instance.arrival_date if self.instance else None
        )
        departure = data.get("departure_date") or (
            self.instance.departure_date if self.instance else None
        )

        if departure and arrival and departure <= arrival:
            raise serializers.ValidationError(
                {"departure_date": "Departure date must be after arrival date"}
            )
        return _validate_contribution_type(self, data, self.instance)

    def update(self, instance, validated_data):
        was_approved = instance.status == "approved"

        if "photo" in validated_data:
            photo = validated_data.pop("photo")

            # Same photo semantics as the admin serializer: absent key keeps
            # the file, explicit null deletes it, a new file replaces it.
            if photo is None and instance.photo:
                instance.photo.delete(save=False)
                instance.photo = None
            elif photo:
                if instance.photo:
                    instance.photo.delete(save=False)
                instance.photo = photo

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if was_approved:
            instance.status = "pending"
            instance.reviewed_at = None
            instance.save()

        return instance


class HikingStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = HikingStop
        fields = ["id", "route", "name", "description", "photo", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        conference = self.context.get("conference")
        if conference is not None:
            self.fields["route"].queryset = HikingRoute.objects.filter(
                conference=conference
            )


class HikingRouteSerializer(serializers.ModelSerializer):
    stops = HikingStopSerializer(many=True, read_only=True)

    class Meta:
        model = HikingRoute
        fields = ["id", "name", "way_description", "map_url", "stops"]


class ConferenceCardSerializer(serializers.ModelSerializer):
    year = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()

    class Meta:
        model = Conference
        fields = [
            "slug",
            "title",
            "date_start",
            "date_end",
            "year",
            "location",
            "card_photo",
            "short_description",
            "status",
        ]


class BlankAsNoneDateField(serializers.DateField):
    """Multipart form posts send an empty string for empty date inputs."""

    def to_internal_value(self, value):
        if value in ("", None):
            return None
        return super().to_internal_value(value)


# Serializes Conference; the name keeps the /conference-info/ contract.
class ConferenceInfoWriteSerializer(serializers.ModelSerializer):
    registration_opening = BlankAsNoneDateField(required=False, allow_null=True)
    registration_deadline = BlankAsNoneDateField(required=False, allow_null=True)
    submission_edit_deadline = BlankAsNoneDateField(required=False, allow_null=True)
    date_start = BlankAsNoneDateField(required=False, allow_null=True)
    date_end = BlankAsNoneDateField(required=False, allow_null=True)

    class Meta:
        model = Conference
        fields = [
            "title",
            "date_start",
            "date_end",
            "location",
            "card_photo",
            "hero_photo",
            "short_description",
            "badge_title",
            "description",
            "registration_instructions",
            "registration_opening",
            "registration_deadline",
            "submission_edit_deadline",
            "registration_allow_talk",
            "registration_allow_poster",
            "registration_allow_attend",
            "registration_fee_note",
            "grant_text",
            "venue_text",
            "footer_venue_text",
            "venue_photo",
            "conference_office_text",
            "website_url",
            "poster_url",
            "info_desk_email",
            "venue_map_embed_url",
            "copyright_text",
            "program_text",
        ]

    def validate(self, attrs):
        def current(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, None)

        deadline = current("submission_edit_deadline")
        if deadline is not None:
            registration_deadline = current("registration_deadline")
            date_end = current("date_end")
            if registration_deadline is not None and deadline < registration_deadline:
                raise serializers.ValidationError(
                    {
                        "submission_edit_deadline": "Submission editing deadline must be on or after the registration deadline."
                    }
                )
            if date_end is not None and deadline > date_end:
                raise serializers.ValidationError(
                    {
                        "submission_edit_deadline": "Submission editing deadline must be on or before the conference end date."
                    }
                )
        if not any(
            (
                current("registration_allow_talk"),
                current("registration_allow_poster"),
                current("registration_allow_attend"),
            )
        ):
            raise serializers.ValidationError(
                {
                    "registration_allow_talk": "At least one contribution type must be allowed."
                }
            )
        return attrs


class ConferenceInfoSerializer(serializers.ModelSerializer):
    # year is a derived @property on the model (F6), never writable.
    year = serializers.ReadOnlyField()

    class Meta:
        model = Conference
        fields = ["id", *ConferenceInfoWriteSerializer.Meta.fields, "year"]
