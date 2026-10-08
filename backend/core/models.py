import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

RESERVED_SLUGS = {"auth", "admin", "api", "conferences", "media", "static"}


class Conference(models.Model):
    # Slug-only identity; the logistics fields (title, dates, location,
    # card/hero photos, short description, badge title) live on ConferenceInfo.
    slug = models.SlugField(max_length=64, unique=True)

    def clean(self):
        # reserved-word validation (F2)
        if self.slug and self.slug.lower() in RESERVED_SLUGS:
            raise ValidationError({"slug": f'"{self.slug}" is a reserved word.'})

    def __str__(self):
        return self.slug


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
    affiliation = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="participants/", blank=True, null=True)

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


class Organizer(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="organizers", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="organizers/", blank=True, null=True)

    def __str__(self):
        return self.name


class OrganizingCommittee(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="committee_members", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="organizingCommittee/", blank=True, null=True)

    def __str__(self):
        return self.name


class AccommodationInfo(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="accommodation_infos", on_delete=models.CASCADE
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Accommodation Info"


class AccommodationOption(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="accommodation_options", on_delete=models.CASCADE
    )
    info = models.ForeignKey(
        AccommodationInfo, on_delete=models.CASCADE, related_name="options"
    )
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    url = models.URLField(blank=True)
    photo = models.ImageField(upload_to="accommodation/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


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
    email = models.EmailField()
    affiliation = models.CharField(max_length=500)
    photo = models.ImageField(upload_to="submissions/photos/", blank=True, null=True)

    abstract_title = models.CharField(max_length=500, blank=True)
    abstract_text = models.TextField(blank=True)
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

    def publish(self):
        from django.utils import timezone

        if self.published_participant:
            participant = self.published_participant
            # Sync the participant-controlled fields the way the dedup-update
            # branch below does; otherwise a participant edit followed by an
            # admin re-publish leaves the public row stale.
            participant.name = self.name
            participant.affiliation = self.affiliation
            participant.email = self.email
            if self.photo:
                participant.photo = self.photo
            participant.save()
        else:
            if self.email:
                try:
                    participant = Participant.objects.get(
                        email=self.email, conference=self.conference
                    )
                    participant.name = self.name
                    participant.affiliation = self.affiliation
                    if self.photo:
                        participant.photo = self.photo
                    participant.save()
                except Participant.DoesNotExist:
                    participant = Participant.objects.create(
                        conference=self.conference,
                        name=self.name,
                        email=self.email,
                        affiliation=self.affiliation,
                        photo=self.photo,
                    )
                except Participant.MultipleObjectsReturned:
                    participant = Participant.objects.create(
                        conference=self.conference,
                        name=self.name,
                        email=self.email,
                        affiliation=self.affiliation,
                        photo=self.photo,
                    )
            else:
                participant = Participant.objects.create(
                    conference=self.conference,
                    name=self.name,
                    email=self.email,
                    affiliation=self.affiliation,
                    photo=self.photo,
                )

        abstract = None
        if self.abstract_title or self.abstract_text:
            all_authors = self.name
            if self.additional_authors:
                all_authors += f", {self.additional_authors}"

            all_affiliations = self.affiliation
            if self.additional_affiliations:
                all_affiliations += f"\n{self.additional_affiliations}"

            if hasattr(participant, "abstract") and participant.abstract:
                abstract = participant.abstract
                abstract.title = self.abstract_title or f"Presentation by {self.name}"
                abstract.text = self.abstract_text
                abstract.authors = all_authors
                abstract.department = all_affiliations
                abstract.save()
            else:
                abstract = Abstract.objects.create(
                    conference=self.conference,
                    participant=participant,
                    title=self.abstract_title or f"Presentation by {self.name}",
                    text=self.abstract_text,
                    authors=all_authors,
                    department=all_affiliations,
                )

        talk = None
        if abstract:
            if hasattr(abstract, "talk") and abstract.talk:
                talk = abstract.talk
                talk.title = abstract.title
                talk.participant = participant
                talk.save()
            else:
                talk = Talk.objects.create(
                    conference=self.conference,
                    title=abstract.title,
                    participant=participant,
                    abstract=abstract,
                    talk_type="talk",
                    is_scheduled=False,
                )
        self.published_participant = participant
        self.published_abstract = abstract
        self.status = "approved"
        self.reviewed_at = timezone.now()
        self.save()

        return participant, abstract, talk

    def delete(self, *args, **kwargs):

        if self.status == "approved":
            if self.published_abstract:
                self.published_abstract.delete()

            if self.published_participant:
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


class ConferenceInfo(models.Model):
    conference = models.ForeignKey(
        Conference, related_name="conference_infos", on_delete=models.CASCADE
    )
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

    class Meta:
        verbose_name = "Conference Info"

    def clean(self):
        super().clean()
        if self.submission_edit_deadline is not None:
            if (
                self.registration_deadline is not None
                and self.submission_edit_deadline < self.registration_deadline
            ):
                raise ValidationError(
                    {
                        "submission_edit_deadline": "Submission editing deadline must be on or after the registration deadline."
                    }
                )
            if (
                self.date_end is not None
                and self.submission_edit_deadline > self.date_end
            ):
                raise ValidationError(
                    {
                        "submission_edit_deadline": "Submission editing deadline must be on or before the conference end date."
                    }
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
