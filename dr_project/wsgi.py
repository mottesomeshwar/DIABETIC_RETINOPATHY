"""
================================================================================
  FILE: dr_project/wsgi.py
  PURPOSE: WSGI (Web Server Gateway Interface) entry point.
  This file is used when deploying to production servers like Gunicorn.
  You don't need to edit this file.
================================================================================
"""
import os
from django.core.wsgi import get_wsgi_application

# Tell Django which settings module to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dr_project.settings')

# Create the WSGI application object that servers use
application = get_wsgi_application()
