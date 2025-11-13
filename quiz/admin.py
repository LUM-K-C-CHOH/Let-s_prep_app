from django.contrib import admin
from .models import UploadedFile, QuizSession, Question

admin.site.register(UploadedFile)
admin.site.register(QuizSession)
admin.site.register(Question)