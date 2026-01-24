import json
import os
import random
from google import genai
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

API_KEYS = [k for k in API_KEYS if k]

def get_gemini_client():
    if not API_KEYS:
        raise ValueError("No Gemini API keys configured.")
    api_key = random.choice(API_KEYS)
    return genai.Client(api_key=api_key)

def generate_quiz(request):
    notes = request.session.get("generated_notes", "")
    if not notes:
        return redirect("upload_notes")

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
        client = get_gemini_client()

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )

        raw_output = response.text.strip()

        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`").replace("json", "").strip()

        questions = json.loads(raw_output)
        request.session["quiz_questions"] = questions

        return render(request, "quiz.html", {"questions": questions})

    except Exception as e:
        return render(request, "quiz.html", {
            "questions": [],
            "error": f"Quiz generation failed: {e}"
        })

@csrf_exempt
def submit_quiz(request):
    questions = request.session.get("quiz_questions", [])
    if not questions:
        return redirect("generate_quiz")

    score = 0
    results = []

    for idx, q in enumerate(questions):
        user_answer = request.POST.get(f"q{idx}")
        correct = (
            user_answer
            and user_answer.strip().lower() == q["answer"].strip().lower()
        )
        if correct:
            score += 1

        results.append({
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["answer"],
            "user_answer": user_answer or None,
        })

    return render(request, "quiz_result.html", {
        "score": score,
        "total": len(questions),
        "results": results
    })



