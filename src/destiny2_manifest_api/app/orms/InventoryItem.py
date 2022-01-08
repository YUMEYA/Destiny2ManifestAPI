from . import db
from sqlalchemy.dialects.postgresql import JSONB


class InventoryItem(db.Model):
    __tablename__ = "destinyinventoryitemdefinition"

    id = db.Column(db.Integer)
    json = db.Column(JSONB)

    displayProperties = db.ObjectProperty(prop_name="json")
    name = db.StringProperty(prop_name="displayProperties")
