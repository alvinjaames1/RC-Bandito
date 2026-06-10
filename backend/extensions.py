"""
RC Bandito - Shared Flask Extensions
This file exists so that app.py, models, and routes can all import
the same db / login_manager / limiter objects without circular imports.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
