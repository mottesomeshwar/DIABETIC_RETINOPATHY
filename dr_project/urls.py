"""
================================================================================
  FILE: dr_project/urls.py
  PURPOSE: The MAIN URL router. Every incoming web request is matched here
  to decide which view function should handle it.
================================================================================
"""

from django.contrib import admin
from django.urls import path, include          # include() wires in app-level URLs
from django.conf import settings               # Access our settings (MEDIA_ROOT etc.)
from django.conf.urls.static import static     # Helper to serve uploaded files in dev

urlpatterns = [
    # ------------------------------------------------------------------
    # /admin/ → Django's built-in administration panel.
    # Access it at http://127.0.0.1:8000/admin/
    # ------------------------------------------------------------------
    path('admin/', admin.site.urls),

    # ------------------------------------------------------------------
    # '' (empty string) → hand ALL other URLs over to detection/urls.py
    # include() means: strip the matched prefix, then route the rest
    # inside detection/urls.py
    # ------------------------------------------------------------------
    path('', include('detection.urls')),
]

# ------------------------------------------------------------------------------
# SERVE MEDIA FILES IN DEVELOPMENT
# When DEBUG=True, Django serves uploaded images (retinal scans) directly.
# In production, a web server (Nginx/Apache) handles this instead.
# static() returns a URL pattern like: /media/<path> → MEDIA_ROOT/<path>
# ------------------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
