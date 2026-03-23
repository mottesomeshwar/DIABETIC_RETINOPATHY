"""
================================================================================
  FILE: detection/forms.py
  PURPOSE: Defines HTML forms using Python classes.
  Django forms handle: rendering HTML inputs, validating submitted data,
  and converting form data to Python objects / database records.
================================================================================
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm  # Built-in registration form
from .models import DoctorProfile, Patient, DetectionResult


# ==============================================================================
# FORM: DoctorRegistrationForm
# PURPOSE: Registration form that creates BOTH a User AND a DoctorProfile.
# Inherits from UserCreationForm which already handles username/password fields.
# ==============================================================================
class DoctorRegistrationForm(UserCreationForm):
    # ------------------------------------------------------------------
    # Extra fields NOT in the default UserCreationForm.
    # required=True means the field MUST be filled in.
    # ------------------------------------------------------------------
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'doctor@hospital.com'
        })
    )
    specialization = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Ophthalmologist'
        })
    )
    hospital = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Hospital / Clinic name'
        })
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+91 9876543210'
        })
    )
    license_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Medical license number'
        })
    )

    class Meta:
        # ------------------------------------------------------------------
        # Meta inner class: configuration for the form.
        # model: which database model this form creates/updates.
        # fields: which fields to include (from the User model).
        # ------------------------------------------------------------------
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'password1', 'password2']

    def __init__(self, *args, **kwargs):
        """Customize widget attributes for inherited fields."""
        super().__init__(*args, **kwargs)
        # Add CSS classes to the inherited username/password fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Repeat your password'
        })

    def save(self, commit=True):
        """
        Override save() to also create the DoctorProfile.
        commit=True means actually save to database.
        """
        # First, save the User object (from parent class)
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            # Now create the associated DoctorProfile
            DoctorProfile.objects.create(
                user=user,
                specialization=self.cleaned_data.get('specialization', ''),
                hospital=self.cleaned_data.get('hospital', ''),
                phone=self.cleaned_data.get('phone', ''),
                license_number=self.cleaned_data.get('license_number', ''),
            )
        return user


# ==============================================================================
# FORM: PatientForm
# PURPOSE: Add or edit patient information.
# ModelForm automatically generates fields from the model.
# ==============================================================================
class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        # Exclude fields that are set automatically (doctor is set in the view)
        fields = ['name', 'age', 'gender', 'email', 'phone',
                  'diabetes_duration', 'notes']

        # ------------------------------------------------------------------
        # widgets: Customize the HTML input element for each field.
        # attrs: HTML attributes added to the <input> element.
        # ------------------------------------------------------------------
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Patient full name'
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1', 'max': '120'
            }),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'patient@email.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 9876543210'
            }),
            'diabetes_duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional medical notes...'
            }),
        }


# ==============================================================================
# FORM: ImageUploadForm
# PURPOSE: Handles the retinal image upload for DR detection.
# ==============================================================================
class ImageUploadForm(forms.Form):
    # ------------------------------------------------------------------
    # ImageField: Validates that the uploaded file is an actual image.
    # ------------------------------------------------------------------
    image = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',   # Only allow image files in file picker
            'id': 'imageUpload'
        })
    )

    # ------------------------------------------------------------------
    # ModelChoiceField: Renders as a <select> dropdown.
    # queryset: which Patient records to show — set dynamically in the view.
    # ------------------------------------------------------------------
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.none(),  # Empty initially, set in view
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Select the patient for this scan'
    )

    doctor_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional pre-analysis notes...'
        })
    )
