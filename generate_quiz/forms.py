from django import forms
from .models import Quiz, Participant, Question, QuizResult

class QuizCreationForm(forms.ModelForm):
    # Optional topic focus (UI placeholder only)
    topic_focus = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Optional: Focus on specific topics'})
    )
    num_questions = forms.IntegerField(
        required=False,
        min_value=5, max_value=100,
        initial=10,
        help_text="How many questions should the AI generate?"
    )

    class Meta:
        model = Quiz
        fields = ['title', 'difficulty', 'duration', 'topic_focus', 'num_questions']
        # no custom save() here — room_code is set in the view

class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['name']

    # You can keep this helper if you plan to use the form for joins
    def __init__(self, *args, **kwargs):
        self.quiz = kwargs.pop('quiz', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.quiz:
            instance.quiz = self.quiz
        if commit:
            instance.save()
        return instance

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option']

class QuizResultForm(forms.ModelForm):
    class Meta:
        model = QuizResult
        fields = ['score', 'time_taken', 'rank']

