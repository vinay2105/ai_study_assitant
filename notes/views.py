import os, uuid, fitz, time, logging
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from google import genai

from .forms import NoteUploadForm
from .rag_utils import store_notes_as_vectors, ask_question_with_rag

# ------------------------------
# Logging
# ------------------------------
logger = logging.getLogger(__name__)

# ------------------------------
# Load all Gemini API keys
# ------------------------------
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

# ------------------------------
# Gemini client with key rotation + retry
# ------------------------------
def get_genai_client(retries=3, delay=2):
    last_exc = None

    for key in GEMINI_KEYS:
        for attempt in range(retries):
            try:
                client = genai.Client(api_key=key)

                # lightweight sanity call
                client.models.generate_content(
                    model="gemini-1.0-pro",
                    contents="ping"
                )

                return client

            except Exception as e:
                last_exc = e
                if "429" in str(e):
                    logger.warning(
                        f"Rate limit hit for key, retry {attempt + 1}/{retries}"
                    )
                    time.sleep(delay * (attempt + 1))
                else:
                    break

    raise RuntimeError(f"⚠️ All Gemini keys failed. Last error: {last_exc}")

# ------------------------------
# Upload Notes Page
# ------------------------------
@login_required
def upload_notes(request):
    return render(request, "upload_notes.html", {"form": NoteUploadForm()})

# ------------------------------
# Generate Notes
# ------------------------------
@login_required
def generated_notes_view(request):
    if request.method != "POST":
        return redirect("upload_notes")

    form = NoteUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Invalid form submission.")
        return redirect("upload_notes")

    f = form.cleaned_data["file"]
    pref = form.cleaned_data["preference"].strip()
    name = f.name.lower()
    tmp = f"tmp_{uuid.uuid4().hex}_{name}"
    path = default_storage.save(tmp, ContentFile(f.read()))
    is_img = name.endswith((".png", ".jpg", ".jpeg", ".gif"))
    url = default_storage.url(path) if is_img else None

    # ------------------------------
    # Extract text from file
    # ------------------------------
    text = ""
    try:
        with default_storage.open(path, "rb") as fh:
            data = fh.read()

        if name.endswith(".pdf"):
            doc = fitz.open(stream=data, filetype="pdf")
            text = "\n".join(p.get_text() for p in doc)
        else:
            text = data.decode("utf-8", errors="ignore")

    except Exception as e:
        messages.error(request, f"⚠️ Extraction error: {e}")

    finally:
        default_storage.delete(path)

    # ------------------------------
    # Generate notes using Gemini
    # ------------------------------
    if not text.strip():
        notes = "⚠️ Could not extract any text."
    else:
        snippet = text[:100000]

        prompt = f"""
You are an AI Study Assistant. Generate HTML-formatted notes.

Preference: {pref}

Content:
{snippet}

Return only clean HTML (<h2>, <p>, <ul><li>…), no fences.
"""

        try:
            client = get_genai_client()

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
            )

            notes = (response.text or "").replace("```html", "").replace("```", "").strip()

            request.session["generated_notes"] = notes

            store_notes_as_vectors(text, str(request.user.id))

        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            notes = f"⚠️ Gemini API Error: {e}"

    return render(
        request,
        "generated_notes.html",
        {
            "generated_notes": notes,
            "file_url": url,
            "file_is_image": is_img,
        },
    )

# ------------------------------
# Ask Doubt with RAG
# ------------------------------
@login_required
def ask_doubt_view(request):
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        if not question:
            return JsonResponse({"answer": "❌ Please ask a valid question."})

        try:
            answer = ask_question_with_rag(str(request.user.id), question)
        except Exception as e:
            logger.error(f"RAG Error: {e}")
            answer = f"⚠️ RAG Error: {e}"

        return JsonResponse({"answer": answer})

    return render(request, "ask_doubt.html")































