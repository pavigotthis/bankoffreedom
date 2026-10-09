"""Hosted HTTPS entry point. Initialize migrations before the first request.

No development server, credentials, demo records, or data reset runs on import.
The hosting provider must supply persistent storage for DATABASE_PATH.
"""

import os

from three_du import create_app

os.environ.setdefault("COOKIE_SECURE", "1")
os.environ.setdefault("SYNTHETIC_ONLY", "1")
application = create_app()
