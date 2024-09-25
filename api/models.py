from django.contrib.gis.db import models as gis_models
from django.db import models


class SpeedRecord(models.Model):
    location = gis_models.PointField(geography=True, srid=4326, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    current_speed = models.IntegerField()
    road_speed_limit = models.IntegerField()
    speed_difference = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SpeedRecord at ({self.latitude}, {self.longitude})"
