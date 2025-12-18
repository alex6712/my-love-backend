from app.models.base import BaseModel


class Album(BaseModel):
    def __init__(self, title, artist, year):
        self.title = title
        self.artist = artist
        self.year = year
