from django.db import models


class ConferenceDay(models.Model):
    date = models.DateField()

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return str(self.date)


class Session(models.Model):
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
    name = models.CharField(max_length=255)
    affiliation = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="participants/", blank=True, null=True)

    def __str__(self):
        return self.name


class Abstract(models.Model):
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
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="organizers/", blank=True, null=True)

    def __str__(self):
        return self.name


class OrganizingCommittee(models.Model):
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=500, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="organizingCommittee/", blank=True, null=True)

    def __str__(self):
        return self.name


class AccommodationInfo(models.Model):
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Accommodation Info"


class AccommodationOption(models.Model):
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


class ParticipantSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Published"),
    ]

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
    is_student = models.BooleanField(default=False)  # ← для галочки Student

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

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.name} - {self.abstract_title or 'No title'} ({self.status})"

    @property
    def stay_duration(self):
        if self.arrival_date and self.departure_date:
            return (self.departure_date - self.arrival_date).days
        return 0

    def publish(self):
        from django.utils import timezone

        if self.published_participant:
            participant = self.published_participant
        else:
            if self.email:
                try:
                    participant = Participant.objects.get(email=self.email)
                    participant.name = self.name
                    participant.affiliation = self.affiliation
                    if self.photo:
                        participant.photo = self.photo
                    participant.save()
                except Participant.DoesNotExist:
                    participant = Participant.objects.create(
                        name=self.name,
                        email=self.email,
                        affiliation=self.affiliation,
                        photo=self.photo,
                    )
                except Participant.MultipleObjectsReturned:
                    participant = Participant.objects.create(
                        name=self.name,
                        email=self.email,
                        affiliation=self.affiliation,
                        photo=self.photo,
                    )
            else:
                participant = Participant.objects.create(
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
    name = models.CharField(max_length=200)
    way_description = models.TextField(blank=True)
    map_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Hiking Route"


class HikingStop(models.Model):
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
    title = models.CharField(max_length=200, default="Workshop on Scientific Computing")
    year = models.PositiveIntegerField(default=2026)
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, default="Děčín")
    description = models.TextField(blank=True)
    registration_instructions = models.TextField(blank=True)
    registration_deadline = models.DateField(null=True, blank=True)
    registration_fee_note = models.CharField(
        max_length=300, blank=True, default="Conference fee is free of charge"
    )
    grant_text = models.TextField(
        blank=True,
        default="This workshop was supported by the Grant Agency of the Czech Technical University in Prague, grant No. SVK 44/25/F4.",
    )
    venue_text = models.TextField(
        blank=True,
        default="Faculty of Nuclear Sciences and Physical Engineering, Pohraniční 1288/1, 405 02 Děčín and MS Teams online",
    )
    conference_office_text = models.TextField(
        blank=True,
        default="D. Landovská, Department of Software Engineering, Faculty of Nuclear Sciences and Physical Engineering, Czech Technical University in Prague",
    )
    website_url = models.URLField(blank=True)
    poster_url = models.URLField(blank=True)
    info_desk_email = models.EmailField(blank=True, default="pauspetr@cvut.cz")
    venue_map_embed_url = models.TextField(
        blank=True,
        default="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2522.8151323874063!2d14.21346707611837!3d50.77900046365381!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x47099fd1ace90813%3A0x7d351b85e2789db!2sCTU%20Decin!5e0!3m2!1sru!2scz!4v1777641891915!5m2!1sru!2scz",
    )
    copyright_text = models.CharField(
        max_length=200, blank=True, default="©2025 MMG, FNSPE CTU in Prague"
    )
    # Program page
    program_local_registration_text = models.TextField(
        blank=True,
        default="Registration for local participants takes place at the conference venue: Thursday: from 13:00 to 14:00 + during coffee breaks between the sessions",
    )
    program_regular_talks_text = models.TextField(
        blank=True,
        default="Oral presentation duration is 20 min = 15 min talk + 5 min for discussion.",
    )
    program_poster_talks_text = models.TextField(
        blank=True,
        default="Each poster will be briefly introduced in a short 1–3 min presentation.",
    )

    class Meta:
        verbose_name = "Conference Info"
