import json
import os
import requests
from datetime import datetime, timedelta

MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')


def calculate_route_mapbox(request_data):
    """
    Calculate route using Mapbox Directions API with string coordinate inputs
    """

    def parse_coords(coord_str):
        try:
            lng, lat = map(float, coord_str.split(','))
            return [lng, lat]
        except ValueError as e:
            raise Exception(f"Invalid coordinate format: {coord_str} - {str(e)}")

    try:
        current_coords = parse_coords(request_data['currentLocation'])
        pickup_coords = parse_coords(request_data['pickupLocation'])
        dropoff_coords = parse_coords(request_data['dropoffLocation'])
    except KeyError as e:
        raise Exception(f"Missing required field: {str(e)}")

    # Adjust for same pickup/dropoff
    if pickup_coords == dropoff_coords:
        coordinates_str = f"{current_coords[0]},{current_coords[1]};{pickup_coords[0]},{pickup_coords[1]}"
    else:
        coordinates_str = f"{current_coords[0]},{current_coords[1]};{pickup_coords[0]},{pickup_coords[1]};{dropoff_coords[0]},{dropoff_coords[1]}"

    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates_str}"
    params = {
        "access_token": MAPBOX_ACCESS_TOKEN,
        "geometries": "geojson",
        "steps": "true",
        "overview": "full"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Mapbox API error: {response.status_code} - {response.text}")

    data = response.json()

    if "routes" not in data or not data["routes"]:
        raise Exception(f"No routes found in response: {json.dumps(data)}")

    route = data["routes"][0]
    if "geometry" not in route:
        raise Exception(f"Geometry not found in route: {json.dumps(route)}")

    total_distance = route["distance"] * 0.000621371  # Convert meters to miles
    total_duration = route["duration"] / 3600  # Convert seconds to hours
    route_coordinates = route["geometry"]["coordinates"]  # Use route-level geometry

    # Process segments
    segments = []
    legs = route.get("legs", [])

    if len(legs) == 1:  # Single leg due to identical pickup/dropoff
        leg = legs[0]
        segments.append({
            'start': route_coordinates[0],
            'end': route_coordinates[-1],
            'distance': leg["distance"] * 0.000621371,
            'duration': leg["duration"] / 3600
        })
    else:
        # For multiple legs (when pickup and dropoff differ)
        for i, leg in enumerate(legs):
            # Since leg["geometry"] isn’t available, approximate using route coordinates
            start_idx = 0 if i == 0 else len(route_coordinates) // 2
            end_idx = len(route_coordinates) if i == len(legs) - 1 else len(route_coordinates) // 2
            coordinates = route_coordinates[start_idx:end_idx + 1]
            segments.append({
                'start': coordinates[0],
                'end': coordinates[-1],
                'distance': leg["distance"] * 0.000621371,
                'duration': leg["duration"] / 3600
            })

    # Add fuel stops every 1000 miles
    fuel_stops = []
    remaining_distance = total_distance
    while remaining_distance > 1000:
        fuel_stops.append({
            'mile_marker': total_distance - remaining_distance,
            'duration': 0.5
        })
        remaining_distance -= 1000

    stops = [
                {'type': 'pickup', 'location': pickup_coords, 'duration': 1.0},
                {'type': 'dropoff', 'location': dropoff_coords, 'duration': 1.0}
            ] + fuel_stops

    return {
        'total_distance': total_distance,
        'total_duration': total_duration,
        'segments': segments,
        'stops': stops,
        'geometry': route["geometry"]
    }


def generate_eld_logs(route_data):
    """
    Generate ELD logs based on route data
    """
    logs = []
    remaining_hours = 70  # 70 hours in 8 days rule
    current_day = datetime.now()
    total_duration = route_data['total_duration']
    segments = route_data['segments']
    stops = route_data['stops']

    hours_driven = 0
    current_log = {
        'date': current_day.date(),
        'entries': [
            {'status': 'Off Duty', 'hours': 0},
            {'status': 'Driving', 'hours': 0},
            {'status': 'On Duty', 'hours': 0}
        ]
    }

    for segment in segments:
        driving_hours = segment['duration']
        while driving_hours > 0:
            available_hours = min(11 - hours_driven, remaining_hours)
            hours_to_drive = min(driving_hours, available_hours)

            current_log['entries'][1]['hours'] += hours_to_drive  # Driving time
            hours_driven += hours_to_drive
            remaining_hours -= hours_to_drive
            driving_hours -= hours_to_drive

            if hours_driven >= 11 or remaining_hours <= 0:
                logs.append(current_log)
                current_day += timedelta(days=1)
                current_log = {
                    'date': current_day.date(),
                    'entries': [
                        {'status': 'Off Duty', 'hours': 10},  # Mandatory break
                        {'status': 'Driving', 'hours': 0},
                        {'status': 'On Duty', 'hours': 0}
                    ]
                }
                hours_driven = 0
                if remaining_hours <= 0:
                    remaining_hours = 70  # Reset after 8 days

    for stop in stops:
        current_log['entries'][2]['hours'] += stop['duration']  # On Duty time

    logs.append(current_log)
    return logs