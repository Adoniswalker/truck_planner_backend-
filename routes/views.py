import requests
from django.http import JsonResponse
import os

def calculate_route(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        origin = data.get('origin')
        waypoints = data.get('waypoints')
        destination = data.get('destination')
        api_key = os.environ.get('GOOGLE_MAPS_API_KEY')

        if not all([origin, waypoints, destination, api_key]):
            return JsonResponse({'error': 'Missing parameters or API key'}, status=400)

        waypoint_string = '|'.join([f"{waypoint['lat']},{waypoint['lng']}" for waypoint in waypoints])

        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin['lat']},{origin['lng']}&destination={destination['lat']},{destination['lng']}&waypoints={waypoint_string}&key={api_key}"

        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return JsonResponse(response.json())
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)