from urllib.parse import urlencode

import requests
from django.http import JsonResponse
import os

from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from routes.validators import PositionData


@csrf_exempt
def calculate_route(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            PositionData(**data)
            api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
            params = {
                'origin':data.get('currentLocation'),
                'destination': data.get('dropoffLocation'),
                'key': api_key
            }
            print(f"API Key: {api_key}")
            # currentLocation =
            # pickupLocation = data.get('pickupLocation')
            # dropoffLocation = data.get('dropoffLocation')

            # print(api_key)
            url = f"https://maps.googleapis.com/maps/api/directions/json?{urlencode(params)}"
            print(url)
            response = requests.get(url)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return JsonResponse(response.json())
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except ValidationError as e:
            # print(e.errors())
            # import pdb;pdb.set_trace()
            return JsonResponse({'error': json.dumps(e.json())}, status=400)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        except TypeError as e:
            return JsonResponse({'error': str(e)}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)