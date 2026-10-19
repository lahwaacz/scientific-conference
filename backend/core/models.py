import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.utils import timezone

from .names import compute_sort_key

RESERVED_SLUGS = {"auth", "admin", "api", "conferences", "media", "static"}

CONTRIBUTION_TYPES = [
    ("talk", "Talk"),
    ("poster", "Poster"),
    ("attend", "Just attend"),
]


class Conference(models.Model):
    slug = models.SlugField(max_length=64, unique=True)

    # Logistics
    title = models.CharField(max_length=200, blank=True, default="")
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, default="")
    card_photo = models.ImageField(upload_to="conferences/", blank=True, null=True)
    hero_photo = models.ImageField(upload_to="conferences/", blank=True, null=True)
    venue_photo = models.ImageField(upload_to="conferences/", blank=True, null=True)
    short_description = models.CharField(max_length=300, blank=True, default="")
    badge_title = models.CharField(max_length=100, blank=True, default="")

    # Web content
    description = models.TextField(blank=True)
    registration_instructions = models.TextField(blank=True)
    registration_opening = models.DateField(null=True, blank=True)
    registration_deadline = models.DateField(null=True, blank=True)
    submission_edit_deadline = models.DateField(null=True, blank=True)
    registration_allow_talk = models.BooleanField(default=True)
    registration_allow_poster = models.BooleanField(default=True)
    registration_allow_attend = models.BooleanField(default=True)
    registration_fee_note = models.CharField(
        max_length=300, blank=True, default="Conference fee is free of charge"
    )
    grant_text = models.TextField(
        blank=True,
        default="This workshop was supported by the Grant Agency of the Czech Technical University in Prague, grant No. SVK 44/25/F4.",
    )
    venue_text = models.TextField(
        blank=True,
        default="Faculty of Nuclear Sciences and Physical Engineering, Trojanova 13, 120 00, Prague",
    )
    footer_venue_text = models.TextField(
        blank=True,
        default="Faculty of Nuclear Sciences and Physical Engineering, Trojanova 13, 120 00, Prague",
    )
    conference_office_text = models.TextField(
        blank=True,
        default="D. Landovská, Department of Software Engineering, Faculty of Nuclear Sciences and Physical Engineering, Czech Technical University in Prague",
    )
    website_url = models.URLField(blank=True)
    poster_url = models.URLField(blank=True)
    info_desk_email = models.EmailField(blank=True)
    venue_map_embed_url = models.TextField(
        blank=True,
        default="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d1280.3159498589002!2d14.416798000000002!3d50.074455!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x470b94f4244a8a5f%3A0xcd7ab24cf4bcbdc7!2sTrojanova%20339%2F13%2C%20120%2000%20Nov%C3%A9%20M%C4%9Bsto%2C%20Czechia!5e0!3m2!1sen!2sus!4v1791310756815!5m2!1sen!2sus",
    )
    copyright_text = models.CharField(
        max_length=200, blank=True, default="©2025 MMG, FNSPE CTU in Prague"
    )

    # Program page
    program_text = models.TextField(blank=True)

    # Accommodation page
    accommodation_description = models.TextField(blank=True)

    def clean(self):
        super().clean()
        # full_clean() path (Django admin, scripts). DRF never calls it, so
        # ConferenceInfoWriteSerializer.validate() mirrors these rules.
        errors = {}
        # reserved-word validation (F2)
        if self.slug and self.slug.lower() in RESERVED_SLUGS:
            errors["slug"] = f'"{self.slug}" is a reserved word.'
        deadline_errors = []
        if self.submission_edit_deadline is not None:
            if (
                self.registration_deadline is not None
                and self.submission_edit_deadline < self.registration_deadline
            ):
                deadline_errors.append(
                    "Submission editing deadline must be on or after the registration deadline."
                )
            if (
                self.date_end is not None
                and self.submission_edit_deadline > self.date_end
            ):
                deadline_errors.append(
                    "Submission editing deadline must be on or before the conference end date."
                )
        if deadline_errors:
            errors["submission_edit_deadline"] = deadline_errors
        if not any(
            (
                self.registration_allow_talk,
                self.registration_allow_poster,
                self.registration_allow_attend,
            )
        ):
            errors["registration_allow_talk"] = (
                "At least one contribution type must be allowed."
            )
        if errors:
            raise ValidationError(errors)

    @property
    def allowed_contribution_types(self):
        allowed = []
        if self.registration_allow_talk:
            allowed.append("talk")
        if self.registration_allow_poster:
            allowed.append("poster")
        if self.registration_allow_attend:
            allowed.append("attend")
        return tuple(allowed)

    def __str__(self):
        return self.slug

    def is_referenced(self):
        """True when any row still points at this conference.

        The admin allows a delete only while this is False: every domain
        model cascades, so a delete would take the referencing rows with it.
        """
        return any(
            relation.related_model._default_manager.filter(
                **{relation.field.name: self}
            ).exists()
            for relation in self._meta.get_fields(include_hidden=True)
            if isinstance(relation, ForeignObjectRel)
        )

    @property
    def year(self):
        # derived, never a column (F6)
        return self.date_start.year if self.date_start else None

    def is_registration_open(self, on=None):
        """Registration window [opening, deadline], bounds optional.

        A conference that has ended always has closed registration.
        """
        today = on or timezone.localdate()
        if self.date_end and today > self.date_end:
            return False
        opened = not self.registration_opening or today >= self.registration_opening
        not_closed = (
            not self.registration_deadline or today <= self.registration_deadline
        )
        return opened and not_closed

    def is_submission_edit_open(self, on=None):
        """Submission-editing window.

        The conference end date always ends editing. Otherwise an explicit
        ``submission_edit_deadline`` (inclusive) wins; when unset, editing
        falls back to the day before the conference starts (open while
        ``today < date_start``); with neither set, editing stays open.
        Registration closing never blocks an edit.
        """
        today = on or timezone.localdate()
        if self.date_end is not None and today > self.date_end:
            return False
        if self.submission_edit_deadline is not None:
            return today <= self.submission_edit_deadline
        if self.date_start is not None:
            return today < self.date_start
        return True

    @property
    def status(self):
        # "running" | "future" | "past"; missing dates -> "future"
        if not self.date_start or not self.date_end:
            return "future"
        today = timezone.localdate()
        if self.date_start <= today <= self.date_end:
            return "running"
        if today < self.date_start:
            return "future"
        return "past"


