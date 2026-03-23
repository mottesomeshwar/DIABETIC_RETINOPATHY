"""
================================================================================
  FILE: detection/views.py
  PURPOSE: VIEW FUNCTIONS — the controllers of our app.
  Each function handles one URL endpoint:
    - Receives an HTTP request
    - Does logic (query DB, call ML model, etc.)
    - Returns an HTTP response (usually renders an HTML template)

  Flow: URL → urls.py → view function → template → HTML response to browser
================================================================================
"""

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required  # Requires login to access view
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages                         # Flash messages
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.utils import timezone

from .models import DoctorProfile, Patient, DetectionResult
from .forms import DoctorRegistrationForm, PatientForm, ImageUploadForm
from .ml_model.predictor import get_predictor

logger = logging.getLogger(__name__)


# ==============================================================================
# VIEW: home
# URL: /
# PURPOSE: Landing page. Redirect logged-in users to dashboard.
# ==============================================================================
def home(request):
    """
    Public landing page.
    If user is already logged in, skip the landing page and go to dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'detection/home.html')


# ==============================================================================
# VIEW: register
# URL: /register/
# PURPOSE: New doctor registration.
# Handles GET (show form) and POST (process form submission).
# ==============================================================================
def register(request):
    """
    Doctor registration view.
    GET:  Show the blank registration form.
    POST: Validate, save user + profile, redirect to dashboard.
    """
    # If already logged in, don't show registration page
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # ------------------------------------------------------------------
        # Bind form with POST data and uploaded files.
        # 'request.POST' contains text fields.
        # 'request.FILES' contains uploaded files.
        # ------------------------------------------------------------------
        form = DoctorRegistrationForm(request.POST, request.FILES)

        if form.is_valid():
            # Save user and profile to database
            user = form.save()

            # Automatically log in the new user
            login(request, user)

            # Add a success flash message (shown on next page)
            messages.success(
                request,
                f'Welcome, Dr. {user.first_name}! Your account has been created.'
            )
            return redirect('dashboard')
        else:
            # Form has errors — show the form again with error messages
            messages.error(request, 'Please correct the errors below.')
    else:
        # GET request: show an empty form
        form = DoctorRegistrationForm()

    return render(request, 'detection/register.html', {'form': form})


# ==============================================================================
# VIEW: login_view
# URL: /login/
# PURPOSE: Doctor login.
# ==============================================================================
def login_view(request):
    """
    Doctor login view.
    Uses Django's built-in AuthenticationForm for username/password validation.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # AuthenticationForm validates username + password against the database
        form = AuthenticationForm(data=request.POST)

        if form.is_valid():
            # get_user() returns the authenticated User object
            user = form.get_user()
            login(request, user)   # Creates a session for this user
            messages.success(request, f'Welcome back, Dr. {user.first_name}!')

            # ------------------------------------------------------------------
            # 'next' parameter: If user tried to access a protected page
            # while logged out, Django saved that URL in ?next=...
            # After login, redirect there instead of dashboard.
            # ------------------------------------------------------------------
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'detection/login.html', {'form': form})


# ==============================================================================
# VIEW: logout_view
# URL: /logout/
# PURPOSE: Log out the current user.
# ==============================================================================
def logout_view(request):
    """Logs out the user and redirects to login page."""
    logout(request)   # Destroys the session
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ==============================================================================
# VIEW: dashboard
# URL: /dashboard/
# PURPOSE: Main dashboard showing statistics and recent activity.
# @login_required: Redirects to /login/ if not authenticated.
# ==============================================================================
@login_required
def dashboard(request):
    """
    Main dashboard view.
    Shows: total patients, total scans, severity breakdown, recent results.
    """
    # Get all patients belonging to the current doctor
    patients = Patient.objects.filter(doctor=request.user)

    # Get all detection results for this doctor's patients
    results = DetectionResult.objects.filter(patient__doctor=request.user)

    # ------------------------------------------------------------------
    # STATISTICS for the dashboard cards:
    # .count() → SQL COUNT(*)
    # .filter() → SQL WHERE clause
    # ------------------------------------------------------------------
    stats = {
        'total_patients': patients.count(),
        'total_scans': results.count(),
        'no_dr_count': results.filter(predicted_class=0).count(),
        'mild_count': results.filter(predicted_class=1).count(),
        'moderate_count': results.filter(predicted_class=2).count(),
        'severe_count': results.filter(predicted_class=3).count(),
        'proliferative_count': results.filter(predicted_class=4).count(),
        # Patients needing urgent attention (severe or proliferative)
        'urgent_cases': results.filter(predicted_class__gte=3).count(),
    }

    # Average confidence score across all analyses
    avg_confidence = results.aggregate(avg=Avg('confidence_score'))
    stats['avg_confidence'] = avg_confidence['avg']

    # Recent scans: last 5 results
    recent_results = results.select_related('patient').order_by('-analyzed_at')[:5]

    # Recent patients: last 5 added
    recent_patients = patients.order_by('-created_at')[:5]

    # Data for the pie chart (JS will use this)
    chart_data = {
        'labels': ['No DR', 'Mild', 'Moderate', 'Severe', 'Proliferative'],
        'data': [
            stats['no_dr_count'],
            stats['mild_count'],
            stats['moderate_count'],
            stats['severe_count'],
            stats['proliferative_count'],
        ],
        'colors': ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#7c3aed']
    }

    context = {
        'stats': stats,
        'recent_results': recent_results,
        'recent_patients': recent_patients,
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'detection/dashboard.html', context)


