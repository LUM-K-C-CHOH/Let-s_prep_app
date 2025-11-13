
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .forms import UploadQuizForm
from .models import UploadedFile, QuizSession, Question
from .utils.file_parsers import extract_text_from_file
from .utils.question_generator import generate_questions

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def home(request):
    """Landing page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'quiz/home.html')


@login_required
def dashboard(request):
    """Show recent quiz sessions for the logged-in user."""
    recent_sessions = QuizSession.objects.filter(
        owner=request.user
    ).order_by('-created_at')[:5]
    return render(request, 'quiz/dashboard.html', {
        'recent_sessions': recent_sessions,
    })


@login_required
def new_quiz(request):
    """Upload a file and generate a new quiz."""
    if request.method == 'POST':
        form = UploadQuizForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data['title']
            uploaded_file = form.cleaned_data['file']
            question_type = form.cleaned_data['question_type']
            num_questions = form.cleaned_data['num_questions']

            # Save the uploaded file record
            uf = UploadedFile.objects.create(
                owner=request.user,
                file=uploaded_file,
                original_name=uploaded_file.name,
            )

            # Extract text from the file
            text = extract_text_from_file(uf.file)
            uf.text_excerpt = text[:1000]
            uf.save()

            # Generate questions (offline version)
            questions_data = generate_questions(text, question_type, num_questions)

            # Create QuizSession record
            session = QuizSession.objects.create(
                owner=request.user,
                source_file=uf,
                title=title,
                question_type=question_type,
                num_questions=len(questions_data),
            )

            # Save each question
            for q in questions_data:
                Question.objects.create(
                    session=session,
                    question_type=q.get('type', question_type),
                    prompt=q.get('prompt', ''),
                    option_a=q.get('option_a', ''),
                    option_b=q.get('option_b', ''),
                    option_c=q.get('option_c', ''),
                    option_d=q.get('option_d', ''),
                    correct_option=q.get('correct_option', ''),
                    answer_text=q.get('answer_text', ''),
                    explanation=q.get('explanation', ''),
                )

            return redirect('quiz_detail', session_id=session.id)
    else:
        form = UploadQuizForm()

    return render(request, 'quiz/new_quiz.html', {'form': form})


@login_required
def quiz_detail(request, session_id):
    """View a single quiz and its questions."""
    session = get_object_or_404(QuizSession, id=session_id, owner=request.user)
    questions = session.questions.all()
    return render(request, 'quiz/quiz_detail.html', {
        'session': session,
        'questions': questions,
    })


@login_required
def history(request):
    """Show the full history of quizzes for this user."""
    sessions = QuizSession.objects.filter(
        owner=request.user
    ).order_by('-created_at')
    return render(request, 'quiz/history.html', {
        'sessions': sessions,
    })


def signup(request):
    """User registration page."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def export_quiz_pdf(request, session_id):
    """Generate a simple PDF with all questions & answers for this quiz."""
    session = get_object_or_404(QuizSession, id=session_id, owner=request.user)
    questions = session.questions.all()

    # Create HTTP response with PDF headers
    response = HttpResponse(content_type='application/pdf')
    filename = f"lets_prep_{session.id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Create the PDF object, using the response as "file."
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"LET'S PREP — {session.title}")
    y -= 30

    p.setFont("Helvetica", 10)

    for i, q in enumerate(questions, start=1):
        lines = [
            f"{i}. ({q.question_type})",
        ]
        lines.extend(q.prompt.splitlines())
        if q.answer_text:
            lines.append(f"Answer: {q.answer_text}")
        if q.correct_option:
            lines.append(f"Correct option: {q.correct_option}")
        lines.append("")  # blank line

        for line in lines:
            if y < 60:  # new page
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 10)
            p.drawString(50, y, line[:110])
            y -= 14

    p.showPage()
    p.save()
    return response
