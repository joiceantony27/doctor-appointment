#!/usr/bin/env python
"""
Script to create initial specializations for the Doctor Appointment System
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctor_appointment.settings')
django.setup()

from appointments.models import Specialization

def create_specializations():
    """Create initial specializations if they don't exist"""
    
    specializations_data = [
        {
            'name': 'Cardiology',
            'description': 'Heart and cardiovascular system specialists',
            'icon': 'fa-heartbeat'
        },
        {
            'name': 'Dermatology',
            'description': 'Skin, hair, and nail specialists',
            'icon': 'fa-user-md'
        },
        {
            'name': 'Neurology',
            'description': 'Brain and nervous system specialists',
            'icon': 'fa-brain'
        },
        {
            'name': 'Orthopedics',
            'description': 'Bone, joint, and muscle specialists',
            'icon': 'fa-bone'
        },
        {
            'name': 'Pediatrics',
            'description': 'Children and adolescent healthcare',
            'icon': 'fa-child'
        },
        {
            'name': 'Gynecology',
            'description': 'Women\'s reproductive health specialists',
            'icon': 'fa-female'
        },
        {
            'name': 'Ophthalmology',
            'description': 'Eye and vision specialists',
            'icon': 'fa-eye'
        },
        {
            'name': 'ENT (Otolaryngology)',
            'description': 'Ear, nose, and throat specialists',
            'icon': 'fa-head-side-mask'
        },
        {
            'name': 'Psychiatry',
            'description': 'Mental health and behavioral specialists',
            'icon': 'fa-brain'
        },
        {
            'name': 'General Medicine',
            'description': 'Primary care and general health',
            'icon': 'fa-stethoscope'
        },
        {
            'name': 'Gastroenterology',
            'description': 'Digestive system specialists',
            'icon': 'fa-stomach'
        },
        {
            'name': 'Pulmonology',
            'description': 'Lung and respiratory system specialists',
            'icon': 'fa-lungs'
        },
        {
            'name': 'Endocrinology',
            'description': 'Hormone and gland specialists',
            'icon': 'fa-dna'
        },
        {
            'name': 'Urology',
            'description': 'Urinary system and male reproductive health',
            'icon': 'fa-kidneys'
        },
        {
            'name': 'Oncology',
            'description': 'Cancer treatment specialists',
            'icon': 'fa-ribbon'
        },
        {
            'name': 'Radiology',
            'description': 'Medical imaging specialists',
            'icon': 'fa-x-ray'
        },
        {
            'name': 'Anesthesiology',
            'description': 'Anesthesia and pain management',
            'icon': 'fa-syringe'
        },
        {
            'name': 'Emergency Medicine',
            'description': 'Emergency and critical care',
            'icon': 'fa-ambulance'
        },
        {
            'name': 'Dentistry',
            'description': 'Oral and dental health',
            'icon': 'fa-tooth'
        },
        {
            'name': 'Physiotherapy',
            'description': 'Physical rehabilitation and therapy',
            'icon': 'fa-walking'
        }
    ]
    
    created_count = 0
    
    for spec_data in specializations_data:
        specialization, created = Specialization.objects.get_or_create(
            name=spec_data['name'],
            defaults={
                'description': spec_data['description'],
                'icon': spec_data['icon']
            }
        )
        
        if created:
            created_count += 1
            print(f"✓ Created specialization: {specialization.name}")
        else:
            print(f"- Specialization already exists: {specialization.name}")
    
    print(f"\nSummary: {created_count} new specializations created")
    print(f"Total specializations in database: {Specialization.objects.count()}")

if __name__ == '__main__':
    create_specializations()
