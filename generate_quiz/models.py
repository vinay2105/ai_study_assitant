import uuid
from django.db import models
from django.conf import settings

class Quiz(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_quizzes"
    )
    title = models.CharField(max_length=255)  # Quiz title
    description = models.TextField(blank=True)  # Optional description
    difficulty = models.IntegerField(
        choices=[
            (1, 'Easy'),
            (2, 'Medium'),
            (3, 'Hard'),
            (4, 'Very Hard'),
            (5, 'Expert')
        ]
    )
    duration = models.IntegerField(help_text="Duration in minutes")
    topic_focus = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional: Focus on specific topics"
    )
    room_code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Indicates if the quiz is currently active"
    )

    def __str__(self):
        return f"{self.title} ({self.room_code})"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1)

    def __str__(self):
        return self.text


class Participant(models.Model):
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="generated_quiz_participations"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    joined_at = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(default=0)
    has_started = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} in {self.quiz.room_code}"


class QuizResult(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="results")
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    score = models.IntegerField()
    time_taken = models.DurationField(null=True, blank=True)
    rank = models.IntegerField(default=0)

    class Meta:
        ordering = ["rank"]

    def __str__(self):
        return f"{self.participant.name} - {self.score}"

