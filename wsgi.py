import eventlet
eventlet.monkey_patch()

from app import create_app # noqa
from dotenv import load_dotenv # noqa
import os # noqa

load_dotenv()

app = create_app(os.getenv("FLASK_ENV", "production"))