from datetime import datetime, timezone

from pydantic import BaseModel, field_serializer

class NewPhotosResponse(BaseModel):
    photoId: str
    contourId: str
    date: datetime
    extension: str

    @field_serializer("date")
    def serialize_datetime(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
