# Function to parse the data into multiple trips
from shapely import LineString, Point


def segment_trips(speed_records, time_threshold=30):
    trips = []
    current_trip = []

    for record in speed_records:
        if not current_trip:
            current_trip.append(record)
        else:
            time_diff = record.timestamp - current_trip[-1].timestamp
            if time_diff.total_seconds() / 60 > time_threshold:
                trips.append(current_trip)
                current_trip = [record]
            else:
                current_trip.append(record)

    if current_trip:
        trips.append(current_trip)

    return trips


def interpolate_speed_differences(trip, interval=100):
    line = LineString([(record.longitude, record.latitude) for record in trip])
    distances = [line.project(Point(record.longitude, record.latitude)) for record in trip]
    speed_differences = [record.speed_difference for record in trip]

    # Interpolating speed differences at regular intervals
    total_length = line.length
    num_points = int(total_length // interval)
    interpolated_points = [line.interpolate(distance) for distance in range(0, int(total_length), interval)]
    interpolated_speeds = [None] * len(interpolated_points)

    for i in range(len(interpolated_points)):
        for j in range(len(distances) - 1):
            if distances[j] <= line.project(interpolated_points[i]) <= distances[j + 1]:
                interpolated_speeds[i] = (
                                                 speed_differences[j] + speed_differences[j + 1]
                                         ) / 2 if speed_differences[j] != 0 and speed_differences[j + 1] != 0 else None
                break

    # Filter out None values (which represent ignored 0 values)
    interpolated_points = [pt for pt, spd in zip(interpolated_points, interpolated_speeds) if spd is not None]
    interpolated_speeds = [spd for spd in interpolated_speeds if spd is not None]

    return interpolated_points, interpolated_speeds
