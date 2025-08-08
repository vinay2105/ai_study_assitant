from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_notes, name='upload_notes'),   
    path('generated/', views.generated_notes_view, name='generated_notes'),
    path('ask-doubt/', views.ask_doubt_view, name='ask_doubt'),

]