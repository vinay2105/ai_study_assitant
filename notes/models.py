from django.db import models
from django.conf import settings

class Note(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='notes/')
    preference = models.CharField(help_text='How you want your notes to be designed (example: detailed, short,etc.)')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title