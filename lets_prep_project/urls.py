from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from quiz import views as quiz_views

print(">>> LOADING LETS_PREP_PROJECT.URLS <<<")

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', quiz_views.signup, name='signup'),

    # App pages
    path('', quiz_views.home, name='home'),
    path('dashboard/', quiz_views.dashboard, name='dashboard'),
    path('new-quiz/', quiz_views.new_quiz, name='new_quiz'),
    path('quiz/<int:session_id>/', quiz_views.quiz_detail, name='quiz_detail'),
    path('history/', quiz_views.history, name='history'),
    path('quiz/<int:session_id>/pdf/', quiz_views.export_quiz_pdf, name='export_quiz_pdf'),
    path('profile/', quiz_views.profile, name='profile'),
    path('session/<int:session_id>/delete/', quiz_views.delete_session, name='delete_session'),
    path('session/<int:session_id>/rename/', quiz_views.rename_session, name='rename_session'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)