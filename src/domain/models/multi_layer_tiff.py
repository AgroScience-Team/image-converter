from typing import List

from pydantic import BaseModel


class MultiLayerTiff(BaseModel):
    photoExtension: str
    layers: List[str]
