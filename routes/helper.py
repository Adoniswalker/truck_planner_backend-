import json
import os
import requests
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
import io

MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')


# Mock calculate_route_mapbox for testing
def calculate_route_mapbox(request_data):
    """Mock function for testing without API calls"""

    def parse_coords(coord_str):
        lng, lat = map(float, coord_str.split(','))
        return [lng, lat]

    current_coords = parse_coords(request_data['currentLocation'])
    pickup_coords = parse_coords(request_data['pickupLocation'])
    dropoff_coords = parse_coords(request_data['dropoffLocation'])

    total_distance = 1200  # miles
    total_duration = 20  # hours
    segments = [
        {'start': current_coords, 'end': pickup_coords, 'distance': 600, 'duration': 10},
        {'start': pickup_coords, 'end': dropoff_coords, 'distance': 600, 'duration': 10}
    ]
    stops = [
        {'type': 'pickup', 'location': pickup_coords, 'distance': 600, 'duration': 1.0},  # Pickup at 600 miles
        {'type': 'fuel', 'mile_marker': 1000, 'duration': 0.5},  # Fuel at 1000 miles
        {'type': 'dropoff', 'location': dropoff_coords, 'distance': 1200, 'duration': 1.0}  # Dropoff at 1200 miles
    ]
    return {
        'total_distance': total_distance,
        'total_duration': total_duration,
        'segments': segments,
        'stops': stops,
        'geometry': {'coordinates': [current_coords, pickup_coords, dropoff_coords]}
    }


# Draw duty grid with 12, 1, 2, ..., 11, 12 labels
def draw_duty_grid(duty_statuses):
    """Draw duty status grid using matplotlib"""
    fig, ax = plt.subplots(figsize=(10, 2))
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 4)
    ax.set_yticks([0.5, 1.5, 2.5, 3.5])
    ax.set_yticklabels(["On Duty Not Dr", "Driving", "Sleeper Berth", "Off Duty"])

    ax.set_xticks(range(25))
    xticklabels = [str((h % 12) or 12) for h in range(25)]
    ax.set_xticklabels(xticklabels)

    ax.grid(True, which="both", linestyle="--", alpha=0.5)

    for status, periods in duty_statuses.items():
        y = {"Off Duty": 3, "Sleeper Berth": 2, "Driving": 1, "On Duty Not Dr": 0}[status]
        for start, end in periods:
            ax.plot([start, end], [y, y], lw=8, solid_capstyle="butt",
                    color={"Off Duty": "gray", "Sleeper Berth": "blue", "Driving": "green", "On Duty Not Dr": "orange"}[
                        status])

    ax.set_title("Duty Status Grid")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


