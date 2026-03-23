"""
================================================================================
  FILE: detection/admin.py
  PURPOSE: Registers our models with Django's admin panel.
  After this, you can manage all data at http://127.0.0.1:8000/admin/
================================================================================
"""

from django.contrib import admin
from .models import DoctorProfile, Patient, DetectionResult


# @admin.register(Model): Decorator to register a model with a custom admin class
@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    # list_display: Columns shown in the admin list view
    list_display = ['user', 'specialization', 'hospital', 'phone']
    # search_fields: Which fields the search box searches through
    search_fields = ['user__username', 'user__email', 'specialization']


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'age', 'gender', 'doctor', 'diabetes_duration', 'created_at']
    list_filter = ['gender', 'created_at']   # Sidebar filters
    search_fields = ['name', 'email', 'phone']
    # ordering: Default sort order in admin list
    ordering = ['-created_at']


@admin.register(DetectionResult)
class DetectionResultAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'predicted_class', 'confidence_score',
        'analyzed_at', 'get_severity_label'
    ]
    list_filter = ['predicted_class', 'analyzed_at']
    search_fields = ['patient__name']
    ordering = ['-analyzed_at']
    # readonly_fields: These fields can't be edited in admin
    readonly_fields = ['analyzed_at', 'predicted_class', 'confidence_score']
