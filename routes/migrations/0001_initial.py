# Generated by Django 5.1.7 on 2025-03-24 14:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_location', models.CharField(max_length=100)),
                ('pickup_location', models.CharField(max_length=100)),
                ('dropoff_location', models.CharField(max_length=100)),
                ('current_cycle_hours', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='LogEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('status', models.CharField(max_length=50)),
                ('hours', models.FloatField()),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='routes.trip')),
            ],
        ),
    ]
