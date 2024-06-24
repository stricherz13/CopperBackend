# Django Speed Limit API

This project is a Django-based API that retrieves the speed limit of a road at a specific GPS location using the OpenStreetMap Overpass API.

## Features

- Asynchronous API endpoint to get the speed limit for a given latitude and longitude
- Uses `uvicorn` as the ASGI server for asynchronous support
- Environment variables management using `python-dotenv`

## Requirements

- Python 3.8 or higher
- Django 3.2 or higher
- `httpx` for asynchronous HTTP requests
- `shapely` for geometric calculations
- `python-dotenv` for environment variables management

## Installation

1. **Clone the repository**

   ```sh
   git clone https://github.com/yourusername/django-speed-limit-api.git
   cd django-speed-limit-api
