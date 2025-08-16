import os
import json
import random
import fitz
import google.generativeai as genai
from datetime import timedelta, datetime
from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse, HttpResponse
from django.urls import reverse

from .models import Quiz, Question, Participant, QuizResult
from .forms import QuizCreationForm

# -----------------------------
# Gemini setup
# -----------------------------
GEMINI_KEYS = [
    os.getenv("GOOGLE_API_KEY_1"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
    os.getenv("GOOGLE_API_KEY_5"),
    os.getenv("GOOGLE_API_KEY_6"),
    os.getenv("GOOGLE_API_KEY_7"),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

def get_gemini_model():
    if not GEMINI_KEYS:
        raise RuntimeError("No Gemini API keys configured.")
    genai.configure(api_key=random.choice(GEMINI_KEYS))
    return genai.GenerativeModel("gemini-1.5-flash")

# -----------------------------
# Helpers
# -----------------------------
ABORT_TTL = 60 * 60 * 6  # 6 hours in cache

def _quiz_cache_keys(room_code: str):
    base = f"quiz:{room_code}"
    return {
        "start_at": f"{base}:start_at",
        "ends_at": f"{base}:ends_at",
        "aborted": f"{base}:aborted",
    }

def _generate_unique_room_code():
    for _ in range(50):
        code = "".join(str(random.randint(0, 9)) for _ in range(6))
        if not Quiz.objects.filter(room_code=code).exists():
            return code
    return "".join(str(random.randint(0, 9)) for _ in range(6))

def _extract_text_from_upload(upload):
    if not upload:
        return ""
    name = (upload.name or "").lower()
    if name.endswith(".pdf"):
        text = []
        with fitz.open(stream=upload.read(), filetype="pdf") as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text).strip()
    return upload.read().decode("utf-8", errors="ignore").strip()

def _build_quiz_prompt(notes_text, difficulty, duration_minutes, topic_focus, num_questions):
    return f"""
You are an expert exam-setter. Create a high-quality multiple-choice quiz from the given notes.

CONSTRAINTS:
- Difficulty level: {difficulty} (1 easiest, 5 hardest).
- Number of questions: {num_questions}.
- Total duration: {duration_minutes} minutes.
- Topic focus: {topic_focus or "None"}.

FORMAT (STRICT JSON):
[{{"question": "...", "options": ["A","B","C","D"], "answer_index": 0}}]

NOTES:
{notes_text}
""".strip()

def _safe_json_from_model_response(response_text):
    raw = (response_text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)

def _store_questions(quiz, items):
    Question.objects.filter(quiz=quiz).delete()
    objs = []
    for it in items:
        q = it.get("question", "").strip()
        opts = it.get("options", [])
        ans_idx = it.get("answer_index", None)
        if not (q and len(opts) == 4 and isinstance(ans_idx, int) and 0 <= ans_idx <= 3):
            continue
        objs.append(Question(
            quiz=quiz,
            text=q,
            option_a=str(opts[0]),
            option_b=str(opts[1]),
            option_c=str(opts[2]),
            option_d=str(opts[3]),
            correct_option=["A", "B", "C", "D"][ans_idx],
        ))
    Question.objects.bulk_create(objs)
    return len(objs)

def _parse_iso(dt_str):
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt

# -----------------------------
# API for real-time lobby
# -----------------------------
@login_required
def quiz_lobby_status(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    qs = quiz.generated_quiz_participations.order_by("joined_at").values("name", "joined_at", "user_id")
    participants = [
        {
            "name": p["name"],
            "joined_at": p["joined_at"].isoformat() if p["joined_at"] else None,
            "is_creator": (p["user_id"] == quiz.creator_id),
        }
        for p in qs
    ]
    keys = _quiz_cache_keys(room_code)
    started = bool(cache.get(keys["start_at"]))
    aborted = bool(cache.get(keys["aborted"])) or getattr(quiz, "status", "") == "aborted"

    return JsonResponse({
        "participants": participants,
        "quiz_started": started,
        "quiz_aborted": aborted,
        "quiz_url": request.build_absolute_uri(reverse("quiz_page", args=[room_code])),
        "redirect": request.build_absolute_uri(reverse("home")),
    })

@require_POST
@login_required
@transaction.atomic
def leave_quiz(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    keys = _quiz_cache_keys(room_code)
    redirect_url = reverse("home")

    participation = quiz.generated_quiz_participations.filter(user_id=request.user.id).first()
    is_creator = (request.user.id == quiz.creator_id)

    if not (participation or is_creator):
        return JsonResponse({"ok": False, "error": "not-in-room", "redirect": redirect_url}, status=400)

    if is_creator:
        cache.set(keys["aborted"], True, ABORT_TTL)
        if hasattr(quiz, "status"):
            quiz.status = "aborted"
            quiz.save(update_fields=["status"])
        quiz.generated_quiz_participations.all().delete()
        return JsonResponse({"ok": True, "aborted": True, "redirect": redirect_url})

    participation.delete()
    return JsonResponse({"ok": True, "aborted": False, "redirect": redirect_url})

# -----------------------------
# Views
# -----------------------------
@login_required
def upload_notes(request):
    if request.method == "POST":
        form = QuizCreationForm(request.POST)
        notes_file = request.FILES.get("notes_file")
        notes_text = _extract_text_from_upload(notes_file) or request.POST.get("notes_text", "").strip()

        if not notes_text:
            messages.error(request, "Please upload or paste notes.")
            return render(request, "generate_quiz_create.html", {"form": form})

        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.creator = request.user
            for _ in range(5):
                quiz.room_code = _generate_unique_room_code()
                try:
                    with transaction.atomic():
                        quiz.is_active = True
                        quiz.save()
                        break
                except IntegrityError:
                    continue
            else:
                messages.error(request, "Could not generate unique room code.")
                return render(request, "generate_quiz_create.html", {"form": form})

            # Use requested number of questions if provided and valid; otherwise fallback to heuristic
            duration = max(1, int(quiz.duration))
            try:
                requested = int(form.cleaned_data.get("num_questions") or 0)
            except (TypeError, ValueError):
                requested = 0
            num_questions = requested if 5 <= requested <= 100 else max(5, min(50, round(duration / 1.7)))

            try:
                model = get_gemini_model()
                prompt = _build_quiz_prompt(
                    notes_text,
                    quiz.difficulty,
                    duration,
                    quiz.topic_focus or "",
                    num_questions,
                )
                resp = model.generate_content(prompt)
                items = _safe_json_from_model_response(getattr(resp, "text", ""))
                if _store_questions(quiz, items) == 0:
                    quiz.delete()
                    messages.error(request, "AI returned no valid questions.")
                    return render(request, "generate_quiz_create.html", {"form": form})
            except Exception as e:
                quiz.delete()
                messages.error(request, f"Quiz generation failed: {e}")
                return render(request, "generate_quiz_create.html", {"form": form})

            if request.POST.get("creator_participates") == "on":
                Participant.objects.get_or_create(
                    quiz=quiz,
                    user=request.user,
                    defaults={"name": getattr(request.user, "username", "Creator")},
                )

            return redirect("quiz_dashboard", room_code=quiz.room_code)

        messages.error(request, "Please fix the errors.")
    else:
        form = QuizCreationForm()
    return render(request, "generate_quiz_create.html", {"form": form})


@login_required
def join_quiz(request):
    if request.method == "POST":
        room_code = (request.POST.get("room_code") or "").strip()
        name = (request.POST.get("name") or "").strip()
        quiz = Quiz.objects.filter(room_code=room_code, is_active=True).first()
        if not quiz:
            messages.error(request, "Invalid or inactive room code.")
            return redirect("generate_quiz_join")

        keys = _quiz_cache_keys(room_code)
        if cache.get(keys["aborted"]):
            messages.error(request, "This quiz was ended by the creator.")
            return redirect("generate_quiz_join")
        if cache.get(keys["start_at"]):
            messages.error(request, "Quiz has already started.")
            return redirect("generate_quiz_join")

        Participant.objects.get_or_create(
            quiz=quiz, user=request.user,
            defaults={"name": name or getattr(request.user, "username", "Participant")}
        )
        return redirect("quiz_dashboard", room_code=room_code)
    return render(request, "generate_quiz_join.html")

@login_required
def quiz_dashboard(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    participants_qs = quiz.generated_quiz_participations.select_related("user").order_by("joined_at")
    participants = list(participants_qs)
    user_is_creator = (quiz.creator_id == request.user.id)
    user_is_participant = user_is_creator or any(
        getattr(p, "user_id", None) == request.user.id for p in participants
    )

    return render(request, "generate_quiz_dashboard.html", {
        "quiz": quiz,
        "participants": participants,
        "is_creator": user_is_creator,
        "user_is_creator": user_is_creator,
        "user_is_participant": user_is_participant,
    })

@login_required
@require_POST
def start_quiz(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    if quiz.creator_id != request.user.id:
        return redirect("quiz_dashboard", room_code=room_code)

    keys = _quiz_cache_keys(room_code)
    now = timezone.now()
    ends = now + timedelta(minutes=max(1, quiz.duration))
    cache.set(keys["start_at"], now.isoformat(), timeout=quiz.duration * 120)
    cache.set(keys["ends_at"], ends.isoformat(), timeout=quiz.duration * 120)

    # If it’s an AJAX call, return JSON; otherwise do a normal redirect.
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or \
              "application/json" in (request.headers.get("accept") or "")
    if is_ajax:
        return JsonResponse({"quiz_started": True, "quiz_url": reverse("quiz_page", args=[room_code])})

    return redirect("quiz_page", room_code=room_code)


@login_required
def quiz_page(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    keys = _quiz_cache_keys(room_code)
    if cache.get(keys["aborted"]) or getattr(quiz, "status", "") == "aborted":
        return redirect("quiz_dashboard", room_code=room_code)

    start_iso = cache.get(keys["start_at"])
    ends_iso = cache.get(keys["ends_at"])
    if not (start_iso and ends_iso):
        return redirect("quiz_dashboard", room_code=room_code)

    start_at = _parse_iso(start_iso)
    ends_at = _parse_iso(ends_iso)
    if timezone.now() >= ends_at:
        quiz.is_active = False
        quiz.save(update_fields=["is_active"])
        return redirect("quiz_results", room_code=room_code)

    Participant.objects.get_or_create(
        quiz=quiz, user=request.user,
        defaults={"name": getattr(request.user, "username", "Participant")}
    )
    return render(request, "generate_quiz_quiz.html", {
        "quiz": quiz,
        "questions": quiz.questions.all(),
        "remaining_seconds": int((ends_at - timezone.now()).total_seconds())
    })

@login_required
@require_POST
def submit_quiz(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    participant = get_object_or_404(Participant, quiz=quiz, user=request.user)

    score = 0
    for q in quiz.questions.all():
        if request.POST.get(f"q_{q.id}") == q.correct_option:
            score += 1

    keys = _quiz_cache_keys(room_code)
    start_at = _parse_iso(cache.get(keys["start_at"]))
    ends_at = _parse_iso(cache.get(keys["ends_at"]))

    elapsed = timezone.now() - start_at if start_at else timedelta(0)
    if ends_at and timezone.now() > ends_at:
        elapsed = ends_at - (start_at or ends_at)

    participant.score = score
    participant.has_started = True
    participant.save()

    QuizResult.objects.update_or_create(
        quiz=quiz, participant=participant,
        defaults={"score": score, "time_taken": elapsed, "rank": 0}
    )
    return redirect("quiz_results", room_code=room_code)

@login_required
def quiz_results(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    results = list(QuizResult.objects.filter(quiz=quiz).select_related("participant"))
    results.sort(key=lambda r: (-int(r.score), r.time_taken or timedelta.max))

    current_rank = 0
    last_key = None
    to_update = []
    for idx, r in enumerate(results, start=1):
        key = (int(r.score), r.time_taken or timedelta.max)
        if key != last_key:
            current_rank = idx
            last_key = key
        if r.rank != current_rank:
            r.rank = current_rank
            to_update.append(r)
        r.is_me = (getattr(r.participant, "user_id", None) == request.user.id)
    if to_update:
        QuizResult.objects.bulk_update(to_update, ["rank"])

    if quiz.is_active:
        quiz.is_active = False
        quiz.save(update_fields=["is_active"])

    return render(request, "generate_quiz_results.html", {"quiz": quiz, "results": results})

# NEW: real-time results API
@login_required
def quiz_results_data(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    results = list(QuizResult.objects.filter(quiz=quiz).select_related("participant").order_by("rank"))
    data = []
    for r in results:
        data.append({
            "rank": r.rank,
            "name": r.participant.name,
            "score": r.score,
            "time_taken": str(r.time_taken) if r.time_taken else "—",
            "is_me": (getattr(r.participant, "user_id", None) == request.user.id),
        })
    return JsonResponse({"results": data})

# -----------------------------
# Results PDF
# -----------------------------
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

@login_required
def results_pdf(request, room_code):
    quiz = get_object_or_404(Quiz, room_code=room_code)
    results = quiz.results.order_by("rank")

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="quiz_{room_code}_results.pdf"'

    p = canvas.Canvas(resp, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(72, 760, f"Results — {quiz.title} ({room_code})")

    y = 730
    p.setFont("Helvetica", 12)
    for r in results:
        line = f"{r.rank}. {r.participant.name}  —  {r.score} pts"
        p.drawString(72, y, line)
        y -= 18
        if y < 72:
            p.showPage()
            p.setFont("Helvetica", 12)
            y = 760

    p.showPage()
    p.save()
    return resp




