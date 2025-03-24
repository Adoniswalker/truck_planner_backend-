from pydantic import BaseModel, Field, field_validator


class PositionData(BaseModel):
    # value: str = Field(pattern=r'^abc(?=def)')
    currentLocation: str =  Field(pattern=r'^-?\d{1,2}(\.\d+)?,\s*-?\d{1,3}(\.\d+)?$')
    pickupLocation:str = Field(pattern=r'^-?\d{1,2}(\.\d+)?,\s*-?\d{1,3}(\.\d+)?$')
    dropoffLocation:str  =  Field(pattern=r'^-?\d{1,2}(\.\d+)?,\s*-?\d{1,3}(\.\d+)?$')

    @field_validator('currentLocation', 'pickupLocation', 'dropoffLocation')
    def validate_lat_lng_range(cls, value):
        try:
            latitude, longitude = map(float, value.split(", "))
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("Invalid latitude or longitude range.")
            return value
        except ValueError:
            raise ValueError("Invalid latitude or longitude format.")
