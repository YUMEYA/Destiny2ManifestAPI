from fastapi import FastAPI

from ..config import DEBUG
from .models import mongo


def create_app():
    app = FastAPI(title="Destiny 2 Manifest API", debug=DEBUG)
    mongo.init_app(app)
    return app
