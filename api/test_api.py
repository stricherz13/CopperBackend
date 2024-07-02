# myapp/test_api.py

from django.test import TestCase, Client
from django.urls import reverse
from api.models import SpeedRecord
import json


class SpeedInfoAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.speed_limit_url = reverse('speed-limit')
        self.speed_info_url = reverse('speed-info')
        self.speed_heatmap_url = reverse('speed-heatmap')

    def test_speed_info_post_valid(self):
        payload = {
            "lat": 52.5200,
            "lon": 13.4050,
            "current_speed": 50.0
        }
        response = self.client.post(self.speed_info_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('latitude', response.json())
        self.assertIn('longitude', response.json())
        self.assertIn('current_speed', response.json())
        self.assertIn('road_speed_limit', response.json())
        self.assertIn('speed_difference', response.json())

    def test_speed_info_post_invalid(self):
        payload = {
            "lat": "invalid_latitude",
            "lon": 13.4050,
            "current_speed": 50.0
        }
        response = self.client.post(self.speed_info_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 422)

    def test_speed_record_creation(self):
        payload = {
            "lat": 52.5200,
            "lon": 13.4050,
            "current_speed": 50.0
        }
        response = self.client.post(self.speed_info_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SpeedRecord.objects.count(), 1)
        speed_record = SpeedRecord.objects.first()
        self.assertEqual(speed_record.latitude, payload['lat'])
        self.assertEqual(speed_record.longitude, payload['lon'])
        self.assertEqual(speed_record.current_speed, payload['current_speed'])

    def test_speed_heatmap_get(self):
        # Create some SpeedRecord instances
        SpeedRecord.objects.create(latitude=52.5200, longitude=13.4050, current_speed=50.0, road_speed_limit=30.0,
                                   speed_difference=20.0)
        SpeedRecord.objects.create(latitude=52.5201, longitude=13.4051, current_speed=40.0, road_speed_limit=30.0,
                                   speed_difference=10.0)

        response = self.client.get(self.speed_heatmap_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertEqual(len(data['features']), 1)
        feature = data['features'][0]
        self.assertEqual(feature['geometry']['type'], 'LineString')
        self.assertEqual(len(feature['geometry']['coordinates']), 2)
        self.assertEqual(len(feature['properties']['speed_differences']), 2)
