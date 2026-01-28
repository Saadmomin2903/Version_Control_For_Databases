import os

# Database connection
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:////app/superset_home/superset.db")

# Secret key
SECRET_KEY = os.getenv("SUPERSET_SECRET_KEY", "default_secret_key_1234")

# Timeouts (Increased to 5 minutes)
SUPERSET_WEBSERVER_TIMEOUT = int(os.getenv("SUPERSET_WEBSERVER_TIMEOUT", 300))
SUPERSET_TIMEOUT = int(os.getenv("SUPERSET_TIMEOUT", 300))
SQLLAB_TIMEOUT = int(os.getenv("SQLLAB_TIMEOUT", 300))

# Result Backend Timeout
RESULTS_BACKEND_USE_MGZIP = True

# Map settings
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY", "")

# Feature flags
FEATURE_FLAGS = {
    "DYNAMIC_PLUGINS": True,
    "ALERT_REPORTS": True,
}

# The image uses Gunicorn by default
# GUNICORN_TIMEOUT is handled by the entrypoint env var
