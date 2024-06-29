from django.test import TestCase, Client
from django.urls import reverse
from api.models import SpeedRecord


class SpeedInfoAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('api:speed_info')

    def test_speed_info_post_valid(self):
        payload = {
            "lat": 52.5200,
            "lon": 13.4050,
            "current_speed": 50.0
        }
        response = self.client.post(self.url, payload, content_type='application/json')
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
        response = self.client.post(self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 422)

    def test_speed_record_creation(self):
        payload = {
            "lat": 52.5200,
            "lon": 13.4050,
            "current_speed": 50.0
        }
        response = self.client.post(self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SpeedRecord.objects.count(), 1)
        speed_record = SpeedRecord.objects.first()
        self.assertEqual(speed_record.latitude, payload['lat'])
        self.assertEqual(speed_record.longitude, payload['lon'])
        self.assertEqual(speed_record.current_speed, payload['current_speed'])
