import datetime

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


class SessionSerializer(serializers.ModelSerializer):
    talks = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = ["id", "day", "chair", "start_time", "end_time", "talks"]

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
        ]
        read_only_fields = [
            "submitted_at",
            "reviewed_at",
            "published_participant",
            "published_abstract",
            "stay_duration",
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
                    title=abstract.title,
                    participant=participant,
                    abstract=abstract,
                    talk_type="talk",
                    is_scheduled=False,
                )


class HikingStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = HikingStop
        fields = "__all__"


class HikingRouteSerializer(serializers.ModelSerializer):
    stops = HikingStopSerializer(many=True, read_only=True)

    class Meta:
        model = HikingRoute
        fields = "__all__"


class ConferenceInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConferenceInfo
        fields = "__all__"