# ==============================================================================
# VIEW: patient_list
# URL: /patients/
# PURPOSE: Show all patients for the logged-in doctor.
# ==============================================================================
@login_required
def patient_list(request):
    """Lists all patients belonging to the current doctor."""
    patients = Patient.objects.filter(doctor=request.user).annotate(
        scan_count=Count('results')   # Add 'scan_count' field to each patient object
    ).order_by('-created_at')

    # Simple search: filter by name if search query provided
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(name__icontains=search_query)  # Case-insensitive search

    context = {
        'patients': patients,
        'search_query': search_query,
    }
    return render(request, 'detection/patient_list.html', context)


# ==============================================================================
# VIEW: add_patient
# URL: /patients/add/
# PURPOSE: Add a new patient to the doctor's list.
# ==============================================================================
@login_required
def add_patient(request):
    """Add a new patient."""
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            # ------------------------------------------------------------------
            # commit=False: Create the object but DON'T save to DB yet.
            # This lets us set the 'doctor' field before saving.
            # ------------------------------------------------------------------
            patient = form.save(commit=False)
            patient.doctor = request.user   # Assign current doctor
            patient.save()
            messages.success(request, f'Patient {patient.name} added successfully.')
            return redirect('patient_list')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = PatientForm()

    return render(request, 'detection/add_patient.html', {'form': form})


