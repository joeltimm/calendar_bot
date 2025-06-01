# gunicorn_config.py
import os # Make sure to import os

bind = "0.0.0.0:5000"
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
# Optional:
# accesslog = '-' # Log to stdout
# errorlog = '-'  # Log to stdout