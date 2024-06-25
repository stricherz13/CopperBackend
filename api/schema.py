from ninja import Schema


# This schema will be used to validate the request body of the /speed-limit endpoint.
class SpeedRequestSchema(Schema):
    lat: float
    lon: float
    current_speed: int
