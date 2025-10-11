#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctor_appointment.settings')
django.setup()

from appointments.models import Specialization

def populate_specializations():
    """Populate the database with common medical specializations"""
    
    specializations = [
        {
            'name': 'Cardiology',
            'description': 'Heart and cardiovascular system disorders',
            'icon': 'fa-heartbeat'
        },
        {
            'name': 'Dermatology',
            'description': 'Skin, hair, and nail conditions',
            'icon': 'fa-user-md'
        },
        {
            'name': 'Neurology',
            'description': 'Nervous system and brain disorders',
            'icon': 'fa-brain'
        },
        {
            'name': 'Orthopedics',
            'description': 'Bones, joints, and musculoskeletal system',
            'icon': 'fa-bone'
        },
        {
            'name': 'Pediatrics',
            'description': 'Medical care for infants, children, and adolescents',
            'icon': 'fa-baby'
        },
        {
            'name': 'Gynecology',
            'description': 'Female reproductive system health',
            'icon': 'fa-female'
        },
        {
            'name': 'Ophthalmology',
            'description': 'Eye and vision care',
            'icon': 'fa-eye'
        },
        {
            'name': 'Psychiatry',
            'description': 'Mental health and behavioral disorders',
            'icon': 'fa-head-side-virus'
        },
        {
            'name': 'General Medicine',
            'description': 'Primary healthcare and general medical conditions',
            'icon': 'fa-stethoscope'
        },
        {
            'name': 'Gastroenterology',
            'description': 'Digestive system disorders',
            'icon': 'fa-pills'
        },
        {
            'name': 'Pulmonology',
            'description': 'Respiratory system and lung disorders',
            'icon': 'fa-lungs'
        },
        {
            'name': 'Endocrinology',
            'description': 'Hormonal and metabolic disorders',
            'icon': 'fa-dna'
        },
        {
            'name': 'Urology',
            'description': 'Urinary tract and male reproductive system',
            'icon': 'fa-male'
        },
        {
            'name': 'Oncology',
            'description': 'Cancer diagnosis and treatment',
            'icon': 'fa-ribbon'
        },
        {
            'name': 'Radiology',
            'description': 'Medical imaging and diagnostic procedures',
            'icon': 'fa-x-ray'
        }
    ]
    
    created_count = 0
    for spec_data in specializations:
        specialization, created = Specialization.objects.get_or_create(
            name=spec_data['name'],
            defaults={
                'description': spec_data['description'],
                'icon': spec_data['icon']
            }
        )
        if created:
            created_count += 1
            print(f"Created specialization: {specialization.name}")
        else:
            print(f"Specialization already exists: {specialization.name}")
    
    print(f"\nTotal specializations created: {created_count}")
    print(f"Total specializations in database: {Specialization.objects.count()}")

if __name__ == '__main__':
    populate_specializations()
