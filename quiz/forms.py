from django import forms
from .models import QuizSession


class UploadQuizForm(forms.Form):
    title = forms.CharField(max_length=255, label="Quiz Title")
    file = forms.FileField(label="Upload a study file")
    question_type = forms.ChoiceField(
        choices=QuizSession.QUESTION_TYPE_CHOICES,
        label="Question Format"
    )
    num_questions = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=10,
        label="Number of Questions"
    )