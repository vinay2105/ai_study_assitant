import json
import os
import random
import google.generativeai as genai
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

# --- Load multiple API keys from .env ---
API_KEYS = [
    os.getenv("GOOGLE_API_KEY_1"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
    os.getenv("GOOGLE_API_KEY_5"),
    os.getenv("GOOGLE_API_KEY_6"),
    os.getenv("GOOGLE_API_KEY_7"),
]

# Remove None or empty keys
API_KEYS = [k for k in API_KEYS if k]

def get_gemini_model():
    """Pick a random API key to distribute load and create a model."""
    if not API_KEYS:
        raise ValueError("No Gemini API keys configured.")
    api_key = random.choice(API_KEYS)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def generate_quiz(request):
    """Generate a quiz from the session notes using Gemini."""
    notes = request.session.get("generated_notes", "")
    if not notes:
        return redirect('upload_notes')  # Redirect if no notes exist

    prompt = f"""
You are an AI quiz generator.
Generate 10 multiple-choice questions (MCQs) from the following HTML study notes.
Return output strictly in valid JSON list format like this:
[
  {{
    "question": "Sample question?",
    "options": ["Option1", "Option2", "Option3", "Option4"],
    "answer": "Correct option"
  }}
]

Study Notes:
{notes}
    """

    try:
        model = get_gemini_model()
        response = model.generate_content(prompt)
        raw_output = response.text.strip()

        # Clean accidental markdown fences
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`").replace("json", "").strip()

        # Ensure valid JSON
        questions = json.loads(raw_output)

        # Store questions in session
        request.session["quiz_questions"] = questions

        return render(request, "quiz.html", {"questions": questions})

    except Exception as e:
        return render(request, "quiz.html", {
            "questions": [],
            "error": f"Quiz generation failed: {e}"
        })


@csrf_exempt
def submit_quiz(request):
    """Evaluate submitted answers and show result with all options."""
    questions = request.session.get("quiz_questions", [])
    if not questions:
        return redirect('generate_quiz')

    score = 0
    results = []

    for idx, q in enumerate(questions):
        user_answer = request.POST.get(f"q{idx}")
        correct = user_answer and user_answer.strip().lower() == q["answer"].strip().lower()
        if correct:
            score += 1

        results.append({
            "question": q["question"],
            "options": q["options"],          # keep all original options
            "correct_answer": q["answer"],
            "user_answer": user_answer or None,
        })

    return render(request, "quiz_result.html", {
        "score": score,
        "total": len(questions),
        "results": results
    })