# Updated generate_daily_logs
def generate_daily_logs(route_data, driver_info, start_date):
    """Generate daily log data based on route data with HOS limits"""
    total_distance = route_data['total_distance']
    segments = route_data['segments']
    stops = route_data['stops'].copy()

    logs = []
    current_time = datetime.strptime(start_date, "%Y-%m-%d")
    distance_covered = 0
    day = 1
    odometer = 150000
    total_on_duty_hours = 0
    eight_day_start = current_time

    while distance_covered < total_distance:
        duty_statuses = {"Off Duty": [], "Sleeper Berth": [], "Driving": [], "On Duty Not Dr": []}
        day_start = current_time.replace(hour=0, minute=0, second=0)
        driving_hours = 0
        on_duty_hours = 0

        # Check 70-hour limit
        if total_on_duty_hours >= 70:
            print(f"Reached 70-hour limit on Day {day}. Stopping logs.")
            break

        # Off Duty from midnight to 8 AM
        duty_statuses["Off Duty"].append((0, 8))
        current_time = day_start + timedelta(hours=8)

        # Pre-trip inspection (0.5 hours)
        if total_on_duty_hours + on_duty_hours + 0.5 <= 70:
            duty_statuses["On Duty Not Dr"].append((8, 8.5))
            current_time += timedelta(minutes=30)
            on_duty_hours += 0.5

        # Driving and stops
        segment_index = 0
        while segment_index < len(segments) and distance_covered < total_distance:
            segment = segments[segment_index]
            prior_distance = sum(s['distance'] for s in segments[:segment_index]) if segment_index > 0 else 0
            remaining_segment_distance = segment['distance'] - (distance_covered - prior_distance)

            if remaining_segment_distance <= 0:
                segment_index += 1
                continue

            speed = segment['distance'] / segment['duration']  # miles per hour
            duration = min(remaining_segment_distance / speed, 11 - driving_hours, 14 - on_duty_hours,
                           70 - total_on_duty_hours - on_duty_hours)
            if duration > 0:
                start_hour = (current_time - day_start).total_seconds() / 3600
                end_hour = start_hour + duration
                if end_hour <= 24:
                    duty_statuses["Driving"].append((start_hour, end_hour))
                    distance_covered += duration * speed
                    driving_hours += duration
                    on_duty_hours += duration
                    current_time += timedelta(hours=duration)

                    # Process stops based on distance covered
                    for stop in stops[:]:
                        stop_distance = stop.get('distance', stop.get('mile_marker', total_distance))
                        if stop_distance <= distance_covered:
                            stop_start = (current_time - day_start).total_seconds() / 3600
                            stop_end = stop_start + stop['duration']
                            if stop_end <= 24 and total_on_duty_hours + on_duty_hours + stop['duration'] <= 70:
                                duty_statuses["On Duty Not Dr"].append((stop_start, stop_end))
                                current_time += timedelta(hours=stop['duration'])
                                on_duty_hours += stop['duration']
                                stops.remove(stop)
                else:
                    break
            segment_index += 1

        # Sleeper Berth (10-hour reset)
        sleeper_start = (current_time - day_start).total_seconds() / 3600
        if sleeper_start < 24:
            sleeper_end = min(sleeper_start + 10, 24)
            duty_statuses["Sleeper Berth"].append((sleeper_start, sleeper_end))
            if sleeper_end < 24:
                duty_statuses["Off Duty"].append((sleeper_end, 24))
            current_time = day_start + timedelta(days=1)

        # Update total on-duty hours
        total_on_duty_hours += on_duty_hours

        # Calculate miles driven this day
        prior_distance = sum(log["Total Miles Driven"] for log in logs) if logs else 0
        miles_this_day = int(distance_covered - prior_distance)

        log = {
            "Day": f"Day {day} - {day_start.strftime('%Y-%m-%d')}",
            "Driver": driver_info["name"],
            "Carrier": driver_info["carrier"],
            "Truck Number": driver_info["truck_number"],
            "Starting Odometer": odometer,
            "Ending Odometer": odometer + miles_this_day,
            "Total Miles Driven": miles_this_day,
            "Duty Statuses": duty_statuses,
            "Remarks": "Fueled at mile 1000" if any(
                s['type'] == 'fuel' and s.get('mile_marker', float('inf')) <= distance_covered for s in
                route_data['stops']) else "",
            "On Duty Hours": on_duty_hours
        }
        logs.append(log)

        odometer = log["Ending Odometer"]
        day += 1

        # Check 8-day cycle
        if day > 8:
            total_on_duty_hours -= logs[day - 9]["On Duty Hours"] if day - 9 >= 0 else 0

    return logs


def create_pdf(logs, filename="driver_log_sheets.pdf"):
    """Create PDF with log sheets"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    for log in logs:
        story.append(Paragraph(f"{log['Day']}", styles['Heading1']))
        story.append(Paragraph(f"Driver: {log['Driver']}", styles['Normal']))
        story.append(Paragraph(f"Carrier: {log['Carrier']}", styles['Normal']))
        story.append(Paragraph(f"Truck Number: {log['Truck Number']}", styles['Normal']))
        story.append(Paragraph(f"Starting Odometer: {log['Starting Odometer']}", styles['Normal']))
        story.append(Paragraph(f"Ending Odometer: {log['Ending Odometer']}", styles['Normal']))
        story.append(Paragraph(f"Total Miles Driven: {log['Total Miles Driven']}", styles['Normal']))
        story.append(Paragraph(f"On Duty Hours: {log['On Duty Hours']}", styles['Normal']))
        story.append(Spacer(1, 12))

        grid_image = draw_duty_grid(log["Duty Statuses"])
        story.append(Image(grid_image, width=500, height=100))
        story.append(Spacer(1, 12))

        story.append(Paragraph(f"Remarks: {log['Remarks']}", styles['Normal']))
        story.append(Spacer(1, 36))

    doc.build(story)


# Example usage
request_data = {
    "currentLocation": "-121.53449957986606,37.72174814332759",
    "pickupLocation": "-118.30225731779183,34.08637121805918",
    "dropoffLocation": "-77.16697187740498,39.075873963992436"
}

driver_info = {
    "name": "John Doe",
    "carrier": "ABC Trucking, 123 Freight Lane, Los Angeles, CA 90001",
    "truck_number": "4567"
}

if __name__ == "__main__":
    route_data = calculate_route_mapbox(request_data)
    logs = generate_daily_logs(route_data, driver_info, "2025-03-24")
    for log in logs:
        print(f"{log['Day']}: {log['Duty Statuses']}")
        print(f"Total Miles Driven: {log['Total Miles Driven']}, On Duty Hours: {log['On Duty Hours']}")
    total_logged_distance = sum(log["Total Miles Driven"] for log in logs)
    total_on_duty_hours = sum(log["On Duty Hours"] for log in logs)
    print(f"Total Distance Logged: {total_logged_distance} miles vs Expected: {route_data['total_distance']} miles")
    print(f"Total On Duty Hours: {total_on_duty_hours} (Limit: 70 hours / 8 days)")
    create_pdf(logs)