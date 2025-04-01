from pydantic import BaseModel, Field, field_validator
from typing import List


class PositionData(BaseModel):
    current: List[float] = Field(..., min_items=2, max_items=2)
    pickup: List[float] = Field(..., min_items=2, max_items=2)
    dropoff: List[float] = Field(..., min_items=2, max_items=2)

    @field_validator('current', 'pickup', 'dropoff', mode='before')
    def validate_lat_lng(cls, value):
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Coordinates must be a list of two floats: [longitude, latitude].")

        lon, lat = value  # Longitude first, then latitude

        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180.")
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90.")

        return value
