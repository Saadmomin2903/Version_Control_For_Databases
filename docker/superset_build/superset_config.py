import os

# Database connection
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:////app/superset_home/superset.db")

# Secret key
SECRET_KEY = os.getenv("SUPERSET_SECRET_KEY", "default_secret_key_1234")

# Timeouts (Increased to 1 HOUR)
SUPERSET_WEBSERVER_TIMEOUT = int(os.getenv("SUPERSET_WEBSERVER_TIMEOUT", 3600))
SUPERSET_TIMEOUT = int(os.getenv("SUPERSET_TIMEOUT", 3600))
SQLLAB_TIMEOUT = int(os.getenv("SQLLAB_TIMEOUT", 3600))

# Result Backend Timeout
RESULTS_BACKEND_USE_MGZIP = True

# Database Pool Settings (Optimized for Heavy Dashboards)
SQLALCHEMY_POOL_SIZE = 30
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_RECYCLE = 300
SQLALCHEMY_POOL_TIMEOUT = 3600

# Map settings
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY", "")

# Feature flags
FEATURE_FLAGS = {
    "DYNAMIC_PLUGINS": False,  # Disabled - causes 404 errors without proper setup
    "ALERT_REPORTS": True,
    # Performance Optimizations (Fix for GitHub #29636 - slow loading)
    "DASHBOARD_VIRTUALIZATION": True,  # Only render visible charts
    "DASHBOARD_NATIVE_FILTERS": True,  # Use native filter bar
    "DASHBOARD_CROSS_FILTERS": True,   # Enable cross-filtering
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# The image uses Gunicorn by default
# GUNICORN_TIMEOUT is handled by the entrypoint env var
