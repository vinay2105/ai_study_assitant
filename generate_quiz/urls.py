from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.upload_notes, name="generate_quiz_create"),
    path("join/", views.join_quiz, name="generate_quiz_join"),
    path("dashboard/<str:room_code>/", views.quiz_dashboard, name="quiz_dashboard"),
    path("start/<str:room_code>/", views.start_quiz, name="start_quiz"),
    path("quiz/<str:room_code>/", views.quiz_page, name="quiz_page"),
    path("results/<str:room_code>/", views.quiz_results, name="quiz_results"),
    path("results/<str:room_code>/pdf/", views.results_pdf, name="quiz_results_pdf"),
    path("quiz/<str:room_code>/status/", views.quiz_lobby_status, name="quiz_lobby_status"),
    path("quiz/<str:room_code>/leave/", views.leave_quiz, name="leave_quiz"),
    path("submit-quiz/<str:room_code>/", views.submit_quiz, name="submit_quiz"),
    path("results/<str:room_code>/data/", views.quiz_results_data, name="quiz_results_data"),


]

