import datetime

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Abstract,
    AccommodationInfo,
    AccommodationOption,
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

User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    abstract_id = serializers.IntegerField(source="abstract.id", read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Participant
        fields = ["id", "name", "affiliation", "email", "abstract_id", "photo"]


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


class OrganizerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizer
        fields = ["id", "name", "department", "email", "photo"]


class OrganizingCommitteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizingCommittee
        fields = ["id", "name", "department", "email", "photo"]


class AccommodationOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationOption
        fields = ["id", "name", "description", "url", "photo", "order"]


class AccommodationInfoSerializer(serializers.ModelSerializer):
    options = AccommodationOptionSerializer(many=True, read_only=True)

    class Meta:
        model = AccommodationInfo
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
        return data

    def update(self, instance, validated_data):
        if "photo" in validated_data:
            photo = validated_data.pop("photo")

            # If photo is explicitly set to None, delete existing photo
            if photo is None and instance.photo:
                instance.photo.delete(save=False)
                instance.photo = None
            elif photo:
                # delete old photo if exists
                if instance.photo:
                    instance.photo.delete(save=False)
                instance.photo = photo

        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if instance.status == "approved" and instance.published_participant:
            self._update_published_data(instance)

        return instance

    def _update_published_data(self, instance):
        # Update Participant
        participant = instance.published_participant
        participant.name = instance.name
        participant.email = instance.email
        participant.affiliation = instance.affiliation

        # Handle photo update
        if instance.photo:
            participant.photo = instance.photo
        else:
            if participant.photo:
                participant.photo.delete(save=False)
            participant.photo = None

        participant.save()

        abstract = instance.published_abstract
        if instance.abstract_title or instance.abstract_text:
            all_authors = instance.name
            if instance.additional_authors:
                all_authors += f", {instance.additional_authors}"

            all_affiliations = instance.affiliation
            if instance.additional_affiliations:
                all_affiliations += f"\n{instance.additional_affiliations}"

            if instance.published_abstract:
                abstract = instance.published_abstract
                abstract.title = (
                    instance.abstract_title or f"Presentation by {instance.name}"
                )
                abstract.text = instance.abstract_text
                abstract.authors = all_authors
                abstract.department = all_affiliations
                abstract.save()
            else:
                abstract = Abstract.objects.create(
                    conference=instance.conference,
                    participant=participant,
                    title=instance.abstract_title or f"Presentation by {instance.name}",
                    text=instance.abstract_text,
                    authors=all_authors,
                    department=all_affiliations,
                )
                instance.published_abstract = abstract
                instance.save()
        if abstract:
            try:
                talk = abstract.talk
                talk.title = abstract.title
                talk.participant = participant
                talk.save()
            except Exception:  # noqa: BLE001
                from .models import Talk

                Talk.objects.create(
                    conference=instance.conference,
                    title=abstract.title,
                    participant=participant,
                    abstract=abstract,
                    talk_type="talk",
                    is_scheduled=False,
                )


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
        return data

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
    # ReadOnlyField: year/status are model @property methods, not fields,
    # and slug lives on the related Conference row, so none of the three
    # is auto-discovered by ModelSerializer.
    slug = serializers.ReadOnlyField(source="conference.slug")
    year = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()

    class Meta:
        model = ConferenceInfo
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


class ConferenceInfoWriteSerializer(serializers.ModelSerializer):
    registration_opening = BlankAsNoneDateField(required=False, allow_null=True)
    registration_deadline = BlankAsNoneDateField(required=False, allow_null=True)
    submission_edit_deadline = BlankAsNoneDateField(required=False, allow_null=True)
    date_start = BlankAsNoneDateField(required=False, allow_null=True)
    date_end = BlankAsNoneDateField(required=False, allow_null=True)

    class Meta:
        model = ConferenceInfo
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
            "registration_fee_note",
            "grant_text",
            "venue_text",
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
        return attrs


class ConferenceInfoSerializer(serializers.ModelSerializer):
    # year is a derived @property on the model (F6), never writable.
    year = serializers.ReadOnlyField()

    class Meta:
        model = ConferenceInfo
        fields = ["id", *ConferenceInfoWriteSerializer.Meta.fields, "year"]
