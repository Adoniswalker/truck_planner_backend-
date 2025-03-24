from django.db import models


class Trip(models.Model):
    current_location = models.CharField(max_length=100)
    pickup_location = models.CharField(max_length=100)
    dropoff_location = models.CharField(max_length=100)
    current_cycle_hours = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

class LogEntry(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=50)  # Off Duty, Driving, On Duty
    hours = models.FloatField()
