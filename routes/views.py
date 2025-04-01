import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from routes.helper import calculate_route_mapbox, generate_daily_logs
from routes.validators import PositionData


driver_info = {
    "name": "John Doe",
    "carrier": "ABC Trucking, 123 Freight Lane, Los Angeles, CA 90001",
    "truck_number": "4567"
}

@csrf_exempt
def calculate_route(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            PositionData(**data)
            route_data = calculate_route_mapbox(data)
            print('>>>>>>>>>>>> logs code 1')
            logs = generate_daily_logs(route_data, driver_info, "2025-03-24")
            print('>>>>>>>>>>>> logs code 2' )
            return JsonResponse({"route": route_data, "logs": logs})
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except ValidationError as e:
            return JsonResponse({'error': json.dumps(e.json())}, status=400)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        except TypeError as e:
            return JsonResponse({'error': str(e)}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
