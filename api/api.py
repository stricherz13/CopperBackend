import geojson
from asgiref.sync import sync_to_async
from ninja import NinjaAPI
from ninja.errors import HttpError
import httpx
from shapely.geometry import Point, LineString
from .schema import SpeedRequestSchema
from .models import SpeedRecord
from .utils import segment_trips

api = NinjaAPI()


# This function will use the Overpass API to get the nearest road to a given latitude and longitude.
async def get_nearest_road(lat, lon):
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    way(around:50,{lat},{lon})["highway"];
    out geom;
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    return data


# This function will get the speed limit of the nearest road to a given latitude and longitude.
def get_speed_limit(road_data, lat, lon):
    point = Point(lon, lat)
    nearest_way = None
    min_distance = float('inf')

    # Find the nearest road to the given latitude and longitude. Loop through all the elements in the road_data.
    for element in road_data['elements']:
        if 'geometry' in element:
            line = LineString([(node['lon'], node['lat']) for node in element['geometry']])
            distance = point.distance(line)
            if distance < min_distance:
                min_distance = distance
                nearest_way = element

    # If the nearest road has a maxspeed tag, return the speed limit as an integer.
    if nearest_way and 'tags' in nearest_way and 'maxspeed' in nearest_way['tags']:
        try:
            speed_limit = int(nearest_way['tags']['maxspeed'].split()[0])
            return speed_limit
        except (ValueError, IndexError):
            return None
    return None


@api.get("/speed-limit")
async def get_speed_limit_endpoint(request, lat: float, lon: float):
    road_data = await get_nearest_road(lat, lon)
    speed_limit = get_speed_limit(road_data, lat, lon)

    if speed_limit:
        return {"speed_limit": speed_limit}
    else:
        return {"error": "No speed limit information found"}


@api.post("/speed-info")
async def get_speed_info(request, payload: SpeedRequestSchema):
    lat = payload.lat
    lon = payload.lon
    user_speed = payload.user_speed

    try:
        road_data = await get_nearest_road(lat, lon)
        speed_limit = get_speed_limit(road_data, lat, lon)

        if speed_limit is None:
            raise HttpError(404, "No speed limit information found")

        speed_difference = user_speed - speed_limit
        if speed_difference < 0:
            speed_difference = 0
        else:
            speed_difference = speed_difference

        # Save the speed record to the database
        speed_record = SpeedRecord(
            latitude=lat,
            longitude=lon,
            current_speed=user_speed,
            road_speed_limit=speed_limit,
            speed_difference=speed_difference
        )
        await sync_to_async(speed_record.save)()

        return {
            "latitude": lat,
            "longitude": lon,
            "user_speed": user_speed,
            "road_speed_limit": speed_limit,
            "speed_difference": speed_difference
        }
    except Exception as e:
        raise HttpError(500, f"Internal server error: {e}")


@api.get("/speed-heatmap")
async def get_speed_heatmap(request):
    try:
        # Retrieve all SpeedRecord data
        speed_records = await sync_to_async(list)(SpeedRecord.objects.all().order_by('timestamp'))

        if not speed_records:
            raise HttpError(404, "No speed records found")

        # Segment the data into trips
        segmented_trips = segment_trips(speed_records)

        # Create GeoJSON features for each trip
        features = []
        for trip in segmented_trips:
            coordinates = [(record.longitude, record.latitude) for record in trip]
            speed_differences = [record.speed_difference for record in trip]

            if len(coordinates) < 2:
                continue  # Skip trips with not enough data points

            line = LineString(coordinates)
            feature = geojson.Feature(
                geometry=line,
                properties={"speed_differences": speed_differences}
            )
            features.append(feature)

        if not features:
            raise HttpError(400, "Not enough data points to create LineString features")

        feature_collection = geojson.FeatureCollection(features)
        return feature_collection

    except Exception as e:
        raise HttpError(500, f"Internal server error: {e}")
