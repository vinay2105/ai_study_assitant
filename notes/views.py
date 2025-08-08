import os, uuid, fitz
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import google.generativeai as genai

from .forms import NoteUploadForm
from .rag_utils import store_notes_as_vectors, ask_question_with_rag

# Load all Gemini API keys
GEMINI_KEYS = [
    os.getenv("GOOGLE_API_KEY_1"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
    os.getenv("GOOGLE_API_KEY_5"),
    os.getenv("GOOGLE_API_KEY_6"),
    os.getenv("GOOGLE_API_KEY_7"),
]

def get_genai_model():
    last_exc = None
    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            _ = model.count_tokens("test")
            return model
        except Exception as e:
            last_exc = e
    raise RuntimeError(f"⚠️ All Gemini keys failed: {last_exc}")

@login_required
def upload_notes(request):
    return render(request, 'upload_notes.html', {'form': NoteUploadForm()})

@login_required
def generated_notes_view(request):
    if request.method != 'POST':
        return redirect('upload_notes')

    form = NoteUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Invalid form submission.")
        return redirect('upload_notes')

    # — rate-limit can be added here —

    # Save file temporarily
    f = form.cleaned_data['file']
    pref = form.cleaned_data['preference'].strip()
    name = f.name.lower()
    tmp = f"tmp_{uuid.uuid4().hex}_{name}"
    path = default_storage.save(tmp, ContentFile(f.read()))
    is_img = name.endswith(('.png','.jpg','jpeg','gif'))
    url = default_storage.url(path) if is_img else None

    # Extract text
    text = ""
    try:
        with default_storage.open(path, 'rb') as fh:
            data = fh.read()
        if name.endswith('.pdf'):
            doc = fitz.open(stream=data, filetype="pdf")
            text = "\n".join(p.get_text() for p in doc)
        else:
            text = data.decode('utf-8', errors='ignore')
    except Exception as e:
        messages.error(request, f"Extraction error: {e}")
    finally:
        default_storage.delete(path)

    if not text.strip():
        notes = "⚠️ Could not extract any text."
    else:
        snippet = text[:100000]
        prompt = f"""
You are an AI Study Assistant. Generate HTML-formatted notes.

Preference: {pref}

Content:
{snippet}

Return only clean HTML (<h2>/<p>/<ul><li>…), no fences.
"""
        try:
            model = get_genai_model()
            resp = model.generate_content(prompt)
            notes = (resp.text or "").replace("```html", "").replace("```", "").strip()
            request.session['generated_notes'] = notes

            # Store vectors in /tmp path for current user ID
            store_notes_as_vectors(notes, str(request.user.id))

        except Exception as e:
            notes = f"⚠️ Gemini API Error: {e}"

    return render(request, 'generated_notes.html', {
        'generated_notes': notes,
        'file_url': url,
        'file_is_image': is_img,
    })

@login_required
def ask_doubt_view(request):
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        if not question:
            return JsonResponse({'answer': "❌ Please ask a valid question."})
        try:
            answer = ask_question_with_rag(str(request.user.id), question)
        except Exception as e:
            answer = f"⚠️ RAG Error: {e}"
        return JsonResponse({'answer': answer})
    
    # GET request → render chat interface
    return render(request, 'ask_doubt.html')





























