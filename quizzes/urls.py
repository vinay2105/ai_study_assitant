from django.urls import path
from . import views

urlpatterns = [
    path('generate-quiz/', views.generate_quiz, name='generate_quiz'),
    path('submit-quiz/', views.submit_quiz, name='submit_quiz'),  # optional for scoring
]
