import geojson
from asgiref.sync import sync_to_async
from ninja import NinjaAPI
from ninja.errors import HttpError
import httpx
from shapely.geometry import Point, LineString
from .schema import SpeedRequestSchema
from .models import SpeedRecord
from .utils import segment_trips, interpolate_speed_differences

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


import logging
import geojson
from shapely.geometry import Point, LineString
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


@api.get("/speed-heatmap")
async def get_speed_heatmap(request):
    try:
        logger.info("Fetching all speed records...")
        # Retrieve all SpeedRecord data
        speed_records = await sync_to_async(list)(SpeedRecord.objects.all().order_by('timestamp'))
        logger.debug(f"Fetched {len(speed_records)} speed records")

        if not speed_records:
            logger.warning("No speed records found")
            return {"detail": "No speed records found"}, 404

        # Segment the data into trips
        logger.info("Segmenting trips...")
        segmented_trips = segment_trips(speed_records)
        logger.debug(f"Segmented into {len(segmented_trips)} trips")

        # Interpolating speed differences for each trip
        all_interpolated_points = []
        all_interpolated_speeds = []

        for trip in segmented_trips:
            points, speeds = interpolate_speed_differences(trip)
            all_interpolated_points.append(points)
            all_interpolated_speeds.append(speeds)
            logger.debug(f"Interpolated trip with {len(points)} points and {len(speeds)} speeds")

        # Flatten the lists
        all_points = [pt for sublist in all_interpolated_points for pt in sublist]
        all_speeds = [spd for sublist in all_interpolated_speeds for spd in sublist]
        logger.debug(f"Flattened to {len(all_points)} total points and {len(all_speeds)} total speeds")

        # Calculate average speed differences for overlapping segments
        point_speed_map = {}
        for pt, spd in zip(all_points, all_speeds):
            coord = (pt.x, pt.y)
            if coord not in point_speed_map:
                point_speed_map[coord] = []
            point_speed_map[coord].append(spd)

        averaged_points = []
        averaged_speeds = []
        for coord, speeds in point_speed_map.items():
            # Filter out 0 values
            valid_speeds = [spd for spd in speeds if spd != 0]
            if valid_speeds:
                averaged_points.append(Point(coord))
                averaged_speeds.append(sum(valid_speeds) / len(valid_speeds))
        logger.debug(f"Averaged to {len(averaged_points)} points with corresponding speeds")

        # Create GeoJSON features
        if not averaged_points:
            logger.warning("Not enough data points to create LineString features")
            return {"detail": "Not enough data points to create LineString features"}, 400

        line = LineString([(pt.x, pt.y) for pt in averaged_points])
        feature = geojson.Feature(
            geometry=line,
            properties={"average_speed_differences": averaged_speeds}
        )

        feature_collection = geojson.FeatureCollection([feature])
        logger.info("Successfully created GeoJSON feature collection")
        return feature_collection

    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return {"detail": f"Internal server error: {e}"}, 500