class ConferenceDay(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="days", on_delete=models.CASCADE
    )
    date = models.DateField()

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return str(self.date)


class Session(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="sessions", on_delete=models.CASCADE
    )
    day = models.ForeignKey(
        ConferenceDay, related_name="sessions", on_delete=models.CASCADE
    )
    chair = models.CharField(max_length=255, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.day} | {self.chair or 'Session'}"


class Participant(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="participants", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    sort_key = models.CharField(
        max_length=320, blank=True, default="", editable=False, db_index=True
    )
    contribution_type = models.CharField(
        max_length=20, choices=CONTRIBUTION_TYPES, default="talk"
    )
    affiliation = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="participants/", blank=True, null=True)

    class Meta:
        ordering = ["sort_key", "name"]

    def save(self, *args, **kwargs):
        # Derived from ``name`` on every full save. QuerySet.update() and
        # bulk_create() bypass this, so bulk renames must recompute sort_key.
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "name" in update_fields:
            self.sort_key = compute_sort_key(self.name)
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "sort_key"}
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Abstract(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="abstracts", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=500)
    text = models.TextField(blank=True)
    authors = models.CharField(max_length=500, blank=True)
    department = models.CharField(max_length=255, blank=True)

    # abstract ←→ participant
    participant = models.OneToOneField(
        Participant,
        related_name="abstract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title


class Talk(models.Model):
    TALK_TYPES = [
        ("talk", "Talk"),
        ("break", "Break"),
        ("event", "Event"),
    ]

    conference = models.ForeignKey(
        Conference, related_name="talks", on_delete=models.CASCADE
    )
    day = models.ForeignKey(
        ConferenceDay,
        related_name="items",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    session = models.ForeignKey(
        Session,
        related_name="talks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    talk_type = models.CharField(max_length=20, choices=TALK_TYPES, default="talk")

    title = models.CharField(max_length=255)

    # talk → participant
    participant = models.ForeignKey(
        Participant,
        related_name="talks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # talk → abstract
    abstract = models.OneToOneField(
        Abstract, related_name="talk", on_delete=models.CASCADE, null=True, blank=True
    )

    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    is_scheduled = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.title} ({self.talk_type})"


class Role(models.Model):
    # Reference lookup, intentionally NOT conference-scoped (like auth tables).
    name = models.CharField(max_length=32, unique=True)  # "organizer" | "committee"
    label = models.CharField(max_length=64)  # "Organiser" | "Organising Committee"

    def __str__(self):
        return self.label


class Person(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="people", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    affiliation = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="people/", blank=True, null=True)
    roles = models.ManyToManyField(Role, related_name="people", blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conference_person_profiles",
    )

    def __str__(self):
        return self.name


class AccommodationOption(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="accommodation_options", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    photo = models.ImageField(upload_to="accommodation/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


def generate_tracking_token():
    return secrets.token_urlsafe(24)


class ParticipantSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Published"),
    ]

    conference = models.ForeignKey(
        Conference, related_name="submissions", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    sort_key = models.CharField(
        max_length=320, blank=True, default="", editable=False, db_index=True
    )
    contribution_type = models.CharField(
        max_length=20, choices=CONTRIBUTION_TYPES, default="talk"
    )
    email = models.EmailField()
    affiliation = models.CharField(max_length=500)
    photo = models.ImageField(upload_to="submissions/photos/", blank=True, null=True)

    abstract_title = models.CharField(max_length=500, blank=True, verbose_name="Title")
    abstract_text = models.TextField(blank=True, verbose_name="Abstract")
    additional_authors = models.CharField(
        max_length=500, blank=True, help_text="Co-authors"
    )
    additional_affiliations = models.TextField(
        blank=True, help_text="Affiliations of co-authors"
    )

    arrival_date = models.DateField()
    departure_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admins")
    info = models.TextField(blank=True, help_text="Additional info from participant")
    is_student = models.BooleanField(default=False)

    published_participant = models.ForeignKey(
        "Participant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submission",
    )
    published_abstract = models.ForeignKey(
        "Abstract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submission",
    )

    tracking_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        default=generate_tracking_token,
    )
    linked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_submissions",
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.name} - {self.abstract_title or 'No title'} ({self.status})"

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "name" in update_fields:
            self.sort_key = compute_sort_key(self.name)
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "sort_key"}
        super().save(*args, **kwargs)

    @property
    def stay_duration(self):
        if self.arrival_date and self.departure_date:
            return (self.departure_date - self.arrival_date).days
        return 0

    @property
    def participant_reference(self):
        # pk-None guard must come first: admin add pages render this
        # property against an unsaved instance (no conference -> 500).
        if self.pk is None:
            return ""
        return f"{self.conference.slug}-{self.pk:04d}"

    def _create_participant(self):
        return Participant.objects.create(
            conference=self.conference,
            name=self.name,
            email=self.email,
            affiliation=self.affiliation,
            photo=self.photo,
        )

    def _participant_claimed_by_other(self, participant):
        return (
            ParticipantSubmission.objects.filter(published_participant=participant)
            .exclude(pk=self.pk)
            .exists()
        )

    def _abstract_used_by_other(self, abstract):
        return (
            abstract is not None
            and ParticipantSubmission.objects.filter(published_abstract=abstract)
            .exclude(pk=self.pk)
            .exists()
        )

    def _sync_participant(self, *, clear_photo=False):
        """Return the public participant owned by this submission.

        A Participant can own only one public Abstract, so a second
        submission with the same email must get its own row. Reusing it
        would let that submission overwrite or delete the first
        submission's abstract and talk.
        """
        participant = self.published_participant
        if participant is not None and self._participant_claimed_by_other(participant):
            participant = None

        if participant is None and self.email:
            try:
                participant = Participant.objects.get(
                    email=self.email, conference=self.conference
                )
            except (
                Participant.DoesNotExist,
                Participant.MultipleObjectsReturned,
            ):
                participant = None

            if participant is not None and self._participant_claimed_by_other(
                participant
            ):
                participant = None

        old_photo = None
        if participant is None:
            participant = self._create_participant()
        else:
            participant.name = self.name
            participant.affiliation = self.affiliation
            participant.email = self.email
            if self.photo:
                participant.photo = self.photo
            elif clear_photo and participant.photo:
                old_photo = participant.photo
                participant.photo = None

        participant.contribution_type = self.contribution_type
        participant.save()
        return participant, old_photo

    def _delete_publication_talk(self, abstract):
        talk = getattr(abstract, "talk", None)
        if talk is None:
            return
        if talk.is_scheduled:
            raise ValidationError(
                {
                    "contribution_type": (
                        "Unschedule the talk before changing this submission "
                        "to poster or just attend."
                    )
                }
            )
        talk.delete()

    def _sync_abstract(self, participant):
        abstract = self.published_abstract
        if self._abstract_used_by_other(abstract):
            # Legacy shared rows: never mutate an abstract another
            # submission points at. Its owner keeps it.
            abstract = None

        if abstract is None:
            abstract = getattr(participant, "abstract", None)
            if self._abstract_used_by_other(abstract):
                abstract = None

        if self.contribution_type == "attend":
            if abstract is not None:
                self._delete_publication_talk(abstract)
                abstract.delete()
            self.published_abstract = None
            return None

        if abstract is None and getattr(participant, "abstract", None) is not None:
            raise ValidationError(
                {
                    "contribution_type": (
                        "This participant already has a published contribution."
                    )
                }
            )

        all_authors = self.name
        if self.additional_authors:
            all_authors += f", {self.additional_authors}"

        all_affiliations = self.affiliation
        if self.additional_affiliations:
            all_affiliations += f"\n{self.additional_affiliations}"

        title = self.abstract_title or f"Presentation by {self.name}"
        if abstract is not None:
            if abstract.participant_id != participant.pk:
                abstract.participant = participant
            abstract.title = title
            abstract.text = self.abstract_text
            abstract.authors = all_authors
            abstract.department = all_affiliations
            abstract.save()
        else:
            abstract = Abstract.objects.create(
                conference=self.conference,
                participant=participant,
                title=title,
                text=self.abstract_text,
                authors=all_authors,
                department=all_affiliations,
            )
        self.published_abstract = abstract
        return abstract

    def _sync_talk(self, participant, abstract):
        if abstract is None:
            return None
        if self.contribution_type != "talk":
            self._delete_publication_talk(abstract)
            return None

        talk = getattr(abstract, "talk", None)
        if talk is not None:
            talk.title = abstract.title
            talk.participant = participant
            talk.save()
            return talk
        return Talk.objects.create(
            conference=self.conference,
            title=abstract.title,
            participant=participant,
            abstract=abstract,
            talk_type="talk",
            is_scheduled=False,
        )

    @transaction.atomic
    def publish(self):
        from django.utils import timezone

        participant, _ = self._sync_participant()
        abstract = self._sync_abstract(participant)
        talk = self._sync_talk(participant, abstract)
        self.published_participant = participant
        self.published_abstract = abstract
        self.status = "approved"
        self.reviewed_at = timezone.now()
        self.save()

        return participant, abstract, talk

    @transaction.atomic
    def sync_published_data(self):
        if self.published_participant is None:
            return None, None, None

        participant, old_photo = self._sync_participant(clear_photo=True)
        abstract = self._sync_abstract(participant)
        talk = self._sync_talk(participant, abstract)
        self.published_participant = participant
        self.published_abstract = abstract
        self.save()
        if old_photo:
            old_photo.delete(save=False)
        return participant, abstract, talk

    def delete(self, *args, **kwargs):

        if self.status == "approved":
            if self.published_abstract and not self._abstract_used_by_other(
                self.published_abstract
            ):
                self.published_abstract.delete()

            if self.published_participant and not self._participant_claimed_by_other(
                self.published_participant
            ):
                self.published_participant.delete()

        if self.photo:
            self.photo.delete(save=False)

        super().delete(*args, **kwargs)


class HikingRoute(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="hiking_routes", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    way_description = models.TextField(blank=True)
    map_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Hiking Route"

    def __str__(self):
        return self.name


class HikingStop(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="hiking_stops", on_delete=models.CASCADE
    )
    route = models.ForeignKey(
        HikingRoute, on_delete=models.CASCADE, related_name="stops"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="hiking/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Hiking Stop"

    def __str__(self):
        return self.name