# ==============================================================================
# VIEW: patient_detail
# URL: /patients/<id>/
# PURPOSE: Show one patient's full history (all their scans).
# ==============================================================================
@login_required
def patient_detail(request, patient_id):
    """
    Show detailed view of one patient including all their scan results.
    get_object_or_404: Returns 404 error if patient not found OR not owned by this doctor.
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    results = DetectionResult.objects.filter(patient=patient).order_by('-analyzed_at')

    context = {
        'patient': patient,
        'results': results,
        'result_count': results.count(),
    }
    return render(request, 'detection/patient_detail.html', context)


# ==============================================================================
# VIEW: edit_patient
# URL: /patients/<id>/edit/
# PURPOSE: Edit an existing patient's information.
# ==============================================================================
@login_required
def edit_patient(request, patient_id):
    """Edit patient information."""
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)  # Bind form to existing patient
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient {patient.name} updated.')
            return redirect('patient_detail', patient_id=patient.id)
    else:
        form = PatientForm(instance=patient)  # Pre-fill form with current data

    return render(request, 'detection/edit_patient.html', {'form': form, 'patient': patient})


# ==============================================================================
# VIEW: analyze
# URL: /analyze/
# PURPOSE: The CORE FEATURE — upload image and run AI analysis.
# ==============================================================================
@login_required
def analyze(request):
    """
    Retinal image upload and AI analysis view.
    GET:  Show the upload form.
    POST: Process upload, run ML model, save result, show results.
    """
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        # Set queryset to only this doctor's patients
        form.fields['patient'].queryset = Patient.objects.filter(doctor=request.user)

        if form.is_valid():
            patient = form.cleaned_data['patient']
            image_file = form.cleaned_data['image']
            doctor_notes = form.cleaned_data.get('doctor_notes', '')

            # ------------------------------------------------------------------
            # Save the uploaded image to the database record.
            # Django automatically saves the file to MEDIA_ROOT/uploads/...
            # ------------------------------------------------------------------
            result = DetectionResult(
                patient=patient,
                image=image_file,
                doctor_notes=doctor_notes
            )
            result.save()  # Save first to get the file path

            # ------------------------------------------------------------------
            # RUN THE AI MODEL
            # result.image.path = absolute file system path to the saved image
            # e.g., /home/user/dr_project/media/uploads/2024/01/15/scan.jpg
            # ------------------------------------------------------------------
            try:
                predictor = get_predictor()
                prediction = predictor.predict(result.image.path)

                # Save prediction results back to the database record
                result.predicted_class = prediction['predicted_class']
                result.confidence_score = prediction['confidence']
                result.class_probabilities = json.dumps(prediction['probabilities'])

                # Save heatmap image if generated
                if prediction.get('heatmap_base64'):
                    # Convert base64 back to image file and save
                    import base64
                    from django.core.files.base import ContentFile

                    heatmap_data = base64.b64decode(prediction['heatmap_base64'])
                    heatmap_filename = f"heatmap_{result.id}.png"
                    result.heatmap_image.save(
                        heatmap_filename,
                        ContentFile(heatmap_data),
                        save=False
                    )

                result.save()   # Final save with all prediction data

                messages.success(request, 'Analysis complete!')
                return redirect('result_detail', result_id=result.id)

            except Exception as e:
                logger.error(f"Analysis failed: {e}", exc_info=True)
                result.delete()  # Clean up failed record
                messages.error(request, f'Analysis failed: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = ImageUploadForm()
        form.fields['patient'].queryset = Patient.objects.filter(doctor=request.user)

    return render(request, 'detection/analyze.html', {'form': form})


# ==============================================================================
# VIEW: result_detail
# URL: /results/<id>/
# PURPOSE: Show the full AI analysis result for one scan.
# ==============================================================================
@login_required
def result_detail(request, result_id):
    """Show detailed result for one scan including heatmap and probabilities."""
    result = get_object_or_404(
        DetectionResult,
        id=result_id,
        patient__doctor=request.user   # Double-check ownership via patient relationship
    )

    # Parse the JSON probabilities string back to a list
    probabilities = []
    if result.class_probabilities:
        try:
            probs = json.loads(result.class_probabilities)
            labels = ['No DR', 'Mild', 'Moderate', 'Severe', 'Proliferative']
            colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#7c3aed']
            probabilities = [
                {
                    'label': labels[i],
                    'prob': probs[i],
                    'percentage': f"{probs[i]*100:.1f}",
                    'color': colors[i]
                }
                for i in range(len(probs))
            ]
        except (json.JSONDecodeError, IndexError):
            pass

    # Clinical recommendations based on severity level
    recommendations = _get_recommendations(result.predicted_class)

    context = {
        'result': result,
        'probabilities': probabilities,
        'recommendations': recommendations,
        'probabilities_json': result.class_probabilities,
    }
    return render(request, 'detection/result_detail.html', context)


# ==============================================================================
# VIEW: history
# URL: /history/
# PURPOSE: Show all scans across all of this doctor's patients.
# ==============================================================================
@login_required
def history(request):
    """Show complete analysis history for all patients."""
    results = DetectionResult.objects.filter(
        patient__doctor=request.user
    ).select_related('patient').order_by('-analyzed_at')

    # Filter by severity if requested
    severity_filter = request.GET.get('severity', '')
    if severity_filter.isdigit():
        results = results.filter(predicted_class=int(severity_filter))

    context = {
        'results': results,
        'severity_filter': severity_filter,
    }
    return render(request, 'detection/history.html', context)


# ==============================================================================
# VIEW: profile
# URL: /profile/
# PURPOSE: View/edit doctor's profile.
# ==============================================================================
@login_required
def profile(request):
    """Doctor profile page."""
    # get_or_create: Get existing profile, or create a blank one if none exists
    profile, created = DoctorProfile.objects.get_or_create(user=request.user)
    return render(request, 'detection/profile.html', {'profile': profile})


# ==============================================================================
# HELPER FUNCTION: _get_recommendations
# PURPOSE: Return clinical recommendations based on DR severity.
# ==============================================================================
def _get_recommendations(severity_class):
    """
    Returns a list of clinical recommendation strings based on predicted class.
    These are general guidelines — actual medical decisions need a real doctor!
    """
    recommendations = {
        0: [
            "✅ No signs of diabetic retinopathy detected.",
            "📅 Schedule routine annual retinal exam.",
            "🩸 Maintain good blood glucose control (HbA1c < 7%).",
            "💪 Continue healthy lifestyle: diet, exercise, no smoking.",
            "👁️ Report any sudden vision changes immediately.",
        ],
        1: [
            "⚠️ Mild diabetic retinopathy detected.",
            "📅 Schedule follow-up retinal exam in 6-12 months.",
            "🩸 Optimize blood glucose: target HbA1c < 7%.",
            "💊 Review blood pressure medications (target < 130/80 mmHg).",
            "🔬 Consider referral to ophthalmologist for further evaluation.",
        ],
        2: [
            "⚠️ Moderate diabetic retinopathy detected.",
            "📅 Schedule ophthalmology referral within 3-6 months.",
            "🩸 Intensify glucose management — consider endocrinology referral.",
            "💊 Ensure blood pressure and cholesterol are well-controlled.",
            "🔬 Fluorescein angiography may be indicated.",
        ],
        3: [
            "🚨 Severe diabetic retinopathy — URGENT referral needed.",
            "📅 Ophthalmology appointment within 2-4 weeks.",
            "🩺 High risk of vision loss — discuss treatment options with specialist.",
            "💉 Laser photocoagulation or anti-VEGF injections may be needed.",
            "🩸 Emergency glucose optimization required.",
        ],
        4: [
            "🚨 PROLIFERATIVE DR — URGENT ophthalmology referral TODAY.",
            "⚡ Immediate risk of severe vision loss or blindness.",
            "💉 Vitrectomy, laser treatment, or anti-VEGF therapy likely needed.",
            "🏥 Consider same-day or next-day specialist consultation.",
            "🩸 Urgent systemic diabetic management review required.",
        ],
    }
    return recommendations.get(severity_class, ["Please consult a specialist."])
