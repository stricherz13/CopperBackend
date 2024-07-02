from datetime import timedelta

# Function to parse the data into multiple trips
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
