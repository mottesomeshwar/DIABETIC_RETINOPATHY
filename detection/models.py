"""
================================================================================
  FILE: detection/models.py
  PURPOSE: Defines the DATABASE TABLES for our app using Python classes.
  Each class = one table. Each attribute = one column.
  Django's ORM (Object Relational Mapper) converts these classes to SQL.
================================================================================
"""

from django.db import models
from django.contrib.auth.models import User   # Django's built-in User model
from django.utils import timezone              # Timezone-aware datetime


# ==============================================================================
# CLASS: DoctorProfile
# PURPOSE: Extends the built-in User model with doctor-specific information.
# We use a OneToOneField so each User has exactly one DoctorProfile.
# ==============================================================================
class DoctorProfile(models.Model):
    # ------------------------------------------------------------------
    # OneToOneField: Links this profile to exactly one User account.
    # on_delete=CASCADE: If the User is deleted, delete the profile too.
    # related_name='profile': Lets us do user.profile to get this object.
    # ------------------------------------------------------------------
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # ------------------------------------------------------------------
    # CharField: A text field with a maximum length.
    # blank=True: This field is optional in forms.
    # ------------------------------------------------------------------
    specialization = models.CharField(max_length=100, blank=True)
    hospital = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    license_number = models.CharField(max_length=50, blank=True)

    # ------------------------------------------------------------------
    # ImageField: Stores a file path in the database, actual file on disk.
    # upload_to: subfolder inside MEDIA_ROOT where profile pics are saved.
    # null=True: Database column can be NULL (no image uploaded).
    # ------------------------------------------------------------------
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True
    )

    # String representation: what shows in Django Admin for this object
    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"

    class Meta:
        verbose_name = "Doctor Profile"
        verbose_name_plural = "Doctor Profiles"


# ==============================================================================
# CLASS: Patient
# PURPOSE: Stores patient information. Each patient belongs to one doctor.
# ==============================================================================
class Patient(models.Model):
    # ------------------------------------------------------------------
    # ForeignKey: Many patients can belong to one doctor.
    # related_name='patients': Lets us do doctor_user.patients.all()
    # ------------------------------------------------------------------
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='patients'
    )

    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()           # Only positive integers allowed

    # ------------------------------------------------------------------
    # CHOICES: Restricts the field to predefined options.
    # Stored as 'M'/'F'/'O' in DB, displayed as 'Male'/'Female'/'Other'.
    # ------------------------------------------------------------------
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    # Patient contact & medical info
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    diabetes_duration = models.PositiveIntegerField(
        help_text="Years with diabetes",
        default=0
    )
    notes = models.TextField(blank=True)  # TextField: unlimited length text

    # ------------------------------------------------------------------
    # auto_now_add=True: Automatically set to NOW when record is CREATED.
    # auto_now=True: Automatically updated to NOW every time record is SAVED.
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Age: {self.age})"

    class Meta:
        ordering = ['-created_at']   # Default sort: newest patients first


# ==============================================================================
# CLASS: DetectionResult
# PURPOSE: Stores one retinal scan + AI prediction result per record.
# Each result belongs to one Patient.
# ==============================================================================
class DetectionResult(models.Model):
    # ------------------------------------------------------------------
    # ForeignKey to Patient: One patient can have MANY scan results.
    # ------------------------------------------------------------------
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='results'
    )

    # ------------------------------------------------------------------
    # The uploaded retinal fundus image.
    # upload_to: organizes by year/month/day automatically.
    # ------------------------------------------------------------------
    image = models.ImageField(upload_to='uploads/%Y/%m/%d/')

    # ------------------------------------------------------------------
    # DR SEVERITY LEVELS:
    # 0 = No DR, 1 = Mild, 2 = Moderate, 3 = Severe, 4 = Proliferative
    # ------------------------------------------------------------------
    DR_LEVELS = [
        (0, 'No Diabetic Retinopathy'),
        (1, 'Mild DR'),
        (2, 'Moderate DR'),
        (3, 'Severe DR'),
        (4, 'Proliferative DR'),
    ]
    predicted_class = models.IntegerField(choices=DR_LEVELS, null=True, blank=True)

    # ------------------------------------------------------------------
    # Confidence score: A float between 0.0 and 1.0.
    # Example: 0.87 means the model is 87% confident in its prediction.
    # ------------------------------------------------------------------
    confidence_score = models.FloatField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Grad-CAM heatmap: Another image showing WHICH parts of the retina
    # the AI focused on when making its decision.
    # ------------------------------------------------------------------
    heatmap_image = models.ImageField(
        upload_to='heatmaps/%Y/%m/%d/',
        null=True,
        blank=True
    )

    # Additional class probabilities stored as text (JSON string)
    class_probabilities = models.TextField(null=True, blank=True)

    doctor_notes = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def get_severity_label(self):
        """Returns the human-readable severity label for the predicted class."""
        labels = {
            0: 'No DR',
            1: 'Mild',
            2: 'Moderate',
            3: 'Severe',
            4: 'Proliferative'
        }
        return labels.get(self.predicted_class, 'Unknown')

    def get_severity_color(self):
        """Returns a CSS color class based on severity (for UI display)."""
        colors = {
            0: 'success',    # Green  - No DR
            1: 'info',       # Blue   - Mild
            2: 'warning',    # Yellow - Moderate
            3: 'danger',     # Red    - Severe
            4: 'dark',       # Dark   - Proliferative
        }
        return colors.get(self.predicted_class, 'secondary')

    def get_confidence_percentage(self):
        """Returns confidence as a percentage string (e.g., '87.3%')."""
        if self.confidence_score is not None:
            return f"{self.confidence_score * 100:.1f}%"
        return "N/A"

    def __str__(self):
        return f"{self.patient.name} - {self.get_severity_label()} ({self.analyzed_at.date()})"

    class Meta:
        ordering = ['-analyzed_at']   # Newest scans first
