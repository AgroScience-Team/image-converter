from datetime import datetime
from typing import List

from pydantic import BaseModel, model_validator

class Layer(BaseModel):
    index: str
    name: str

class MultiLayerTiff(BaseModel):
    extension: str
    date: str
    contourId: str
    layers: List[Layer]

    @model_validator(mode='before')
    def format_date(cls, values):
        # Получаем дату из MongoDB (предполагается, что это объект datetime)
        date_value = values.get('date')
        if isinstance(date_value, datetime):
            # Форматируем дату как строку в формате 'YYYY-MM-DD'
            values['date'] = date_value.strftime('%Y-%m-%d')
        return values
