# Create your views here.

from urllib import request, response

from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import *
from .serializers import *


def generate_program_pdf(request):
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os, datetime

    try:
        auth = JWTAuthentication()
        result = auth.authenticate(request)
        if result is None or not result[0].is_staff:
            return HttpResponse(status=403)
    except Exception:
        return HttpResponse(status=403)

    font_path = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
    font_bold_path = os.path.join(
        os.path.dirname(__file__), "fonts", "DejaVuSans-Bold.ttf"
    )
    pdfmetrics.registerFont(TTFont("DejaVu", font_path))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", font_bold_path))

    days = ConferenceDay.objects.prefetch_related(
        "sessions__talks__participant", "items__participant"
    ).order_by("date")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="program.pdf"'

    page_width, page_height = A4
    c = canvas.Canvas(response, pagesize=A4)

    margin_left = 20 * mm
    margin_right = 20 * mm
    content_width = page_width - margin_left - margin_right

    col_time = 30 * mm
    col_name = 38 * mm
    col_title_x = margin_left + col_time + col_name
    col_title_w = content_width - col_time - col_name

    ROW_HEIGHT = 7 * mm
    CHAIR_BEFORE = 6 * mm
    CHAIR_AFTER = 2 * mm
    DAY_AFTER = 10 * mm

    y = page_height - 20 * mm

    BLUE = colors.Color(0 / 255, 101 / 255, 189 / 255)
    DARK = colors.Color(30 / 255, 30 / 255, 30 / 255)
    GRAY = colors.Color(80 / 255, 80 / 255, 80 / 255)

    DAYS_EN = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    MONTHS_EN = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    def check_space(needed):
        nonlocal y
        if y < needed:
            c.showPage()
            y = page_height - 20 * mm

    def fmt_time(t):
        return f"{t.hour:02d}:{t.minute:02d}" if t else ""

    def draw_wrapped(text, x, start_y, max_width, font, size, line_h):
        c.setFont(font, size)
        words = text.split()
        line = ""
        cur_y = start_y
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                if line:
                    c.drawString(x, cur_y, line)
                    cur_y -= line_h
                line = word
        if line:
            c.drawString(x, cur_y, line)
            cur_y -= line_h
        return cur_y

    for day in days:
        check_space(35 * mm)

        day_label = (
            f"{DAYS_EN[day.date.weekday()].upper()}, "
            f"{day.date.day} {MONTHS_EN[day.date.month - 1].upper()} {day.date.year}"
        )
        c.setFillColor(BLUE)
        c.setFont("DejaVu-Bold", 13)
        c.drawString(margin_left, y, day_label)
        y -= 2.5 * mm
        c.setStrokeColor(BLUE)
        c.setLineWidth(1.5)
        c.line(margin_left, y, margin_left + content_width, y)
        y -= 4 * mm

        timeline = []
        for session in day.sessions.all().order_by("start_time"):
            timeline.append(("session", session))
            for talk in session.talks.all().order_by("start_time"):
                timeline.append(("talk", talk))
        for item in day.items.filter(session__isnull=True).order_by("start_time"):
            timeline.append(("item", item))

        timeline.sort(key=lambda e: e[1].start_time or datetime.time(0, 0))

        for entry_type, obj in timeline:
            if entry_type == "session":
                check_space(12 * mm)
                y -= CHAIR_BEFORE

                c.setFillColor(DARK)
                c.setFont("DejaVu-Bold", 10)
                chair_text = f"Chair: {obj.chair}" if obj.chair else "Session"
                c.drawString(margin_left, y, chair_text)
                y -= CHAIR_AFTER + 5 * mm

            elif entry_type in ("talk", "item"):
                check_space(12 * mm)

                title = obj.title or ""
                c.setFont("DejaVu", 9)
                words = title.split()
                lines_count = 1
                line = ""
                for word in words:
                    test = (line + " " + word).strip()
                    if c.stringWidth(test, "DejaVu", 9) <= col_title_w:
                        line = test
                    else:
                        lines_count += 1
                        line = word
                row_h = max(ROW_HEIGHT, lines_count * 4.5 * mm + 2 * mm)

                check_space(row_h + 4 * mm)

                time_str = f"{fmt_time(obj.start_time)} – {fmt_time(obj.end_time)}"
                c.setFillColor(DARK)
                c.setFont("DejaVu-Bold", 9)
                c.drawString(margin_left, y, time_str)

                if hasattr(obj, "participant") and obj.participant:
                    c.setFillColor(DARK)
                    c.setFont("DejaVu", 9)
                    name = obj.participant.name
                    while (
                        c.stringWidth(name, "DejaVu", 9) > col_name - 3 * mm
                        and len(name) > 4
                    ):
                        name = name[:-2] + "."
                    c.drawString(margin_left + col_time, y, name)

                c.setFillColor(DARK)
                draw_wrapped(title, col_title_x, y, col_title_w, "DejaVu", 9, 4.5 * mm)

                y -= row_h

        y -= DAY_AFTER

    c.save()
    return response


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class AccommodationInfoView(APIView):
    def get(self, request):
        obj, _ = AccommodationInfo.objects.get_or_create(id=1)
        serializer = AccommodationInfoSerializer(obj)
        return Response(serializer.data)


