from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_POST
from django.http import HttpResponse

from .forms import UploadQuizForm
from .models import UploadedFile, QuizSession, Question
from .utils.file_parsers import extract_text_from_file
from .utils.question_generator import generate_questions

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def home(request):
    """Landing page."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "quiz/home.html")


@login_required
def dashboard(request):
    """Main dashboard with streak + recent sessions."""
    sessions_qs = QuizSession.objects.filter(
        owner=request.user
    ).order_by("-created_at")
    recent_sessions = sessions_qs[:5]

    total_quizzes = sessions_qs.count()
    total_questions = Question.objects.filter(
        session__owner=request.user
    ).count()

    # Simple XP system: 10 XP per question
    xp = total_questions * 10
    level = xp // 100 + 1  # every 100 XP → new level
    next_level_xp = level * 100
    xp_progress = int((xp / next_level_xp) * 100) if next_level_xp else 0

    context = {
        "recent_sessions": recent_sessions,
        "total_quizzes": total_quizzes,
        "total_questions": total_questions,
        "xp": xp,
        "level": level,
        "xp_progress": xp_progress,
        "next_level_xp": next_level_xp,
    }
    return render(request, "quiz/dashboard.html", context)


@login_required
def new_quiz(request):
    """
    Upload a file and generate a new quiz.

    IMPORTANT:
    - Every question created for this session is forced to use the
      user-selected `question_type` from the form, so choosing
      "Multiple Choice" does NOT mix in flashcards / fill-in.
    """
    if request.method == "POST":
        form = UploadQuizForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data["title"]
            uploaded_file = form.cleaned_data["file"]
            selected_type = form.cleaned_data["question_type"]
            num_questions = form.cleaned_data["num_questions"]

            # 1) Save uploaded file record
            uf = UploadedFile.objects.create(
                owner=request.user,
                file=uploaded_file,
                original_name=uploaded_file.name,
            )

            # 2) Extract raw text from the file
            text = extract_text_from_file(uf.file)
            uf.text_excerpt = text[:1000]
            uf.save()

            # 3) Let the question generator (AI or simple) do its thing
            questions_data = generate_questions(
                text=text,
                question_type=selected_type,
                num_questions=num_questions,
            )

            # 4) Create a QuizSession
            session = QuizSession.objects.create(
                owner=request.user,
                source_file=uf,
                title=title,
                question_type=selected_type,
                num_questions=len(questions_data),
            )

            # 5) Save each question.
            #    Force `question_type` to the user's choice so sessions are consistent.
            for q in questions_data:
                Question.objects.create(
                    session=session,
                    question_type=selected_type,  # <-- enforce one type per session
                    prompt=q.get("prompt", ""),
                    option_a=q.get("option_a", ""),
                    option_b=q.get("option_b", ""),
                    option_c=q.get("option_c", ""),
                    option_d=q.get("option_d", ""),
                    correct_option=q.get("correct_option", ""),
                    answer_text=q.get("answer_text", ""),
                    explanation=q.get("explanation", ""),
                )

            return redirect("quiz_detail", session_id=session.id)
    else:
        form = UploadQuizForm()

    return render(request, "quiz/new_quiz.html", {"form": form})


@login_required
def quiz_detail(request, session_id):
    """View a single quiz + go through its questions."""
    session = get_object_or_404(QuizSession, id=session_id, owner=request.user)
    questions = session.questions.all()
    return render(
        request,
        "quiz/quiz_detail.html",
        {"session": session, "questions": questions},
    )


@login_required
def history(request):
    """
    Full history of quiz sessions for this user.
    Newest first.
    """
    sessions = QuizSession.objects.filter(
        owner=request.user
    ).order_by("-created_at")

    return render(request, "quiz/history.html", {"sessions": sessions})


@login_required
@require_POST
def delete_session(request, session_id):
    """Delete a single quiz session and all its questions."""
    session = get_object_or_404(QuizSession, id=session_id, owner=request.user)
    session.delete()
    return redirect("dashboard")


@login_required
def rename_session(request, session_id):
    """Rename a quiz session (from quiz detail page)."""
    session = get_object_or_404(QuizSession, id=session_id, owner=request.user)

    if request.method == "POST":
        new_title = request.POST.get("title", "").strip()
        if new_title:
            session.title = new_title
            session.save()
            return redirect("quiz_detail", session_id=session.id)

    return render(request, "quiz/rename_session.html", {"session": session})


def signup(request):
    """User registration page."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def export_quiz_pdf(request, session_id):
    """Generate a simple PDF with all questions & answers for this quiz."""
    session = get_object_or_404(QuizSession, id=session_id, owner=request.user)
    questions = session.questions.all()

    # Create HTTP response with PDF headers
    response = HttpResponse(content_type="application/pdf")
    filename = f"lets_prep_{session.id}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    # Create the PDF object, using the response as "file."
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"LET'S PREP — {session.title}")
    y -= 30

    p.setFont("Helvetica", 10)

    for i, q in enumerate(questions, start=1):
        lines = [f"{i}. ({q.question_type})"]
        lines.extend(q.prompt.splitlines())
        if q.answer_text:
            lines.append(f"Answer: {q.answer_text}")
        if q.correct_option:
            lines.append(f"Correct option: {q.correct_option}")
        lines.append("")

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


@login_required
def profile(request):
    """Simple stats page for the user."""
    sessions = QuizSession.objects.filter(owner=request.user)
    total = sessions.count()
    total_mcq = sessions.filter(question_type="mcq").count()
    total_flash = sessions.filter(question_type="flashcard").count()
    total_fill = sessions.filter(question_type="fill_blank").count()
    total_short = sessions.filter(question_type="short_answer").count()

    return render(
        request,
        "quiz/profile.html",
        {
            "total_sessions": total,
            "total_mcq": total_mcq,
            "total_flashcards": total_flash,
            "total_fill_blank": total_fill,
            "total_short_answer": total_short,
        },
    )