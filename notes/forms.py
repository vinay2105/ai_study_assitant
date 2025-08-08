from django import forms
from .models import Note

class NoteUploadForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'file', 'preference']
        widgets = {
            'preference': forms.TextInput(attrs={
                'placeholder': 'e.g. short, detailed, easy to remember'
            })
        }