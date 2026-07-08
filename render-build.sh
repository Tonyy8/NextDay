#!/usr/bin/env bash
set -euo pipefail
pip install -r requirements.txt
python manage.py migrate --noinput
python -c "import your_application.wsgi as wsgi; assert wsgi.application"
python manage.py check
python manage.py collectstatic --noinput
