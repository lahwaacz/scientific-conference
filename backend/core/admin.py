from django import forms
from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .importing import (
    IMPORTABLE_FIELDS,
    REQUIRED_FIELDS,
    ImportFileError,
    create_submissions,
    decode_csv_bytes,
    field_label,
    parse_csv,
    parsed_from_session,
    parsed_to_session,
    resolve_date_defaults,
    resolve_mapping,
    summarise,
    validate_rows,
)
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
    # Conferences are created here and their configuration lives on this
    # row; the SPA admin edits the same fields. Deleting one cascades to
    # every domain row, so it is offered only while nothing references it.
    fieldsets = (
        (None, {"fields": ("slug",)}),
        (
            "Logistics",
            {
                "fields": (
                    "title",
                    "date_start",
                    "date_end",
                    "location",
                    "card_photo",
                    "hero_photo",
                    "venue_photo",
                    "short_description",
                    "badge_title",
                )
            },
        ),
        (
            "Web content",
            {
                "fields": (
                    "description",
                    "website_url",
                    "poster_url",
                    "info_desk_email",
                    "copyright_text",
                    "grant_text",
                )
            },
        ),
        (
            "Registration",
            {
                "fields": (
                    "registration_instructions",
                    "registration_opening",
                    "registration_deadline",
                    "submission_edit_deadline",
                    "registration_allow_talk",
                    "registration_allow_poster",
                    "registration_allow_attend",
                    "registration_fee_note",
                )
            },
        ),
        (
            "Venue",
            {
                "fields": (
                    "venue_text",
                    "footer_venue_text",
                    "conference_office_text",
                    "venue_map_embed_url",
                )
            },
        ),
        ("Program", {"fields": ("program_text",)}),
        ("Accommodation", {"fields": ("accommodation_description",)}),
    )
    list_display = ("slug",)
    search_fields = ("slug",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_referenced():
            return False
        return super().has_delete_permission(request, obj)

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if (
            obj is not None
            and self.has_view_or_change_permission(request, obj)
            and obj.is_referenced()
        ):
            self.message_user(
                request,
                "This conference still has related objects and cannot be deleted.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(
                reverse("admin:core_conference_change", args=[obj.pk])
            )
        return super().delete_view(request, object_id, extra_context)

    def delete_model(self, request, obj):
        if obj.is_referenced():
            raise PermissionDenied(
                "This conference still has related objects and cannot be deleted."
            )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        if any(conference.is_referenced() for conference in queryset):
            raise PermissionDenied(
                "Conferences that still have related objects cannot be deleted."
            )
        super().delete_queryset(request, queryset)


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


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    # Reference lookup data (like auth tables): no conference FK by design.
    list_display = ("name", "label")
    search_fields = ("name",)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("conference", "name", "affiliation", "email")
    list_filter = ("conference", "roles")
    search_fields = ("name", "affiliation", "email")
    filter_horizontal = ("roles",)
    autocomplete_fields = ("user",)
    list_select_related = ("user",)


SESSION_KEY = "participantsubmission_import"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
PREVIEW_LIMIT = 200


class ParticipantSubmissionImportForm(forms.Form):
    conference = forms.ModelChoiceField(
        queryset=Conference.objects.order_by("slug"),
        help_text="Imported rows are attached to this conference.",
    )
    csv_file = forms.FileField(
        label="CSV file",
        help_text=(
            "Columns named after participant fields (ignoring case and spaces) "
            "are matched automatically; any other column can be mapped on the "
            "next screen."
        ),
    )

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if upload.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                f"The file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        return upload


@admin.register(ParticipantSubmission)
class ParticipantSubmissionAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/participantsubmission/change_list.html"
    list_display = [
        "conference",
        "name",
        "contribution_type",
        "email",
        "abstract_title",
        "status",
        "participant_reference",
        "linked_user",
        "submitted_at",
    ]
    list_filter = ["conference", "status", "contribution_type", "submitted_at"]
    search_fields = ["name", "email", "abstract_title"]
    readonly_fields = [
        "tracking_token",
        "participant_reference",
        "submitted_at",
        "reviewed_at",
    ]

    actions = ["publish_selected"]

    def publish_selected(self, request, queryset):
        published = 0
        failed = 0
        skipped = 0
        for submission in queryset:
            if submission.status == "approved":
                skipped += 1
                continue
            try:
                submission.publish()
                published += 1
            except ValidationError as exc:
                failed += 1
                self.message_user(
                    request,
                    f"{submission.name}: {exc.messages[0]}",
                    level=messages.ERROR,
                )
        summary = f"{published} published"
        if failed:
            summary += f", {failed} failed"
        if skipped:
            summary += f", {skipped} already published"
        self.message_user(
            request,
            summary,
            level=messages.WARNING if failed else messages.SUCCESS,
        )

    publish_selected.short_description = "Publish selected submissions"

    # CSV import wizard: upload -> preview -> confirm
    def get_urls(self):
        custom = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_csv_view),
                name="core_participantsubmission_import",
            ),
        ]
        return custom + super().get_urls()

    def _render_import(self, request, context):
        return TemplateResponse(
            request, "admin/core/participantsubmission/import.html", context
        )

    def _import_context(self, request, **extra):
        context = {
            **self.admin_site.each_context(request),
            "title": "Import pre-registered participants",
            "opts": self.model._meta,
            "form": None,
            "preview": None,
        }
        context.update(extra)
        return context

    def import_csv_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied

        if request.method != "POST":
            request.session.pop(SESSION_KEY, None)
            return self._render_import(
                request,
                self._import_context(request, form=ParticipantSubmissionImportForm()),
            )

        step = request.POST.get("step")
        if step == "confirm":
            return self._confirm_import(request)
        if step == "remap":
            return self._remap_import(request)
        return self._preview_import(request)

    def _preview_import(self, request):
        form = ParticipantSubmissionImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._render_import(
                request, self._import_context(request, form=form)
            )

        conference = form.cleaned_data["conference"]
        upload = form.cleaned_data["csv_file"]
        try:
            parsed = parse_csv(decode_csv_bytes(upload.read()))
        except ImportFileError as exc:
            form.add_error("csv_file", str(exc))
            return self._render_import(
                request, self._import_context(request, form=form)
            )

        request.session[SESSION_KEY] = {
            "conference_id": conference.pk,
            "filename": upload.name,
            "parsed": parsed_to_session(parsed),
            "manual": {},
        }
        return self._render_preview(request, conference, upload.name, parsed, {})

    def _remap_import(self, request):
        loaded = self._load_session(request)
        if loaded is None:
            return self._session_expired(request)
        conference, filename, parsed, manual = loaded
        manual.update(self._manual_from_post(request))
        self._store_manual(request, manual)
        return self._render_preview(request, conference, filename, parsed, manual)

    def _confirm_import(self, request):
        loaded = self._load_session(request)
        if loaded is None:
            return self._session_expired(request)
        conference, filename, parsed, manual = loaded
        manual.update(self._manual_from_post(request))

        mapping = resolve_mapping(parsed.headers, manual)
        if self._missing_required(mapping):
            self._store_manual(request, manual)
            return self._render_preview(request, conference, filename, parsed, manual)
        try:
            defaults = resolve_date_defaults(conference, mapping)
        except ImportFileError:
            self._store_manual(request, manual)
            return self._render_preview(request, conference, filename, parsed, manual)

        request.session.pop(SESSION_KEY, None)
        with transaction.atomic():
            results = validate_rows(parsed, mapping, conference, defaults)
            summary = create_submissions(results, conference, defaults)

        self.message_user(
            request,
            f'Imported {summary.created} participant(s) into "{conference.slug}". '
            f"Skipped {summary.skipped} duplicate(s), {summary.failed} error row(s).",
            level=messages.SUCCESS,
        )
        return HttpResponseRedirect(
            reverse("admin:core_participantsubmission_changelist")
        )

    def _render_preview(self, request, conference, filename, parsed, manual):
        mapping = resolve_mapping(parsed.headers, manual)
        missing = self._missing_required(mapping)

        dates_error = None
        results = []
        if not missing:
            try:
                defaults = resolve_date_defaults(conference, mapping)
            except ImportFileError as exc:
                dates_error = str(exc)
            else:
                results = validate_rows(parsed, mapping, conference, defaults)

        columns = [
            (name, field_label(name))
            for name, _ in IMPORTABLE_FIELDS
            if name in mapping.field_to_indices
        ]
        column_names = [name for name, _ in columns]
        rows = [
            {
                "line": result.line,
                "cells": [result.values.get(name, "") for name in column_names],
                "status": result.status,
                "messages": result.messages,
            }
            for result in results[:PREVIEW_LIMIT]
        ]

        preview = {
            "conference": conference,
            "filename": filename,
            "configurable": mapping.configurable,
            "recognized": mapping.recognized,
            "conflicts": mapping.conflicts,
            "importable": IMPORTABLE_FIELDS,
            "columns": columns,
            "missing_required": missing,
            "dates_error": dates_error,
            "rows": rows,
            "truncated": len(results) > PREVIEW_LIMIT,
            "summary": summarise(results) if results else None,
        }
        return self._render_import(
            request, self._import_context(request, preview=preview)
        )

    def _load_session(self, request):
        stored = request.session.get(SESSION_KEY)
        if not stored:
            return None
        conference = Conference.objects.filter(pk=stored["conference_id"]).first()
        if conference is None:
            return None
        parsed = parsed_from_session(stored["parsed"])
        manual = {int(key): value for key, value in stored.get("manual", {}).items()}
        return conference, stored["filename"], parsed, manual

    def _store_manual(self, request, manual):
        stored = request.session.get(SESSION_KEY, {})
        stored["manual"] = {str(key): value for key, value in manual.items()}
        request.session[SESSION_KEY] = stored

    def _manual_from_post(self, request):
        manual = {}
        for key in request.POST:
            if not key.startswith("map_"):
                continue
            try:
                index = int(key[4:])
            except ValueError:
                continue
            manual[index] = request.POST.get(key, "").strip()
        return manual

    def _missing_required(self, mapping):
        return [
            field_label(name)
            for name in REQUIRED_FIELDS
            if name not in mapping.field_to_indices
        ]

    def _session_expired(self, request):
        self.message_user(
            request,
            "The import session expired. Please upload the file again.",
            level=messages.ERROR,
        )
        return HttpResponseRedirect(reverse("admin:core_participantsubmission_import"))


@admin.register(AccommodationOption)
class AccommodationOptionAdmin(admin.ModelAdmin):
    list_display = ("conference", "name", "order")
    list_filter = ("conference",)
    list_select_related = ("conference",)


class HikingStopInline(admin.TabularInline):
    model = HikingStop
    extra = 1


@admin.register(HikingRoute)
class HikingRouteAdmin(admin.ModelAdmin):
    list_display = ("conference", "name")
    list_filter = ("conference",)
    inlines = [HikingStopInline]
