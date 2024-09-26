import geojson
import httpx
from asgiref.sync import sync_to_async
from django.contrib.gis.geos import Point
from django.db.models import Avg, Max, Min
from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.errors import HttpError
from shapely.geometry import LineString, Point

from .models import SpeedRecord
from .schema import SpeedRequestSchema

# from .utils import interpolate_speed_differences, segment_trips

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
        response = await client.get(overpass_url, params={"data": overpass_query})
    data = response.json()
    return data


# This function will get the speed limit of the nearest road to a given latitude and longitude.
def get_speed_limit(road_data, lat, lon):
    point = Point(lon, lat)
    nearest_way = None
    min_distance = float("inf")

    # Find the nearest road to the given latitude and longitude. Loop through all the elements in the road_data.
    for element in road_data["elements"]:
        if "geometry" in element:
            line = LineString(
                [(node["lon"], node["lat"]) for node in element["geometry"]]
            )
            distance = point.distance(line)
            if distance < min_distance:
                min_distance = distance
                nearest_way = element

    # If the nearest road has a maxspeed tag, return the speed limit as an integer.
    if nearest_way and "tags" in nearest_way and "maxspeed" in nearest_way["tags"]:
        try:
            speed_limit = int(nearest_way["tags"]["maxspeed"].split()[0])
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

        location_point = Point(lon, lat, srid=4326)
        # Save the speed record to the database
        speed_record = SpeedRecord(
            location=location_point,
            latitude=lat,
            longitude=lon,
            current_speed=user_speed,
            road_speed_limit=speed_limit,
            speed_difference=speed_difference,
        )
        await sync_to_async(speed_record.save)()

        return {
            "latitude": lat,
            "longitude": lon,
            "user_speed": user_speed,
            "road_speed_limit": speed_limit,
            "speed_difference": speed_difference,
        }
    except Exception as e:
        raise HttpError(500, f"Internal server error: {e}")


@api.get("/speed-heatmap")
def get_speed_heatmap(request):
    try:
        # Aggregate min, max, and avg speed differences for each unique location (road/point)
        aggregated_data = (
            SpeedRecord.objects.values("location")
            .annotate(
                avg_speed_diff=Avg("speed_difference"),
                min_speed_diff=Min("speed_difference"),
                max_speed_diff=Max("speed_difference"),
            )
            .values("location", "avg_speed_diff", "min_speed_diff", "max_speed_diff")
        )

        # Prepare the data for the GeoJSON response
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [record["location"].x, record["location"].y],
                    },
                    "properties": {
                        "avg_speed_difference": record["avg_speed_diff"],
                        "min_speed_difference": record["min_speed_diff"],
                        "max_speed_difference": record["max_speed_diff"],
                    }
                }
                for record in aggregated_data
            ]
        }

        return JsonResponse(geojson_data)
    except Exception as e:
        raise HttpError(500, f"Internal server error: {e}")

# @api.get("/speed-heatmap")
# async def get_speed_heatmap(request):
#     try:
#         print("Fetching all speed records...")
#         # Retrieve all SpeedRecord data
#         speed_records = await sync_to_async(list)(
#             SpeedRecord.objects.all().order_by("timestamp")
#         )
#         print(f"Fetched {len(speed_records)} speed records")

#         if not speed_records:
#             print("No speed records found")
#             return JsonResponse({"detail": "No speed records found"}, status=404)

#         # Segment the data into trips
#         print("Segmenting trips...")
#         segmented_trips = segment_trips(speed_records)
#         print(f"Segmented into {len(segmented_trips)} trips")

#         if len(segmented_trips) > 1:
#             # Interpolating speed differences for each trip
#             all_interpolated_points = []
#             all_interpolated_speeds = []

#             for trip in segmented_trips:
#                 print(f"Interpolating trip with {len(trip)} points...")
#                 points, speeds = interpolate_speed_differences(trip)
#                 if not points or not speeds:
#                     print("Interpolation returned empty lists")
#                 else:
#                     print(f"Interpolated {len(points)} points and {len(speeds)} speeds")
#                 all_interpolated_points.extend(points)
#                 all_interpolated_speeds.extend(speeds)
#                 print(f"All interpolated points so far: {len(all_interpolated_points)}")
#                 print(f"All interpolated speeds so far: {len(all_interpolated_speeds)}")

#             # Flatten the lists (already flattened in the above step)
#             print(
#                 f"Flattened to {len(all_interpolated_points)} total points and {len(all_interpolated_speeds)} total speeds"
#             )

#             # Calculate average speed differences for overlapping segments
#             point_speed_map = {}
#             for pt, spd in zip(all_interpolated_points, all_interpolated_speeds):
#                 coord = (pt.x, pt.y)
#                 if coord not in point_speed_map:
#                     point_speed_map[coord] = []
#                 point_speed_map[coord].append(spd)
#             print(
#                 f"Calculated average speed differences for {len(point_speed_map)} points"
#             )

#             print("Calculating averaged points and speeds...")
#             averaged_points = []
#             averaged_speeds = []
#             for coord, speeds in point_speed_map.items():
#                 # Filter out 0 values
#                 valid_speeds = [spd for spd in speeds if spd != 0]
#                 print(f"Valid speeds: {valid_speeds}")
#                 if valid_speeds:
#                     averaged_points.append(Point(coord))
#                     averaged_speeds.append(sum(valid_speeds) / len(valid_speeds))
#                     print(
#                         f"Averaged to {len(averaged_points)} points with corresponding speeds"
#                     )

#             # Create GeoJSON features
#             if not averaged_points:
#                 print("Not enough data points to create LineString features")
#                 print(f"Point-speed map: {point_speed_map}")
#                 print(f"Averaged points: {averaged_points}")
#                 print(f"Averaged speeds: {averaged_speeds}")
#                 return JsonResponse(
#                     {"detail": "Not enough data points to create LineString features"},
#                     status=400,
#                 )

#             line = LineString([(pt.x, pt.y) for pt in averaged_points])
#             feature = geojson.Feature(
#                 geometry=line, properties={"average_speed_differences": averaged_speeds}
#             )

#             feature_collection = geojson.FeatureCollection([feature])
#             print("Successfully created GeoJSON feature collection")
#             return JsonResponse(feature_collection, safe=False)

#         # Create GeoJSON features for each trip
#         features = []
#         for trip in segmented_trips:
#             coordinates = [(record.longitude, record.latitude) for record in trip]
#             speed_differences = [record.speed_difference for record in trip]

#             if len(coordinates) < 2:
#                 continue  # Skip trips with not enough data points

#             line = LineString(coordinates)
#             feature = geojson.Feature(
#                 geometry=line, properties={"speed_differences": speed_differences}
#             )
#             features.append(feature)

#         if not features:
#             return JsonResponse(
#                 {"detail": "Not enough data points to create LineString features"},
#                 status=400,
#             )

#         feature_collection = geojson.FeatureCollection(features)
#         return JsonResponse(feature_collection, safe=False)

#     except Exception as e:
#         print(f"Error occurred: {str(e)}")
#         return JsonResponse({"detail": str(e)}, status=500)
