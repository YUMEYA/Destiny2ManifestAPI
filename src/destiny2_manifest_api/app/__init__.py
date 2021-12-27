from fastapi import FastAPI

from ..config import DEBUG

from .models import db


def create_app():
    app = FastAPI(title="Destiny 2 Manifest API", debug=DEBUG)
    db.init_app(app)
    return app