class AccommodationOptionListView(generics.ListAPIView):
    queryset = AccommodationOption.objects.all().order_by("order")
    serializer_class = AccommodationOptionSerializer


class AccommodationInfoEditView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser]

    def patch(self, request):
        obj, _ = AccommodationInfo.objects.get_or_create(id=1)
        serializer = AccommodationInfoSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class AccommodationOptionEditView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        info, _ = AccommodationInfo.objects.get_or_create(id=1)
        data = request.data.copy()
        data["info"] = info.id
        serializer = AccommodationOptionWriteSerializer(data=data)
        if serializer.is_valid():
            serializer.save(info=info)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        option = AccommodationOption.objects.get(pk=pk)
        serializer = AccommodationOptionWriteSerializer(
            option, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        AccommodationOption.objects.get(pk=pk).delete()
        return Response(status=204)


accommodation_info_view = AccommodationInfoView.as_view()


def generate_badges_pdf(request):
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    try:
        auth = JWTAuthentication()
        result = auth.authenticate(request)
        if result is None or not result[0].is_staff:
            return HttpResponse(status=403)
    except Exception:
        return HttpResponse(status=403)

    font_path = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
    font_bold_path = os.path.join(
        os.path.dirname(__file__), "fonts", "DejaVuSans-Bold.ttf"
    )
    pdfmetrics.registerFont(TTFont("DejaVu", font_path))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", font_bold_path))

    submissions = ParticipantSubmission.objects.filter(status="approved").order_by(
        "name"
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="badges.pdf"'

    page_width, page_height = A4

    c = canvas.Canvas(response, pagesize=A4)

    badge_w = 85 * mm
    badge_h = 54 * mm
    cols = 2
    rows = 5

    total_w = cols * badge_w
    total_h = rows * badge_h
    offset_x = (page_width - total_w) / 2
    offset_y = (page_height - total_h) / 2

    DARK_BLUE = colors.Color(7 / 255, 67 / 255, 145 / 255)  # rgba(7, 67, 145, 1)
    LIGHT_BLUE = colors.Color(0 / 255, 101 / 255, 189 / 255)  # rgba(0, 101, 189, 1)

    MONTHS = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    badges = list(submissions)
    i = 0

    while i < len(badges):
        for row in range(rows):
            for col in range(cols):
                if i >= len(badges):
                    break
                sub = badges[i]

                x = offset_x + col * badge_w
                y = page_height - offset_y - (row + 1) * badge_h

                accent = LIGHT_BLUE if sub.is_student else DARK_BLUE

                # ── Header ──
                c.setFillColor(accent)
                c.rect(x, y + badge_h - 9 * mm, badge_w, 9 * mm, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("DejaVu-Bold", 9)
                c.drawCentredString(x + badge_w / 2, y + badge_h - 6 * mm, "WSC 2025")

                # ── Name ──
                c.setFillColor(colors.black)
                name = sub.name
                font_size = (
                    19
                    if len(name) <= 16
                    else 16
                    if len(name) <= 22
                    else 13
                    if len(name) <= 30
                    else 10
                )
                c.setFont("DejaVu-Bold", font_size)
                c.drawCentredString(x + badge_w / 2, y + badge_h - 24 * mm, name)

                # ── Affiliation ──
                c.setFont("DejaVu", 7.5)
                affil = sub.affiliation or ""
                c.drawCentredString(x + badge_w / 2, y + badge_h - 33 * mm, affil)

                # ── Footer ──
                c.setFillColor(accent)
                c.rect(x, y, badge_w, 8 * mm, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("DejaVu", 6.5)
                if sub.arrival_date and sub.departure_date:
                    arr = sub.arrival_date
                    dep = sub.departure_date
                    arrival_str = f"{arr.day} {MONTHS[arr.month - 1]}"
                    departure_str = f"{dep.day} {MONTHS[dep.month - 1]} {dep.year}"
                    footer_text = f"{arrival_str} – {departure_str}  |  Děčín"
                else:
                    footer_text = "Děčín"
                c.drawCentredString(x + badge_w / 2, y + 2.8 * mm, footer_text)

                c.setStrokeColor(colors.HexColor("#aaaaaa"))
                c.setLineWidth(0.3)
                c.setDash(2, 3)
                c.rect(x, y, badge_w, badge_h, fill=0, stroke=1)
                c.setDash()

                i += 1

        if i < len(badges):
            c.showPage()

    c.save()
    return response


class ReactView(APIView):
    serializer_class = ReactSerializer

    def get(self, request):
        detail = [
            {"name": detail.name, "detail": detail.detail}
            for detail in React.objects.all()
        ]
        return Response(detail)

    def post(self, request):
        serializer = ReactSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)


# Program: all days with timeline
class ProgramView(generics.ListAPIView):
    queryset = ConferenceDay.objects.all().order_by("date")
    serializer_class = ConferenceDaySerializer


# Participants
class ParticipantListView(generics.ListCreateAPIView):
    queryset = Participant.objects.all().order_by("name")
    serializer_class = ParticipantSerializer


class ParticipantDetailView(generics.RetrieveAPIView):
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer


# Abstracts
class AbstractListView(generics.ListCreateAPIView):
    queryset = Abstract.objects.all().order_by("title")
    serializer_class = AbstractSerializer


class AbstractDetailView(generics.RetrieveAPIView):
    queryset = Abstract.objects.all()
    serializer_class = AbstractSerializer


# Talks (optional endpoints)
class TalkListView(generics.ListAPIView):
    queryset = Talk.objects.all().order_by("day", "start_time")
    serializer_class = TalkSerializer


class TalkDetailView(generics.RetrieveAPIView):
    queryset = Talk.objects.all()
    serializer_class = TalkSerializer


class OrganizerListAPIView(generics.ListCreateAPIView):
    queryset = Organizer.objects.all()
    serializer_class = OrganizerSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        return [IsAdminUser()]

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        return [JWTAuthentication()]


class OrganizingCommitteeListAPIView(generics.ListCreateAPIView):
    queryset = OrganizingCommittee.objects.all()
    serializer_class = OrganizingCommitteeSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        return [IsAdminUser()]

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        return [JWTAuthentication()]


class OrganizerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Organizer.objects.all()
    serializer_class = OrganizerSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class OrganizingCommitteeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OrganizingCommittee.objects.all()
    serializer_class = OrganizingCommitteeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


# Admin Panel - JWT
class AdminPanelView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            {"message": "Welcome to admin panel", "user": request.user.username}
        )


class SubmissionCreateView(generics.CreateAPIView):
    queryset = ParticipantSubmission.objects.all()
    serializer_class = ParticipantSubmissionSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class SubmissionListView(generics.ListAPIView):
    queryset = ParticipantSubmission.objects.all()
    serializer_class = ParticipantSubmissionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            return ParticipantSubmission.objects.filter(status=status_filter)
        return ParticipantSubmission.objects.all()


class SubmissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ParticipantSubmission.objects.all()
    serializer_class = ParticipantSubmissionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


# Admin: get unscheduled talks (talks without time/day)
class UnscheduledTalksView(generics.ListAPIView):
    serializer_class = TalkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        # Talks без времени или дня
        return Talk.objects.filter(is_scheduled=False).select_related(
            "participant", "abstract"
        )


# Admin: update talk schedule
class TalkScheduleUpdateView(generics.UpdateAPIView):
    queryset = Talk.objects.all()
    serializer_class = TalkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    http_method_names = ["patch"]

    def patch(self, request, *args, **kwargs):
        talk = self.get_object()

        serializer = self.get_serializer(talk, data=request.data, partial=True)
        if serializer.is_valid():
            updated_talk = serializer.save()

            if updated_talk.day and updated_talk.start_time and updated_talk.end_time:
                updated_talk.is_scheduled = True
            else:
                updated_talk.is_scheduled = False

            updated_talk.save()

            return Response(self.get_serializer(updated_talk).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Admin: publish submission
@api_view(["POST"])
def publish_submission(request, pk):
    if not request.user.is_staff:
        return Response({"error": "Admin only"}, status=403)

    try:
        submission = ParticipantSubmission.objects.get(pk=pk)
    except ParticipantSubmission.DoesNotExist:
        return Response({"error": "Submission not found"}, status=404)

    if submission.status == "approved":
        return Response(
            {
                "message": "Already published",
                "participant_id": submission.published_participant.id
                if submission.published_participant
                else None,
                "abstract_id": submission.published_abstract.id
                if submission.published_abstract
                else None,
            },
            status=200,
        )

    try:
        participant, abstract, talk = submission.publish()

        return Response(
            {
                "message": "Published successfully",
                "participant_id": participant.id,
                "abstract_id": abstract.id if abstract else None,
                "participant_name": participant.name,
                "abstract_title": abstract.title if abstract else None,
                "talk_id": talk.id if talk else None,
                "talk_created": talk is not None,
            },
            status=200,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()  # Для отладки
        return Response({"error": f"Failed to publish: {str(e)}"}, status=500)


class UnscheduledTalkDeleteView(generics.DestroyAPIView):
    queryset = Talk.objects.all()
    serializer_class = TalkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        talk = self.get_object()

        if talk.talk_type == "break":
            talk.delete()
            return Response(
                {"message": "Break deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )

        if talk.is_scheduled:
            return Response(
                {"error": "Cannot delete a scheduled talk from here"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        talk.delete()
        return Response(
            {"message": "Talk deleted successfully"}, status=status.HTTP_204_NO_CONTENT
        )


class ConferenceDayDeleteView(generics.DestroyAPIView):
    queryset = ConferenceDay.objects.all()
    serializer_class = ConferenceDaySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        day = self.get_object()
        day.delete()
        return Response(
            {"message": "Day deleted successfully"}, status=status.HTTP_200_OK
        )


# Admin: create a break/event in schedule
class ScheduleBreakCreateView(generics.CreateAPIView):
    queryset = Talk.objects.all()
    serializer_class = TalkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        day_id = request.data.get("day")
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")
        title = request.data.get("title", "Break")
        talk_type = request.data.get("talk_type", "break")

        if not day_id or not start_time or not end_time:
            return Response(
                {"error": "day, start_time and end_time are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        talk = Talk.objects.create(
            title=title,
            talk_type=talk_type,
            day_id=day_id,
            start_time=start_time,
            end_time=end_time,
            is_scheduled=True,
        )

        serializer = self.get_serializer(talk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# Admin: create session
class SessionCreateView(generics.CreateAPIView):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        day_id = request.data.get("day")
        chair = request.data.get("chair", "")

        if not day_id:
            return Response(
                {"error": "day is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        session = Session.objects.create(
            day_id=day_id,
            chair=chair,
        )

        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SessionListView(generics.ListAPIView):
    serializer_class = SessionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        day_id = self.request.query_params.get("day", None)
        if day_id:
            return Session.objects.filter(day_id=day_id)
        return Session.objects.all()


class ConferenceDayCreateView(generics.CreateAPIView):
    queryset = ConferenceDay.objects.all()
    serializer_class = ConferenceDaySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


class SessionUpdateTimeView(generics.UpdateAPIView):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    http_method_names = ["patch"]


class HikingRouteListView(generics.ListAPIView):
    queryset = HikingRoute.objects.all()
    serializer_class = HikingRouteSerializer


class HikingRouteEditView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = HikingRouteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def patch(self, request):
        route_id = request.data.get("id")
        if not route_id:
            return Response({"detail": "Route id is required."}, status=400)

        try:
            route = HikingRoute.objects.get(pk=route_id)
        except HikingRoute.DoesNotExist:
            return Response({"detail": "Route not found."}, status=404)

        serializer = HikingRouteSerializer(route, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request):
        route_id = request.data.get("id")
        if not route_id:
            return Response({"detail": "Route id is required."}, status=400)

        try:
            route = HikingRoute.objects.get(pk=route_id)
        except HikingRoute.DoesNotExist:
            return Response({"detail": "Route not found."}, status=404)

        route.delete()
        return Response(status=204)


class HikingStopEditView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = HikingStopSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        stop = HikingStop.objects.get(pk=pk)
        serializer = HikingStopSerializer(stop, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        HikingStop.objects.get(pk=pk).delete()
        return Response(status=204)


class ConferenceInfoView(APIView):
    def get(self, request):
        obj, _ = ConferenceInfo.objects.get_or_create(id=1)
        return Response(ConferenceInfoSerializer(obj).data)


class ConferenceInfoEditView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser]

    def patch(self, request):
        obj, _ = ConferenceInfo.objects.get_or_create(id=1)
        serializer = ConferenceInfoSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_session(request, pk):
    try:
        session = Session.objects.get(pk=pk)
        session.talks.all().update(session=None)
        session.delete()
        return Response(status=204)
    except Session.DoesNotExist:
        return Response({"error": "Not found"}, status=404)


@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def update_session(request, pk):
    try:
        session = Session.objects.get(pk=pk)
        chair = request.data.get("chair")
        if chair is not None:
            session.chair = chair
            session.save()
        return Response({"id": session.id, "chair": session.chair})
    except Session.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
