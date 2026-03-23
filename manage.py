#!/usr/bin/env python
"""
================================================================================
  FILE: manage.py
  PURPOSE: Django's command-line management utility.
  This is the entry point for all Django commands:

  USAGE EXAMPLES:
    python manage.py runserver          → Start development web server
    python manage.py makemigrations     → Create new database migration files
    python manage.py migrate            → Apply migrations to the database
    python manage.py createsuperuser    → Create an admin account
    python manage.py shell              → Open Django Python REPL
    python manage.py collectstatic      → Gather static files for production

  You NEVER need to edit this file.
================================================================================
"""
import os
import sys


def main():
    """Run administrative tasks."""
    # Tell Django which settings module to use
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dr_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Parse and execute the command-line arguments (e.g., 'runserver')
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
