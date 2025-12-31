import eventlet
import sys

# Patch only if not running a CLI command that doesn't need it
# Some CLI commands like 'flask db migrate' trip over monkey_patching LocalProxies
# leading to RuntimeError: Working outside of application context.
if not any(arg in sys.argv for arg in ["db", "migrate", "upgrade", "shell"]):
    try:
        eventlet.monkey_patch()
    except Exception as e:
        print(f"[WSGI] Warning: monkey_patch failed: {e}")
else:
    # Minimal patching for CLI if needed, or skip
    # For migrations, we usually don't need eventlet at all
    pass

from app import create_app  # noqa
from dotenv import load_dotenv  # noqa
import os  # noqa

load_dotenv()

app = create_app(os.getenv("FLASK_ENV", "production"))
