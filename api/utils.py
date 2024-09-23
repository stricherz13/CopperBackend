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
    if not trip:
        print("Trip is empty")
        return [], []

    line = LineString([(record.longitude, record.latitude) for record in trip])
    distances = [line.project(Point(record.longitude, record.latitude)) for record in trip]
    speed_differences = [record.speed_difference for record in trip]

    print(f"LineString length: {line.length}")
    print(f"Distances: {distances}")
    print(f"Speed differences: {speed_differences}")

    # Interpolating speed differences at regular intervals
    total_length = line.length
    num_points = int(total_length // interval)
    interpolated_points = [line.interpolate(distance) for distance in range(0, int(total_length), interval)]
    interpolated_speeds = [None] * len(interpolated_points)

    print(f"Total length: {total_length}")
    print(f"Number of interpolated points: {len(interpolated_points)}")

    for i in range(len(interpolated_points)):
        interpolated_point_distance = line.project(interpolated_points[i])
        for j in range(len(distances) - 1):
            if distances[j] <= interpolated_point_distance <= distances[j + 1]:
                if speed_differences[j] != 0 and speed_differences[j + 1] != 0:
                    interpolated_speeds[i] = (speed_differences[j] + speed_differences[j + 1]) / 2
                print(f"Interpolated point {i} at distance {interpolated_point_distance}: speed = {interpolated_speeds[i]}")
                break

    # Filter out None values (which represent ignored 0 values)
    interpolated_points = [pt for pt, spd in zip(interpolated_points, interpolated_speeds) if spd is not None]
    interpolated_speeds = [spd for spd in interpolated_speeds if spd is not None]

    print(f"Final interpolated points: {len(interpolated_points)}")
    print(f"Final interpolated speeds: {len(interpolated_speeds)}")

    return interpolated_points, interpolated_speeds
