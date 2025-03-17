from datetime import datetime
from typing import List

from pydantic import BaseModel, model_validator

class Layer(BaseModel):
    index: str
    name: str

class MultiLayerTiff(BaseModel):
    extension: str
    date: datetime
    contourId: str
    layers: List[Layer]
