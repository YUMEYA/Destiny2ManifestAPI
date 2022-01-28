from .base_model import BaseModel


class Lore(BaseModel):
    __collection_name__ = "DestinyLoreDefinition"

    @property
    def title(self):
        return self.displayProperties.get("name", "")

    @property
    def subtitle(self):
        return self.raw.get("subtitle", "")

    @property
    def content(self):
        return self.displayProperties.get("description", "")

    def as_dict(self):
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "content": self.content,
        }
