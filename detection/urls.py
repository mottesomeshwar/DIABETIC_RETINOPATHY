"""
================================================================================
  FILE: detection/urls.py
  PURPOSE: URL patterns specific to the 'detection' app.
  Maps URL strings to view functions.

  Pattern syntax:
    path('url/', view_function, name='name')
    - 'url/': The URL pattern to match
    - view_function: The function in views.py to call
    - name='name': A unique name so templates can use {% url 'name' %}

  <int:id>: URL parameter that captures an integer and passes it to the view.
================================================================================
"""

from django.urls import path
from . import views   # Import our views module

urlpatterns = [
    # ------------------------------------------------------------------
    # PUBLIC PAGES (no login required)
    # ------------------------------------------------------------------

    # Landing page: http://127.0.0.1:8000/
    path('', views.home, name='home'),

    # Registration: http://127.0.0.1:8000/register/
    path('register/', views.register, name='register'),

    # Login: http://127.0.0.1:8000/login/
    path('login/', views.login_view, name='login'),

    # Logout: http://127.0.0.1:8000/logout/
    path('logout/', views.logout_view, name='logout'),

    # ------------------------------------------------------------------
    # PROTECTED PAGES (login required — handled by @login_required in views)
    # ------------------------------------------------------------------

    # Dashboard: http://127.0.0.1:8000/dashboard/
    path('dashboard/', views.dashboard, name='dashboard'),

    # ------------------------------------------------------------------
    # PATIENT MANAGEMENT
    # ------------------------------------------------------------------

    # Patient list: http://127.0.0.1:8000/patients/
    path('patients/', views.patient_list, name='patient_list'),

    # Add patient: http://127.0.0.1:8000/patients/add/
    path('patients/add/', views.add_patient, name='add_patient'),

    # Patient detail: http://127.0.0.1:8000/patients/42/
    # <int:patient_id> captures the integer from the URL and passes to view
    path('patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),

    # Edit patient: http://127.0.0.1:8000/patients/42/edit/
    path('patients/<int:patient_id>/edit/', views.edit_patient, name='edit_patient'),

    # ------------------------------------------------------------------
    # AI ANALYSIS
    # ------------------------------------------------------------------

    # Upload & analyze: http://127.0.0.1:8000/analyze/
    path('analyze/', views.analyze, name='analyze'),

    # Analysis result: http://127.0.0.1:8000/results/15/
    path('results/<int:result_id>/', views.result_detail, name='result_detail'),

    # ------------------------------------------------------------------
    # HISTORY & PROFILE
    # ------------------------------------------------------------------

    # Full analysis history: http://127.0.0.1:8000/history/
    path('history/', views.history, name='history'),

    # Doctor profile: http://127.0.0.1:8000/profile/
    path('profile/', views.profile, name='profile'),
]
