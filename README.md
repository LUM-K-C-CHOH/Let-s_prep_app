

🎓 LET’S PREP — Intelligent Study Material Generator

A Django Web Application for Automated Study Question Creation

LET’S PREP is a full-stack web platform that transforms uploaded study materials into interactive learning resources.
Users can upload PDFs, Word documents, PowerPoints, images, or plain text files, and LET’S PREP automatically extracts content and generates structured study questions such as:
	•	Flashcards
	•	Multiple-Choice Questions (MCQs)
	•	Fill-in-the-Blank items

The application includes user authentication, persistent quiz history, interactive quiz navigation, and a clean dashboard for managing all generated study sessions.



🌟 Key Features

📤 Upload Anything

Supports multiple file formats:
	•	.pdf — parsed with PyPDF2
	•	.docx — parsed with python-docx
	•	.pptx — parsed with python-pptx
	•	.txt
	•	.jpg, .png (OCR via pytesseract + Pillow)

🧠 Automatic Study Question Generation

LET’S PREP intelligently extracts meaningful text from uploaded materials and generates:
	•	Flashcards (Term → Key Idea)
	•	MCQs (randomized options, scoring, explanations)
	•	Fill-in-the-Blank items

📚 Quiz Sessions & History

Every quiz session is:
	•	Saved to the user’s profile
	•	Viewable later in the History page
	•	Associated with the uploaded file for traceability

🎮 Interactive Quiz Experience
	•	Previous/Next navigation
	•	Option highlighting
	•	Automatic scoring
	•	Clean, readable interface

📄 PDF Export

Users can download quizzes as formatted PDFs for offline studying.

🔐 User Authentication

Includes:
	•	Sign-up
	•	Login
	•	Logout
	•	User-specific dashboards

⸻

🧰 Tech Stack

Backend
	•	Python 3
	•	Django 4.2
	•	SQLite (default database)

Frontend
	•	HTML (Django Templates)
	•	CSS (custom styling)
	•	Responsive, clean UI design

File Processing Libraries
	•	PyPDF2
	•	python-docx
	•	python-pptx
	•	pytesseract
	•	Pillow



🚀 Getting Started

1. Clone the Repository

git clone https://github.com/<your-username>/lets_prep.git
cd lets_prep

2. Create and Activate Virtual Environment

python3 -m venv venv
source venv/bin/activate

3. Install Dependencies

pip install -r requirements.txt

4. Apply Database Migrations

python manage.py migrate

5. Run the Development Server

python manage.py runserver

Now navigate to:

http://127.0.0.1:8000/


⸻

🔑 Authentication Routes
	•	/signup/ — Register new account
	•	/accounts/login/ — Login
	•	/dashboard/ — User dashboard
	•	/history/ — Quiz history

⸻

📝 Notes(Finally did this)
	•	This version uses offline logic for question generation (no API required).
	•	To enable AI-enhanced conceptual question generation, integrate an AI model into question_generator.py.
	•	SQLite is sufficient for development; switch to PostgreSQL for production deployments.

⸻

🧩 Future Enhancements(Completed)
	•	AI-powered study questions 
	•	Tag-based question grouping
	•	Flashcard flip animations
	•	Dark mode UI
	•	Export to Quizlet
	•	Mobile-optimized interface
	•	Collaborative study sessions

⸻
👩‍💻 Author

Lum Kelly Chelsie Choh
Janelle Yankey
Edward Sie
Developers • Computer Science @ Howard University


	•	A version tailored for your portfolio website

Just tell me!
