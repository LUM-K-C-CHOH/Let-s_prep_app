from django.db import models
from django.contrib.auth.models import User


class UploadedFile(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )
    file = models.FileField(upload_to='uploads/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    text_excerpt = models.TextField(blank=True)

    def __str__(self):
        return f"{self.original_name} ({self.owner.username})"


class QuizSession(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('flashcard', 'Flashcards'),
        ('fill_blank', 'Fill in the Blanks'),
        ('short_answer', 'Short Answer'),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quiz_sessions'
    )
    source_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES
    )
    num_questions = models.PositiveIntegerField(default=10)

    def __str__(self):
        return f"{self.title} ({self.owner.username})"


class Question(models.Model):
    session = models.ForeignKey(
        QuizSession,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_type = models.CharField(max_length=20)
    prompt = models.TextField()

    option_a = models.CharField(max_length=255, blank=True)
    option_b = models.CharField(max_length=255, blank=True)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)
    correct_option = models.CharField(max_length=1, blank=True)

    answer_text = models.TextField(blank=True)
    explanation = models.TextField(blank=True)

    def __str__(self):
        return f"Q for {self.session.title}"