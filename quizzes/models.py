from django.db import models
from django.conf import settings

class Quiz(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quizzes')
    created_at = models.DateTimeField(auto_now_add=True)
    notes_title = models.CharField(max_length=255, blank=True)  # Optional
    total_questions = models.PositiveIntegerField(default=0)
    score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Quiz {self.id} by {self.user.username} - Score: {self.score}/{self.total_questions}"

