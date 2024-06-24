from ninja import NinjaAPI
import httpx
from shapely.geometry import Point, LineString

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

    # # If the nearest road has a maxspeed tag, return the speed limit as a string.
    # if nearest_way and 'tags' in nearest_way and 'maxspeed' in nearest_way['tags']:
    #     return nearest_way['tags']['maxspeed']
    # return None


@api.get("/speed-limit")
async def get_speed_limit_endpoint(request, lat: float, lon: float):
    road_data = await get_nearest_road(lat, lon)
    speed_limit = get_speed_limit(road_data, lat, lon)

    if speed_limit:
        return {"speed_limit": speed_limit}
    else:
        return {"error": "No speed limit information found"}
