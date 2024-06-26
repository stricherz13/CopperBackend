from django.db import models


class SpeedRecord(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    current_speed = models.IntegerField()
    road_speed_limit = models.IntegerField()
    speed_difference = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SpeedRecord at ({self.latitude}, {self.longitude})"
