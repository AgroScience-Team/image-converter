from pydantic import BaseModel

class NewPhotosResponse(BaseModel):
    id: str
    contourId: str
    date: str
    extension: str
