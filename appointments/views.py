from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.template.loader import render_to_string
from django.conf import settings
from .models import User, Doctor, Appointment, Review, Schedule, Payment, Specialization, WorkingHours, TimeSlot, SavedDoctor, Patient, Notification, Note, DoctorPatientNote, BlockedTimeSlot
from .forms import UserRegistrationForm, DoctorRegistrationForm, AppointmentForm, ReviewForm, DoctorProfileForm, AddDoctorForm
from decimal import Decimal
import json
import os
import stripe
import razorpay
from django.db.models import Avg, Count, Q, F, Sum
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.db.models import Q

def health_check(request):
    """Health check endpoint for Docker containers"""
    return JsonResponse({'status': 'healthy', 'timestamp': timezone.now().isoformat()})
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
import random
import string
from django.views.decorators.http import require_POST
from django.utils.html import strip_tags
from django.urls import reverse
from .decorators import doctor_required
import uuid
import logging
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import time
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from django.conf import settings
import json
from django.http import JsonResponse, HttpResponse
from datetime import datetime
import uuid

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

def is_admin(user):
    return user.user_type == 'admin'

def home(request):
    doctors = Doctor.objects.filter(is_available=True)[:6]
    return render(request, 'appointments/home.html', {'doctors': doctors})

def custom_logout(request):
    logout(request)
    return redirect('appointments:home')

def register(request):
    specializations = Specialization.objects.all()
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Create doctor profile if registering as doctor
            if user.user_type == 'doctor':
                # Get the selected specialization or create a default one if none exists
                specialization_id = request.POST.get('specialization')
                specialization = Specialization.objects.get(id=specialization_id) if specialization_id else Specialization.objects.create(
                    name="General Medicine",
                    description="General medical practice",
                    icon="fa-user-md"
                )
                
                doctor = Doctor.objects.create(
                    user=user,
                    specialization=specialization,
                    experience=request.POST.get('experience', 0),
                    education="",  # Empty by default
                    bio="",  # Empty by default
                    consultation_fee=Decimal(request.POST.get('consultation_fee', '0.00')),
                    is_available=True,
                    available_days="Monday,Tuesday,Wednesday,Thursday,Friday",
                    available_hours="09:00-12:00,14:00-17:00"
                )
                messages.success(request, 'Doctor account created successfully! Please complete your profile.')
                return redirect('appointments:edit_doctor_profile', doctor_id=doctor.id)
            elif user.user_type == 'admin':
                messages.success(request, 'Admin account created successfully!')
            else:
                messages.success(request, 'Patient account created successfully!')
            
            # Authenticate the user after registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('appointments:home')
            else:
                messages.error(request, 'Registration successful, but login failed. Please log in manually.')
                return redirect('appointments:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegistrationForm()
    return render(request, 'appointments/register.html', {'form': form, 'specializations': specializations})

@login_required
@user_passes_test(is_admin)
def add_doctor(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        doctor_form = DoctorRegistrationForm(request.POST, request.FILES)
        if user_form.is_valid() and doctor_form.is_valid():
            user = user_form.save(commit=False)
            user.user_type = 'doctor'
            user.save()
            
            doctor = doctor_form.save(commit=False)
            doctor.user = user
            if 'profile_picture' in request.FILES:
                doctor.profile_picture = request.FILES['profile_picture']
            doctor.save()
            
            messages.success(request, 'Doctor added successfully.')
            return redirect('appointments:admin_dashboard')
    else:
        user_form = UserRegistrationForm(initial={'user_type': 'doctor'})
        doctor_form = DoctorRegistrationForm()
    
    return render(request, 'appointments/add_doctor.html', {
        'user_form': user_form,
        'doctor_form': doctor_form
    })

@login_required
def doctor_list(request):
    specializations = Specialization.objects.all()
    doctors = Doctor.objects.filter(is_available=True)
    
    # Get filter parameters from request
    specialization = request.GET.get('specialization')
    location = request.GET.get('location')
    availability = request.GET.get('availability')
    rating = request.GET.get('rating')
    
    # Apply filters
    if specialization:
        doctors = doctors.filter(specialization_id=specialization)
    
    if location:
        doctors = doctors.filter(location__icontains=location)
    
    if availability:
        today = timezone.now().date()
        if availability == 'today':
            # Filter doctors who are available today
            doctors = doctors.filter(
                Q(available_days__contains=today.strftime('%A')) |
                Q(available_days__contains='Any Day')
            )
        elif availability == 'week':
            # Filter doctors who are available this week
            doctors = doctors.filter(
                Q(available_days__contains=today.strftime('%A')) |
                Q(available_days__contains=(today + timedelta(days=1)).strftime('%A')) |
                Q(available_days__contains=(today + timedelta(days=2)).strftime('%A')) |
                Q(available_days__contains=(today + timedelta(days=3)).strftime('%A')) |
                Q(available_days__contains=(today + timedelta(days=4)).strftime('%A')) |
                Q(available_days__contains=(today + timedelta(days=5)).strftime('%A')) |
                Q(available_days__contains=(today + timedelta(days=6)).strftime('%A')) |
                Q(available_days__contains='Any Day')
            )
    
    if rating:
        min_rating = int(rating)
        doctors = doctors.annotate(avg_rating=Avg('review__rating'))
        doctors = doctors.filter(avg_rating__gte=min_rating)
    
    # Order by average rating (highest first)
    doctors = doctors.annotate(avg_rating=Avg('review__rating'))
    doctors = doctors.order_by('-avg_rating', 'user__get_full_name')
    
    context = {
        'doctors': doctors,
        'specializations': specializations,
        'selected_specialization': specialization,
        'location': location,
        'availability': availability,
        'rating': rating
    }
    return render(request, 'appointments/doctors_list.html', context)

@login_required
def doctor_detail(request, doctor_id):
    """View doctor details"""
    doctor = get_object_or_404(Doctor.objects.select_related('user', 'specialization'), id=doctor_id)
    reviews = Review.objects.filter(doctor=doctor).select_related('patient')
    
    # Calculate average rating
    ratings = [review.rating for review in reviews if review.rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Get recent reviews (last 5)
    recent_reviews = reviews.order_by('-created_at')[:5]
    
    # Split education into a list
    education_list = [edu.strip() for edu in doctor.education.split('\n') if edu.strip()] if doctor.education else []
    
    # Get available days from doctor's working hours
    working_hours = WorkingHours.objects.filter(doctor=doctor, is_active=True).order_by('day_of_week', 'start_time')
    
    # Generate available days list from working hours
    available_days = []
    for wh in working_hours:
        day_name = wh.get_day_of_week_display()
        if day_name not in available_days:
            available_days.append(day_name)
    
    # If no working hours defined but doctor has available_days field, use that
    if not available_days and doctor.available_days:
        available_days = doctor.get_available_days_list()
    
    # Get available time slots
    time_slots = []
    
    # First try to get time slots from working hours
    if working_hours:
        for wh in working_hours:
            time_slots.append({
                'day': wh.get_day_of_week_display(),
                'start_time': wh.start_time.strftime('%I:%M %p'),
                'end_time': wh.end_time.strftime('%I:%M %p'),
                'appointment_duration': wh.appointment_duration
            })
    # Fallback to doctor.available_hours if working_hours is empty
    elif doctor.available_hours:
        for slot in doctor.available_hours.split(','):
            if '-' in slot:
                start_time, end_time = slot.split('-')
                time_slots.append({
                    'day': 'Flexible',
                    'start_time': start_time.strip(),
                    'end_time': end_time.strip(),
                    'appointment_duration': 30
                })
    
    # Check if doctor is saved by the user
    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedDoctor.objects.filter(user=request.user, doctor=doctor).exists()
    
    context = {
        'doctor': doctor,
        'education_list': education_list,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'recent_reviews': recent_reviews,
        'available_days': available_days,
        'time_slots': time_slots,
        'working_hours': working_hours,
        'is_saved': is_saved,
    }
    
    return render(request, 'appointments/doctor_detail.html', context)

@login_required
@require_POST
def save_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    saved_doctor, created = SavedDoctor.objects.get_or_create(
        user=request.user,
        doctor=doctor
    )
    
    if not created:
        saved_doctor.delete()
        is_saved = False
    else:
        is_saved = True
    
    return JsonResponse({'is_saved': is_saved})

@login_required
def book_appointment(request, doctor_id):
    """
    Book an appointment with a doctor.
    
    Creates an appointment with status 'pending' and redirects to patient dashboard.
    """
    if request.method == 'POST':
        doctor = get_object_or_404(Doctor, id=doctor_id)
        
        # Get form data
        date_str = request.POST.get('day') or request.POST.get('date')
        time_slot = request.POST.get('time_slot')
        appointment_type = request.POST.get('appointment_type', 'regular')
        is_video = request.POST.get('is_video_consultation', '') == 'on'
        note = request.POST.get('note', '')
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Validate data
        if not date_str or not time_slot:
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please select a date and time slot.'
                }, status=400)
            else:
                messages.error(request, 'Please select a date and time slot.')
                return redirect('appointments:doctor_detail', doctor_id=doctor_id)
            
        try:
            # Parse date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if the slot is already booked
            existing_appointment = Appointment.objects.filter(
                doctor=doctor,
                date=date_obj,
                time_slot=time_slot
            ).exists()
            
            if existing_appointment:
                error_message = 'This time slot has already been booked. Please select another time.'
                if is_ajax:
                    return JsonResponse({
                        'status': 'error',
                        'message': error_message
                    }, status=409)  # 409 Conflict
                else:
                    messages.error(request, error_message)
                    return redirect('appointments:doctor_detail', doctor_id=doctor_id)
            
            # Create appointment
            appointment = Appointment.objects.create(
                doctor=doctor,
                patient=request.user,
                date=date_obj,
                time_slot=time_slot,
                status='pending',
                response_status='pending',
                payment_status='pending',
                appointment_type=appointment_type,
                is_video_consultation=is_video,
                cancellation_reason=note  # Change from 'reason' to 'cancellation_reason'
            )
            
            # Create success message with appointment details
            success_message = f'Appointment request with Dr. {doctor.user.get_full_name()} on {appointment.date} at {appointment.time_slot} has been submitted successfully. Status: Pending approval.'
            
            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': success_message,
                    'appointment_id': appointment.id,
                    'redirect_url': f"{reverse('appointments:patient_dashboard')}?new_appointment={appointment.id}"
                })
            else:
                messages.success(request, success_message)
                # Add parameter to highlight the newly created appointment
                return redirect(f"{reverse('appointments:patient_dashboard')}?new_appointment={appointment.id}")
        
        except Exception as e:
            error_message = f'Failed to book appointment: {str(e)}'
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                }, status=500)
            else:
                messages.error(request, error_message)
                return redirect('appointments:doctor_detail', doctor_id=doctor_id)
    
    # If GET request, redirect to doctor detail page
    return redirect('appointments:doctor_detail', doctor_id=doctor_id)

@login_required
def get_available_slots(request, doctor_id, date):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    selected_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
    
    working_hours = doctor.workinghours_set.filter(
        day_of_week=selected_date.weekday(),
        is_active=True
    ).first()
    
    available_slots = []
    if working_hours:
        start_time = working_hours.start_time
        end_time = working_hours.end_time
        
        while start_time < end_time:
            is_booked = Appointment.objects.filter(
                doctor=doctor,
                date=selected_date,
                time_slot=start_time.strftime('%H:%M'),
                status__in=['accepted', 'scheduled']
            ).exists()
            
            if not is_booked:
                available_slots.append(start_time.strftime('%H:%M'))
            
            start_time = (timezone.datetime.combine(selected_date, start_time) + timezone.timedelta(hours=1)).time()
    
    return JsonResponse({'available_slots': available_slots})

@login_required
def approve_appointment(request, appointment_id):
    if not request.user.user_type == 'doctor':
        return redirect('appointments:home')
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if appointment.doctor.user != request.user:
        return redirect('appointments:doctor_dashboard')
    
    appointment.status = 'confirmed'
    appointment.save()
    
    # Send notification to patient
    send_notification(
        user=appointment.patient.user,
        message=f"Your appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.date} at {appointment.time_slot} has been confirmed."
    )
    
    return redirect('appointments:doctor_dashboard')

@login_required
def patient_dashboard(request):
    user = request.user
    today = date.today()
    
    # Fetch all appointments for count
    all_appointments = Appointment.objects.filter(patient=user)
    
    # Get the 6 most recent appointments for display
    recent_appointments = all_appointments.order_by('-created_at')[:6]
    
    # Fetch upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=user, 
        date__gte=today, 
        status__in=['accepted', 'pending', 'paid']
    ).order_by('date', 'time_slot')
    
    # Get all completed appointments
    completed_appointments = Appointment.objects.filter(
        patient=user,
        status='completed'
    ).order_by('-date')
    
    # Get doctor notes sent by this patient
    doctor_notes = DoctorPatientNote.objects.filter(patient=user)
    
    # Get personal notes from this patient
    patient_notes = Note.objects.filter(patient=user).order_by('-created_at')
    
    # Get list of all doctors for the note creation form
    doctors = Doctor.objects.all()
    
    # Get notifications
    notifications = Notification.objects.filter(recipient=user).order_by('-created_at')[:5]
    
    # Check if there's a newly created appointment to highlight
    new_appointment_id = request.GET.get('new_appointment')
    
    # Create a dictionary to store available times for each doctor
    doctors_available_times = {}
    for appointment in recent_appointments:
        # Get available time slots for this doctor on a future date
        # This is a simplified version - in a real app, you'd query for actual availability
        available_times = []
        start_time = datetime.strptime("09:00", "%H:%M")
        end_time = datetime.strptime("17:00", "%H:%M")
        
        # Generate time slots in 1-hour intervals
        current_time = start_time
        while current_time < end_time:
            next_time = current_time + timedelta(hours=1)
            time_slot = f"{current_time.strftime('%H:%M')}-{next_time.strftime('%H:%M')}"
            available_times.append(time_slot)
            current_time = next_time
        
        doctors_available_times[appointment.id] = available_times
    
    context = {
        'appointments': recent_appointments,
        'all_appointments_count': all_appointments.count(),
        'upcoming_appointments': upcoming_appointments,
        'completed_appointments': completed_appointments,
        'doctor_notes': doctor_notes,
        'patient_notes': patient_notes,
        'doctors': doctors,
        'today': today,
        'notifications': notifications,
        'doctors_available_times': doctors_available_times,
        'new_appointment_id': new_appointment_id,
    }
    
    return render(request, 'appointments/patient_dashboard.html', context)

@login_required
@doctor_required
def doctor_dashboard(request):
    doctor = request.user.doctor
    today = date.today()
    
    # Get appointments for today
    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        date=today,
        status__in=['scheduled', 'accepted', 'paid']
    ).order_by('time_slot')
    
    # Get pending appointment requests
    pending_appointments = Appointment.objects.filter(
        doctor=doctor, 
        status='pending'
    ).order_by('date', 'time_slot')
    
    # Get past completed appointments - include both 'completed' and 'accepted' statuses
    completed_appointments = Appointment.objects.filter(
        doctor=doctor,
        status__in=['completed', 'accepted']
    ).order_by('-date', '-time_slot')[:10]
    
    # Get doctor's working hours
    working_hours = WorkingHours.objects.filter(doctor=doctor)
    
    # Get patient notes sent to this doctor
    patient_notes = DoctorPatientNote.objects.filter(doctor=doctor)
    
    today_appointments_count = today_appointments.count()
    pending_appointments_count = pending_appointments.count()
    completed_appointments_count = Appointment.objects.filter(doctor=doctor, status__in=['completed', 'accepted']).count()
    
    context = {
        'today_appointments': today_appointments,
        'pending_appointments': pending_appointments,
        'completed_appointments': completed_appointments,
        'working_hours': working_hours,
        'today_appointments_count': today_appointments_count,
        'pending_appointments_count': pending_appointments_count,
        'completed_appointments_count': completed_appointments_count,
        'patient_notes': patient_notes,
    }
    
    return render(request, 'appointments/doctor_dashboard.html', context)

@login_required
@require_POST
def update_appointment_status(request, appointment_id):
    """
    Update the status of an appointment (confirm or reject)
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if the current user is the doctor for this appointment
    if appointment.doctor.user != request.user:
        messages.error(request, "You don't have permission to update this appointment.")
        return redirect('appointments:doctor_dashboard')
    
    status = request.POST.get('status')
    if status in ['confirmed', 'rejected']:
        appointment.status = status
        appointment.save()
        
        # Create notification for the patient
        Notification.objects.create(
            user=appointment.patient.user,
            type='appointment_status_updated',
            title='Appointment Status Updated',
            message=f'Your appointment with Dr. {appointment.doctor.user.get_full_name()} has been {status}.',
            related_appointment=appointment
        )
        
        messages.success(request, f'Appointment has been {status} successfully.')
    else:
        messages.error(request, 'Invalid status provided.')
    
    return redirect('appointments:doctor_dashboard')

@login_required
def admin_dashboard(request):
    """
    Admin dashboard view showing system statistics and management options.
    """
    # Check if user has admin access
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'user_type', None) == 'admin'):
        messages.error(request, 'You do not have permission to access the admin dashboard.')
        return redirect('appointments:home')
    
    # Get statistics
    total_users = User.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()
    pending_appointments = Appointment.objects.filter(status='pending').count()
    
    # Get recent appointments
    recent_appointments = Appointment.objects.select_related(
        'patient', 'doctor__user'
    ).order_by('-created_at')[:10]
    
    # Get all users
    users = User.objects.all().order_by('-date_joined')
    
    # Handle search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'recent_appointments': recent_appointments,
        'users': users,
        'search_query': search_query,
    }
    
    return render(request, 'appointments/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def edit_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if request.method == 'POST':
        # Update user information
        doctor.user.first_name = request.POST['name'].split()[0]
        doctor.user.last_name = ' '.join(request.POST['name'].split()[1:]) if len(request.POST['name'].split()) > 1 else ''
        doctor.user.email = request.POST['email']
        doctor.user.save()
        
        # Update doctor information
        doctor.specialization = request.POST['specialization']
        doctor.experience = request.POST['experience']
        doctor.consultation_fee = request.POST['consultation_fee']
        if 'image' in request.FILES:
            doctor.image = request.FILES['image']
        doctor.save()
        
        messages.success(request, 'Doctor information updated successfully!')
        return redirect('appointments:admin_dashboard')
    return redirect('appointments:admin_dashboard')

@login_required
@user_passes_test(is_admin)
def delete_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    doctor.user.delete()  # This will also delete the doctor due to CASCADE
    messages.success(request, 'Doctor deleted successfully!')
    return redirect('appointments:admin_dashboard')

@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.user_type = request.POST.get('user_type')
        user.is_active = request.POST.get('is_active') == 'on'
        user.save()
        
        messages.success(request, 'User updated successfully.')
        return redirect('appointments:admin_dashboard')
    
    return render(request, 'appointments/edit_user.html', {'user': user})

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@user_passes_test(is_admin)
def admin_cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, 'Appointment cancelled successfully!')
    return redirect('appointments:admin_dashboard')

@login_required
def add_review(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.patient = request.user
            review.doctor = doctor
            review.save()
            # Update doctor rating
            doctor.total_reviews += 1
            doctor.rating = (doctor.rating * (doctor.total_reviews - 1) + review.rating) / doctor.total_reviews
            doctor.save()
            messages.success(request, 'Review added successfully!')
            return redirect('appointments:doctor_detail', pk=doctor_id)
    else:
        form = ReviewForm()
    return render(request, 'appointments/add_review.html', {
        'form': form,
        'doctor': doctor
    })

@login_required
def edit_review(request, review_id):
    """
    Edit an existing review
    """
    review = get_object_or_404(Review, id=review_id, patient=request.user)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if not rating:
            return JsonResponse({'status': 'error', 'message': 'Rating is required'})
        
        review.rating = rating
        review.comment = comment
        review.save()
        
        # Update doctor's average rating
        review.doctor.update_rating()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Review updated successfully'
        })
    
    return render(request, 'appointments/edit_review.html', {'review': review})

@login_required
def delete_review(request, review_id):
    """
    Delete a review
    """
    review = get_object_or_404(Review, id=review_id, patient=request.user)
    
    if request.method == 'POST':
        doctor = review.doctor
        review.delete()
        
        # Update doctor's average rating
        doctor.update_rating()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Review deleted successfully'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def send_message(request, doctor_id):
    """
    Send a message to a doctor
    """
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    if request.method == 'POST':
        message = request.POST.get('message')
        
        if not message:
            return JsonResponse({'status': 'error', 'message': 'Message is required'})
        
        # Create message
        Message.objects.create(
            sender=request.user,
            recipient=doctor.user,
            content=message
        )
        
        # Create notification for doctor
        Notification.objects.create(
            user=doctor.user,
            type='new_message',
            title='New Message',
            message=f'You have a new message from {request.user.get_full_name()}'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Message sent successfully'
        })
    
    return render(request, 'appointments/send_message.html', {'doctor': doctor})

@login_required
def share_profile(request, doctor_id):
    """
    Share a doctor's profile
    """
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    # Generate share URL
    share_url = request.build_absolute_uri(
        reverse('appointments:doctor_detail', args=[doctor_id])
    )
    
    context = {
        'doctor': doctor,
        'share_url': share_url
    }
    
    return render(request, 'appointments/share_profile.html', context)

class CustomLoginView(LoginView):
    template_name = 'appointments/login.html'
    
    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_superuser or user.is_staff:
                return reverse_lazy('appointments:admin_dashboard')
            elif hasattr(user, 'doctor_profile'):
                return reverse_lazy('appointments:doctor_dashboard')
            else:
                return reverse_lazy('appointments:patient_dashboard')
        return reverse_lazy('appointments:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        if user.is_superuser or user.is_staff:
            return redirect('appointments:admin_dashboard')
        elif hasattr(user, 'doctor_profile'):
            return redirect('appointments:doctor_dashboard')
        return redirect('appointments:patient_dashboard')

from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
import random
import string

def forget_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        print(f"Processing email: {email}")  # Debug print
        try:
            user = User.objects.get(email=email)
            print(f"Found user: {user.username}")  # Debug print
            
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))
            print(f"Generated OTP: {otp}")  # Debug print
            request.session['reset_otp'] = otp
            request.session['reset_user_id'] = user.id
            
            # Send OTP to email
            subject = 'Password Reset OTP - Prescripto'
            message = f"Your OTP for password reset is: {otp}\nThis OTP will expire in 10 minutes.\n\nPlease keep this OTP confidential and do not share it with anyone."
            print(f"Email message: {message}")  # Debug print
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                print(f"Email sent to: {email}")  # Debug print
                messages.success(request, 'OTP has been sent to your registered email')
                return redirect('appointments:verify_otp')
            except Exception as e:
                print(f"Email error: {str(e)}")  # Debug print
                messages.error(request, f'Failed to send OTP: {str(e)}')
                return render(request, 'appointments/forget_password.html')
            
        except User.DoesNotExist:
            print(f"User not found for email: {email}")  # Debug print
            messages.error(request, 'Email not registered')
            
    return render(request, 'appointments/forget_password.html')

def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('reset_otp')
        
        if entered_otp == stored_otp:
            # Clear OTP from session
            del request.session['reset_otp']
            return redirect('appointments:reset_password')
        else:
            messages.error(request, 'Invalid OTP')
            
    return render(request, 'appointments/verify_otp.html')

def reset_password(request):
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'appointments/reset_password.html')
            
        try:
            user_id = request.session.get('reset_user_id')
            user = User.objects.get(id=user_id)
            user.set_password(password1)
            user.save()
            
            # Clear session
            del request.session['reset_user_id']
            
            messages.success(request, 'Password has been reset successfully')
            return redirect('appointments:login')
            
        except User.DoesNotExist:
            messages.error(request, 'Invalid user')
            
    return render(request, 'appointments/reset_password.html')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_doctor_profile(request, doctor_id=None):
    """Manage doctor profile (admin only)"""
    if doctor_id:
        doctor = get_object_or_404(Doctor, id=doctor_id)
    else:
        doctor = None
    
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, 'Doctor profile saved successfully')
            return redirect('appointments:doctor_list')
    else:
        form = DoctorProfileForm(instance=doctor)
    
    return render(request, 'appointments/manage_doctor_profile.html', {
        'form': form,
        'doctor': doctor,
        'is_new': doctor_id is None
    })

@login_required
def doctor_list(request):
    """List all doctors"""
    doctors = Doctor.objects.select_related('user', 'specialization').all()
    return render(request, 'appointments/doctor_list.html', {
        'doctors': doctors
    })

@login_required
def reject_appointment(request, appointment_id):
    if not request.user.user_type == 'doctor':
        return redirect('appointments:home')
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if appointment.doctor.user != request.user:
        return redirect('appointments:doctor_dashboard')
    
    appointment.status = 'cancelled'
    appointment.save()
    
    # Send notification to patient
    send_notification(
        user=appointment.patient.user,
        message=f"Your appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.date} at {appointment.time_slot} has been cancelled."
    )
    
    return redirect('appointments:doctor_dashboard')

@login_required
def edit_doctor_profile(request, doctor_id):
    try:
        doctor = Doctor.objects.get(id=doctor_id)
        if doctor.user != request.user:
            messages.error(request, 'You do not have permission to edit this profile.')
            return redirect('appointments:doctor_dashboard')
    except Doctor.DoesNotExist:
        messages.error(request, 'Doctor profile not found.')
        return redirect('appointments:doctor_dashboard')

    if request.method == 'POST':
        print("Processing POST request for doctor profile update")
        form = DoctorProfileForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            doctor = form.save(commit=False)
            
            # Handle profile picture explicitly
            if 'profile_picture' in request.FILES:
                profile_pic = request.FILES['profile_picture']
                print(f"Saving profile picture: {profile_pic.name}, size: {profile_pic.size} bytes")
                doctor.profile_picture = profile_pic
            
            doctor.save()
            
            # Make sure user data is also updated
            user = doctor.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('appointments:doctor_dashboard')
        else:
            print(f"Form validation errors: {form.errors}")
    else:
        form = DoctorProfileForm(instance=doctor)

    context = {
        'form': form,
        'doctor': doctor
    }
    return render(request, 'appointments/edit_doctor_profile.html', context)

@login_required
def register_doctor(request):
    if request.user.user_type != 'doctor':
        return redirect('appointments:home')

    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            doctor = form.save(commit=False)
            doctor.user = request.user
            doctor.save()
            messages.success(request, 'Doctor profile created successfully! Please complete your profile.')
            return redirect('appointments:edit_doctor_profile', doctor_id=doctor.id)
    else:
        form = DoctorRegistrationForm()

    context = {
        'form': form
    }
    return render(request, 'appointments/register_doctor.html', context)

@login_required
def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('appointments:login')

@login_required
def dashboard(request):
    """
    Redirect users to their appropriate dashboard based on their user type.
    """
    # Check user type and redirect accordingly
    if request.user.is_staff or request.user.is_superuser or getattr(request.user, 'user_type', None) == 'admin':
        return redirect('appointments:admin_dashboard')
    elif hasattr(request.user, 'doctor'):
        return redirect('appointments:doctor_dashboard')
    elif hasattr(request.user, 'patient'):
        return redirect('appointments:patient_dashboard')
    else:
        messages.warning(request, 'Unable to determine user type. Please contact support.')
        return redirect('appointments:home')

@login_required
def get_available_slots(request):
    """
    Get available appointment slots for a doctor on a specific date.
    
    Args:
        request: Django request object
        
    Returns:
        JsonResponse: Available time slots in JSON format
        
    Raises:
        ValidationError: If required parameters are missing or invalid
    """
    # Get query parameters
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    
    # Validate required parameters
    if not doctor_id or not date_str:
        return JsonResponse({
            'error': 'Both doctor_id and date are required'
        }, status=400)
    
    try:
        # Validate and parse date
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get doctor
        doctor = get_object_or_404(Doctor, id=doctor_id)
        
        # Get booked appointments for the doctor on that date
        booked_appointments = Appointment.objects.filter(
            doctor=doctor,
            date=date,
            status__in=['pending', 'confirmed']
        ).values_list('time_slot', flat=True)
        
        # Generate available time slots (7AM to 7PM)
        available_slots = []
        current_time = timezone.make_aware(datetime.combine(date, datetime.min.time()) + timedelta(hours=7))
        
        while current_time.hour < 19:  # 7PM
            time_str = current_time.strftime('%I:%M %p')
            
            # Check if slot is already booked
            if time_str not in booked_appointments:
                available_slots.append({
                    'time': time_str,
                    'is_available': True
                })
            else:
                available_slots.append({
                    'time': time_str,
                    'is_available': False
                })
            
            # Move to next hour
            current_time += timedelta(hours=1)
        
        return JsonResponse({
            'date': date_str,
            'doctor_id': doctor_id,
            'available_slots': available_slots
        })
        
    except ValueError:
        return JsonResponse({
            'error': 'Invalid date format. Please use YYYY-MM-DD'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

def about(request):
    """
    Display the about page
    """
    return render(request, 'appointments/about.html')

def contact(request):
    """
    Display and handle the contact form
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Send email to admin
        try:
            send_mail(
                f'Contact Form: {subject}',
                f'From: {name} ({email})\n\nMessage:\n{message}',
                email,
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent successfully!')
        except Exception as e:
            messages.error(request, 'Failed to send message. Please try again later.')
        
        return redirect('appointments:contact')
    
    return render(request, 'appointments/contact.html')

@login_required
def edit_patient_profile(request):
    if request.method == 'POST':
        # Get the current user
        user = request.user
        
        # Update user information
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        # Save the changes
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('appointments:patient_dashboard')
    
    return render(request, 'appointments/edit_patient_profile.html', {
        'user': request.user
    })

@login_required
def update_availability(request):
    """
    View for updating doctor's availability
    """
    if not hasattr(request.user, 'doctor'):
        return JsonResponse({
            'status': 'error',
            'message': 'Only doctors can update availability'
        }, status=403)
    
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)
    
    try:
        doctor = request.user.doctor
        
        # Get form data
        day_of_week = request.POST.get('day_of_week')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        appointment_duration = request.POST.get('appointment_duration')
        is_active = request.POST.get('is_active', 'true') == 'true'
        
        # Validate required fields
        if not all([day_of_week, start_time, end_time, appointment_duration]):
            return JsonResponse({
                'status': 'error',
                'message': 'All fields are required'
            }, status=400)
        
        try:
            day_of_week = int(day_of_week)
            appointment_duration = int(appointment_duration)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid day or duration value'
            }, status=400)
        
        # Convert time strings to datetime.time objects
        try:
            start_time = datetime.strptime(start_time, '%H:%M').time()
            end_time = datetime.strptime(end_time, '%H:%M').time()
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid time format'
            }, status=400)
        
        # Check if end time is after start time
        start_datetime = datetime.combine(datetime.today(), start_time)
        end_datetime = datetime.combine(datetime.today(), end_time)
        if end_datetime <= start_datetime:
            return JsonResponse({
                'status': 'error',
                'message': 'End time must be after start time'
            }, status=400)
        
        # Validate time slots for 30-minute interval compatibility
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        # Check if start time is aligned to 30-minute intervals (00 or 30 minutes)
        if start_minutes % 30 != 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Start time must be aligned to 30-minute intervals (e.g., 9:00, 9:30, 10:00)'
            }, status=400)
        
        # Check if end time is aligned to 30-minute intervals (00 or 30 minutes)
        if end_minutes % 30 != 0:
            return JsonResponse({
                'status': 'error',
                'message': 'End time must be aligned to 30-minute intervals (e.g., 9:00, 9:30, 10:00)'
            }, status=400)
        
        # Check if slot duration is sufficient for appointment duration
        duration_minutes = (end_datetime - start_datetime).total_seconds() / 60
        if duration_minutes < appointment_duration:
            return JsonResponse({
                'status': 'error',
                'message': 'Time slot duration must be at least equal to appointment duration'
            }, status=400)
        
        # Check for overlapping slots
        existing_slots = WorkingHours.objects.filter(
            doctor=doctor,
            day_of_week=day_of_week,
            is_active=True
        ).exclude(
            start_time__gte=end_time
        ).exclude(
            end_time__lte=start_time
        )
        
        if existing_slots.exists():
            return JsonResponse({
                'status': 'error',
                'message': f'This slot overlaps with existing slots on {WorkingHours.DAYS_OF_WEEK[day_of_week][1]}'
            }, status=400)
        
        # Set appointment duration to a multiple of 30 if it's not already
        if appointment_duration % 30 != 0:
            appointment_duration = ((appointment_duration // 30) + 1) * 30
        
        # Create new working hours
        working_hour = WorkingHours.objects.create(
            doctor=doctor,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            appointment_duration=appointment_duration,  # Always a multiple of 30
            is_active=is_active
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Availability updated successfully',
            'working_hour': {
                'id': working_hour.id,
                'day_of_week': working_hour.day_of_week,
                'start_time': working_hour.start_time.strftime('%H:%M'),
                'end_time': working_hour.end_time.strftime('%H:%M'),
                'appointment_duration': working_hour.appointment_duration,
                'is_active': working_hour.is_active
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_working_hour(request, working_hour_id):
    """
    Get working hour details for editing
    """
    if not hasattr(request.user, 'doctor'):
        return JsonResponse({
            'status': 'error',
            'message': 'Only doctors can access this endpoint'
        }, status=403)
    
    try:
        working_hour = WorkingHours.objects.get(
            id=working_hour_id,
            doctor=request.user.doctor
        )
        return JsonResponse({
            'status': 'success',
            'working_hour': {
                'day_of_week': working_hour.day_of_week,
                'start_time': working_hour.start_time.strftime('%H:%M'),
                'end_time': working_hour.end_time.strftime('%H:%M'),
                'appointment_duration': working_hour.appointment_duration,
                'is_active': working_hour.is_active
            }
        })
    except WorkingHours.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Working hour not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@doctor_required
def delete_working_hour(request, working_hour_id):
    """
    Delete a working hour
    """
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)
    
    try:
        working_hour = WorkingHours.objects.get(
            id=working_hour_id,
            doctor=request.user.doctor
        )
        
        # Check if there are any appointments for this slot
        has_appointments = Appointment.objects.filter(
            doctor=request.user.doctor,
            status__in=['scheduled', 'accepted'],
            date__gte=timezone.now().date(),
            time_slot__gte=working_hour.start_time,
            time_slot__lte=working_hour.end_time
        ).exists()
        
        if has_appointments:
            return JsonResponse({
                'status': 'error',
                'message': 'Cannot delete slot with existing appointments'
            }, status=400)
        
        # Delete the working hour
        working_hour.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Availability slot deleted successfully'
        })
        
    except WorkingHours.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Working hour not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def generate_appointment_pdf(request, appointment_id):
    """
    Generate a PDF confirmation for an appointment
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if the current user is authorized to view this appointment
    if appointment.patient != request.user and appointment.doctor.user != request.user:
        messages.error(request, "You don't have permission to view this appointment.")
        return redirect('appointments:home')
    
    # Create the HttpResponse object with the appropriate PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="appointment_confirmation_{appointment.id}.pdf"'
    
    # Create the PDF object
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Add title
    elements.append(Paragraph("Appointment Confirmation", title_style))
    elements.append(Spacer(1, 20))
    
    # Patient Information
    elements.append(Paragraph("Patient Information", styles['Heading2']))
    patient_data = [
        ["Name:", appointment.patient.get_full_name()],
        ["Email:", appointment.patient.email],
        ["Phone:", appointment.patient.phone_number if hasattr(appointment.patient, 'phone_number') else "Not provided"]
    ]
    patient_table = Table(patient_data, colWidths=[1.5*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 20))
    
    # Doctor Information
    elements.append(Paragraph("Doctor Information", styles['Heading2']))
    doctor_data = [
        ["Name:", appointment.doctor.user.get_full_name()],
        ["Specialization:", appointment.doctor.specialization.name],
        ["Location:", appointment.doctor.location if hasattr(appointment.doctor, 'location') else "Not provided"]
    ]
    doctor_table = Table(doctor_data, colWidths=[1.5*inch, 4*inch])
    doctor_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(doctor_table)
    elements.append(Spacer(1, 20))
    
    # Appointment Details
    elements.append(Paragraph("Appointment Details", styles['Heading2']))
    appointment_data = [
        ["Date:", appointment.date.strftime("%B %d, %Y")],
        ["Time:", appointment.time_slot],
        ["Status:", appointment.status if appointment.status else "Not specified"],
        ["Reference Number:", f"APT-{appointment.id:06d}"]
    ]
    appointment_table = Table(appointment_data, colWidths=[1.5*inch, 4*inch])
    appointment_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(appointment_table)
    elements.append(Spacer(1, 20))
    
    # Payment Information
    if appointment.is_paid:
        elements.append(Paragraph("Payment Information", styles['Heading2']))
        payment_data = [
            ["Amount:", f"${appointment.doctor.consultation_fee}"],
            ["Status:", "Paid"],
            ["Payment Date:", appointment.payment_date.strftime("%B %d, %Y") if hasattr(appointment, 'payment_date') else "Not available"]
        ]
        payment_table = Table(payment_data, colWidths=[1.5*inch, 4*inch])
        payment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(payment_table)
        elements.append(Spacer(1, 20))
    
    # Clinic Information
    elements.append(Paragraph("Clinic Information", styles['Heading2']))
    clinic_data = [
        ["Name:", "Your Clinic Name"],  # Replace with actual clinic name
        ["Address:", "123 Clinic Street, City, State, ZIP"],  # Replace with actual address
        ["Phone:", "(123) 456-7890"],  # Replace with actual phone
        ["Email:", "contact@clinic.com"]  # Replace with actual email
    ]
    clinic_table = Table(clinic_data, colWidths=[1.5*inch, 4*inch])
    clinic_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(clinic_table)
    
    # Generate PDF
    doc.build(elements)
    
    return response

@login_required
def notification_list(request):
    """View for displaying all notifications"""
    notifications = Notification.objects.filter(user=request.user)
    unread_count = Notification.get_unread_count(request.user)
    
    if request.method == 'POST' and 'mark_all_read' in request.POST:
        Notification.mark_all_as_read(request.user)
        messages.success(request, 'All notifications marked as read')
        return redirect('appointments:notification_list')
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'appointments/notifications.html', context)

@login_required
def notification_detail(request, notification_id):
    """View for displaying a single notification"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    if not notification.is_read:
        notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    return render(request, 'appointments/notification_detail.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """View for marking a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    return JsonResponse({'status': 'success'})

@login_required
def get_unread_count(request):
    """API endpoint to get unread notification count"""
    count = Notification.get_unread_count(request.user)
    return JsonResponse({'count': count})

# Add this to the context processor
def notification_context(request):
    """Context processor to add notification count to all templates"""
    if request.user.is_authenticated:
        return {
            'unread_notification_count': Notification.get_unread_count(request.user)
        }
    return {}

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    Notification.mark_all_as_read(request.user)
    messages.success(request, 'All notifications marked as read')
    return redirect(request.META.get('HTTP_REFERER', 'appointments:home'))

@login_required
@doctor_required
def save_time_slot(request):
    if request.method == 'POST':
        try:
            days = request.POST.getlist('days[]')
            start_times = request.POST.getlist('start_times[]')
            end_times = request.POST.getlist('end_times[]')
            
            if not days or not start_times or not end_times:
                return JsonResponse({'status': 'error', 'message': 'Please provide all required fields'})
            
            # Delete existing working hours for selected days
            WorkingHours.objects.filter(doctor=request.user.doctor, day_of_week__in=days).delete()
            
            # Create new working hours
            for day in days:
                for start_time, end_time in zip(start_times, end_times):
                    try:
                        # Create the working hour
                        WorkingHours.objects.create(
                            doctor=request.user.doctor,
                            day_of_week=day,
                            start_time=start_time,
                            end_time=end_time,
                            is_active=True
                        )
                    except ValidationError as e:
                        return JsonResponse({
                            'status': 'error',
                            'message': str(e)
                        })
            
            return JsonResponse({
                'status': 'success',
                'message': 'Time slots saved successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
@doctor_required
@require_POST
def delete_time_slot(request, slot_id):
    try:
        working_hour = WorkingHours.objects.get(id=slot_id, doctor=request.user.doctor)
        working_hour.delete()
        return JsonResponse({'status': 'success', 'message': 'Time slot deleted successfully'})
    except WorkingHours.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Time slot not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@doctor_required
def handle_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            appointment.status = 'accepted'
            appointment.save()
            
            # Create notification for patient
            Notification.objects.create(
                recipient=appointment.patient,
                title='Appointment Accepted',
                message=f'Your appointment with Dr. {request.user.get_full_name()} has been accepted.',
                notification_type='appointment',
                related_link=f'/appointments/{appointment.id}/'
            )
            
            messages.success(request, 'Appointment accepted successfully.')
            
        elif action == 'reject':
            appointment.status = 'rejected'
            appointment.save()
            
            # Create notification for patient
            Notification.objects.create(
                recipient=appointment.patient,
                title='Appointment Rejected',
                message=f'Your appointment with Dr. {request.user.get_full_name()} has been rejected.',
                notification_type='appointment',
                related_link=f'/appointments/{appointment.id}/'
            )
            
            messages.success(request, 'Appointment rejected successfully.')
    
    return redirect('appointments:doctor_dashboard')

@login_required
@doctor_required
def complete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor)
    
    if request.method == 'POST':
        appointment.status = 'completed'
        appointment.save()
        
        # Create notification for patient
        Notification.objects.create(
            recipient=appointment.patient,
            title='Appointment Completed',
            message=f'Your appointment with Dr. {request.user.get_full_name()} has been marked as completed.',
            notification_type='appointment',
            related_link=f'/appointments/{appointment.id}/'
        )
        
        messages.success(request, 'Appointment marked as completed.')
    
    return redirect('appointments:doctor_dashboard')

@login_required
def download_receipt(request, appointment_id):
    """
    Generate and download a PDF receipt for a paid appointment
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check permissions
    if appointment.patient != request.user and appointment.doctor.user != request.user:
        messages.error(request, "You don't have permission to access this receipt.")
        return redirect('appointments:patient_dashboard')
    
    # Check if appointment is paid
    if not appointment.is_paid:
        messages.error(request, "No receipt available - appointment has not been paid for.")
        return redirect('appointments:patient_dashboard')
    
    try:
        # Get payment details
        payment = Payment.objects.get(appointment=appointment)
        
        # Create the PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{payment.invoice_number}.pdf"'
        
        # Create the PDF document
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='Center',
            parent=styles['Heading1'],
            alignment=1,
        ))
        
        # Add logo and header
        elements.append(Paragraph("MedApp", styles['Center']))
        elements.append(Spacer(1, 20))
        
        # Receipt details
        elements.append(Paragraph("RECEIPT", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Create receipt data
        data = [
            ["Invoice Number:", payment.invoice_number],
            ["Date:", payment.created_at.strftime("%B %d, %Y")],
            ["Transaction ID:", payment.transaction_id],
            ["", ""],
            ["Patient:", appointment.patient.get_full_name()],
            ["Doctor:", f"Dr. {appointment.doctor.user.get_full_name()}"],
            ["Appointment Date:", appointment.date.strftime("%B %d, %Y")],
            ["Appointment Time:", appointment.time_slot],
            ["", ""],
            ["Consultation Fee:", f"${payment.amount}"],
            ["Tax (10%):", f"${payment.tax}"],
            ["Total Amount:", f"${payment.total_amount}"],
            ["Payment Status:", "Paid"],
            ["Payment Method:", payment.payment_method.title()],
        ]
        
        # Create table
        table = Table(data, colWidths=[200, 300])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Add footer
        elements.append(Paragraph("Thank you for your payment!", styles['Center']))
        
        # Build PDF
        doc.build(elements)
        
        return response
        
    except Payment.DoesNotExist:
        messages.error(request, "Receipt not found.")
        return redirect('appointments:patient_dashboard')
    except Exception as e:
        logger.error(f'Error generating receipt: {str(e)}')
        messages.error(request, "An error occurred while generating the receipt.")
        return redirect('appointments:patient_dashboard')

@login_required
def notes_list(request):
    """
    List all notes for the current patient
    """
    if request.user.user_type != 'patient':
        return redirect('appointments:home')
    
    notes = Note.objects.filter(patient=request.user).order_by('-updated_at')
    
    context = {
        'notes': notes,
        'categories': dict(Note.CATEGORY_CHOICES)
    }
    return render(request, 'appointments/notes_list.html', context)

@login_required
def create_note(request):
    """
    Create a new note
    """
    if request.user.user_type != 'patient':
        return redirect('appointments:home')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        share_with_doctor = request.POST.get('share_with_doctor') == 'on'
        
        if not title or not content:
            messages.error(request, 'Title and content are required')
            return redirect('appointments:notes_list')
        
        Note.objects.create(
            patient=request.user,
            title=title,
            content=content,
            category=category,
            share_with_doctor=share_with_doctor
        )
        
        messages.success(request, 'Note created successfully')
        return redirect('appointments:notes_list')
    
    # Get all doctors for doctor selection dropdown
    doctors = Doctor.objects.all()
    
    return render(request, 'appointments/create_note.html', {
        'categories': Note.CATEGORY_CHOICES,
        'doctors': doctors
    })

@login_required
def edit_note(request, note_id):
    """
    Edit an existing note
    """
    if request.user.user_type != 'patient':
        return redirect('appointments:home')
    
    note = get_object_or_404(Note, id=note_id, patient=request.user)
    
    if request.method == 'POST':
        note.title = request.POST.get('title')
        note.content = request.POST.get('content')
        note.category = request.POST.get('category')
        note.share_with_doctor = request.POST.get('share_with_doctor') == 'on'
        note.save()
        
        messages.success(request, 'Note updated successfully')
        return redirect('appointments:notes_list')
    
    return render(request, 'appointments/edit_note.html', {
        'note': note,
        'categories': Note.CATEGORY_CHOICES
    })

@login_required
def delete_note(request, note_id):
    """
    Delete a note with confirmation
    """
    if request.user.user_type != 'patient':
        return redirect('appointments:home')
    
    note = get_object_or_404(Note, id=note_id, patient=request.user)
    
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully')
        return redirect('appointments:notes_list')
    
    return render(request, 'appointments/delete_note.html', {'note': note})

@login_required
def appointment_detail(request, appointment_id):
    """
    Display detailed information about an appointment.
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Ensure the user has access to this appointment
        if request.user != appointment.patient and request.user != appointment.doctor.user:
            return redirect('appointments:home')
            
        context = {
            'appointment': appointment,
            'is_patient': request.user == appointment.patient,
            'is_doctor': request.user == appointment.doctor.user,
        }
        
        return render(request, 'appointments/appointment_detail.html', context)
        
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found')
        return redirect('appointments:home')

class AddDoctorView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'appointments/add_doctor.html'
    form_class = AddDoctorForm
    success_url = reverse_lazy('appointments:admin_dashboard')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specializations'] = Specialization.objects.all()
        return context

    def form_valid(self, form):
        try:
            doctor = form.save()
            messages.success(self.request, f'Doctor {doctor.user.get_full_name()} added successfully!')
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Error adding doctor: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field}: {error}')
        return super().form_invalid(form)

@login_required
def create_doctor_note(request):
    """Create a note to send to a doctor"""
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        message = request.POST.get('message')
        
        if not doctor_id or not message:
            messages.error(request, 'Both doctor and message are required')
            return redirect('appointments:patient_dashboard')
        
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            
            # Create the note
            note = DoctorPatientNote.objects.create(
                patient=request.user,
                doctor=doctor,
                message=message
            )
            
            # Create notification for doctor
            Notification.objects.create(
                recipient=doctor.user,
                title='New Note From Patient',
                message=f'You have a new note from {request.user.get_full_name()}',
                notification_type='doctor_note',
                related_link=f'/doctor-notes/'
            )
            
            messages.success(request, f'Note sent to Dr. {doctor.user.get_full_name()}')
        except Doctor.DoesNotExist:
            messages.error(request, 'Selected doctor does not exist')
        
    return redirect('appointments:patient_dashboard')

@login_required
@doctor_required
def reply_to_patient_note(request, note_id):
    """Reply to a patient's note"""
    note = get_object_or_404(DoctorPatientNote, id=note_id)
    
    # Check if this note is addressed to the logged-in doctor
    if note.doctor.user != request.user:
        messages.error(request, 'You do not have permission to reply to this note')
        return redirect('appointments:doctor_dashboard')
    
    if request.method == 'POST':
        reply = request.POST.get('reply')
        
        if not reply:
            messages.error(request, 'Reply cannot be empty')
            return redirect('appointments:doctor_dashboard')
        
        # Update the note with the reply
        note.reply = reply
        note.replied_at = timezone.now()
        note.is_read_by_doctor = True
        note.is_read_by_patient = False
        note.save()
        
        # Create notification for patient
        Notification.objects.create(
            recipient=note.patient,
            title='Doctor Reply',
            message=f'Dr. {request.user.get_full_name()} has replied to your note',
            notification_type='patient_note_reply',
            related_link=f'/patient-dashboard/#doctor-notes'
        )
        
        messages.success(request, f'Reply sent to {note.patient.get_full_name()}')
    
    return redirect('appointments:doctor_dashboard')

@login_required
def mark_note_as_read(request, note_id):
    """Mark a note as read"""
    note = get_object_or_404(DoctorPatientNote, id=note_id)
    
    # Check if the user has permission to access this note
    if request.user == note.patient:
        note.is_read_by_patient = True
        note.save()
    elif hasattr(request.user, 'doctor') and request.user.doctor == note.doctor:
        note.is_read_by_doctor = True
        note.save()
    else:
        messages.error(request, 'You do not have permission to access this note')
    
    if request.user == note.patient:
        return redirect('appointments:patient_dashboard')
    else:
        return redirect('appointments:doctor_dashboard')

# New API view for getting available time slots
@login_required
def get_available_time_slots(request, doctor_id):
    """API endpoint to get available time slots for a doctor on a specific date"""
    try:
        # Check for proper AJAX request to prevent CSRF issues
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid request method'}, status=400)
        
        # Get doctor or return 404
        doctor = get_object_or_404(Doctor, id=doctor_id)
        
        # Get date from query params
        date_str = request.GET.get('date')
        day_of_week = request.GET.get('day_of_week')
        
        if not date_str:
            return JsonResponse({
                'error': 'Date parameter is required',
                'time_slots': []
            }, status=400)
        
        try:
            # Parse the date string into a date object
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Get current time with timezone awareness
            now = timezone.now()
            
            # Check if the selected date is in the past
            if selected_date < now.date():
                print(f"Error: Selected date {date_str} is in the past")
                return JsonResponse({
                    'error': 'Selected date is in the past', 
                    'time_slots': [],
                    'date': date_str,
                    'day': selected_date.strftime('%A')
                }, status=400)
            
            # Get day of week index if not provided (0 = Monday, 6 = Sunday)
            if day_of_week is None:
                day_of_week = selected_date.weekday()
            else:
                day_of_week = int(day_of_week)
                
                # Handle case where day_of_week comes from JavaScript (0=Sunday)
                if request.GET.get('js_format') == 'true':
                    # Convert JavaScript's 0=Sunday format to Django's 0=Monday format
                    day_of_week = day_of_week if day_of_week > 0 else 6
            
            # Get day name (Monday, Tuesday, etc.)
            day_name = selected_date.strftime('%A')
            
            # Check if doctor has working hours for this day
            working_hour = WorkingHours.objects.filter(
                doctor=doctor,
                day_of_week=day_of_week,
                is_active=True
            ).first()
            
            # If doctor is not available on this day, return empty slots
            if not working_hour:
                return JsonResponse({
                    'time_slots': [],
                    'booked_slots': [],
                    'date': date_str,
                    'day': day_name,
                    'is_today': selected_date == now.date(),
                    'no_schedule': True,
                    'message': f'The doctor is not available on {day_name}'
                })
            
            # Generate time slots based on doctor's working hours with specified appointment_duration
            time_slots = []
            start_time = working_hour.start_time
            end_time = working_hour.end_time
            
            # Convert to datetime objects for easier time slot generation
            start_datetime = datetime.combine(selected_date, start_time)
            end_datetime = datetime.combine(selected_date, end_time)
            
            # Get appointment duration in minutes, default to 30 if not set
            appointment_duration = working_hour.appointment_duration or 30
            
            # Generate time slots in the specified appointment_duration intervals
            current_time = start_datetime
            while current_time + timedelta(minutes=appointment_duration) <= end_datetime:
                # Start and end time for this slot
                slot_start_time = current_time.time()
                slot_end_time = (current_time + timedelta(minutes=appointment_duration)).time()
                    
                # Format times as strings (HH:MM format)
                start_time_str = slot_start_time.strftime('%H:%M')
                end_time_str = slot_end_time.strftime('%H:%M')
                
                # Add the time slot
                time_slots.append({
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'available': True,
                    'hour': slot_start_time.hour,
                    'reason': None
                })
                
                # Move to the next time slot (using appointment_duration)
                current_time += timedelta(minutes=appointment_duration)
            
            # Get booked appointments for this doctor on the selected date
            booked_appointments = Appointment.objects.filter(
                doctor=doctor,
                date=selected_date,
                status__in=['pending', 'accepted', 'scheduled', 'confirmed']
            )
            
            # Create list of booked slots
            booked_slots = []
            for appointment in booked_appointments:
                try:
                    if '-' in appointment.time_slot:
                        start_time, end_time = appointment.time_slot.split('-')
                        booked_slots.append({
                            'start_time': start_time.strip(),
                            'end_time': end_time.strip(),
                            'status': appointment.status
                        })
                    else:
                        # Handle single time format (HH:MM)
                        time_parts = appointment.time_slot.strip().split(':')
                        if len(time_parts) == 2:
                            hour, minute = map(int, time_parts)
                            slot_start = f"{hour:02d}:{minute:02d}"
                            # Calculate end time based on appointment_duration
                            end_dt = datetime.strptime(slot_start, '%H:%M') + timedelta(minutes=appointment_duration)
                            slot_end = end_dt.strftime('%H:%M')
                            booked_slots.append({
                                'start_time': slot_start,
                                'end_time': slot_end,
                                'status': appointment.status
                            })
                except Exception as e:
                    print(f"Error parsing appointment time slot: {e}")
                    continue  # Skip invalid time slots
            
            # Mark booked slots as unavailable
            for slot in time_slots:
                for booked in booked_slots:
                    if slot['start_time'] == booked['start_time']:
                        slot['available'] = False
                        slot['reason'] = 'This time slot is already booked'
            
            # Check if it's today to handle past slots
            is_today = selected_date == now.date()
            if is_today:
                current_hour = now.hour
                current_minute = now.minute
                
                # Mark past slots as unavailable
                for slot in time_slots:
                    slot_hour, slot_minute = map(int, slot['start_time'].split(':'))
                    if slot_hour < current_hour or (slot_hour == current_hour and slot_minute < current_minute):
                        slot['available'] = False
                        slot['reason'] = "This time slot has already passed"
            
            # Prepare doctor schedule information
            doctor_schedule = {
                'day': day_name,
                'start_time': working_hour.start_time.strftime('%I:%M %p'),
                'end_time': working_hour.end_time.strftime('%I:%M %p'),
                'appointment_duration': appointment_duration
            }
            
            # Return response with time slots and doctor schedule
            print(f"Returning {len(time_slots)} time slots, {len(booked_slots)} booked slots, and doctor schedule")
            return JsonResponse({
                'time_slots': time_slots,
                'booked_slots': booked_slots,
                'date': date_str,
                'day': day_name,
                'is_today': is_today,
                'doctor_schedule': doctor_schedule
            })
            
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return JsonResponse({
                'error': 'Invalid date format. Use YYYY-MM-DD',
                'message': str(e),
                'time_slots': []
            }, status=400)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in get_available_time_slots: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while retrieving time slots',
            'message': str(e),
            'time_slots': []
        }, status=500)

@login_required
def get_appointment_status_updates(request):
    """
    API endpoint to check for appointment status updates for the current patient
    
    Returns:
        JsonResponse: Updated appointments with their status information
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    user = request.user
    
    # Get the last check timestamp from the session or default to 5 minutes ago
    last_check = request.session.get('last_appointment_check', None)
    if last_check:
        last_check = datetime.fromisoformat(last_check)
    else:
        last_check = timezone.now() - timedelta(minutes=5)
    
    # Update the last check timestamp
    request.session['last_appointment_check'] = timezone.now().isoformat()
    
    # Find appointments that have been updated since the last check
    updated_appointments = Appointment.objects.filter(
        patient=user,
        updated_at__gt=last_check
    ).select_related('doctor__user')
    
    # Format the updated appointments for the response
    appointment_updates = []
    for appointment in updated_appointments:
        # Get status display text
        status_display = dict(Appointment.STATUS_CHOICES).get(appointment.status, appointment.status)
        
        # Get status color
        status_color = appointment.get_status_color()
        
        appointment_updates.append({
            'id': appointment.id,
            'doctor_name': appointment.doctor.user.get_full_name(),
            'date': appointment.date.strftime('%Y-%m-%d'),
            'time_slot': appointment.time_slot,
            'status': appointment.status,
            'status_display': status_display,
            'status_color': status_color,
            'is_paid': appointment.is_paid,
            'updated_at': appointment.updated_at.isoformat()
        })
    
    return JsonResponse({
        'updated_appointments': appointment_updates,
        'last_check': timezone.now().isoformat()
    })

@login_required
def get_doctor_working_hours(request, doctor_id):
    """API endpoint to get working hours for a doctor on a specific day, including booked slots"""
    try:
        doctor = get_object_or_404(Doctor, id=doctor_id)
        
        # Get the day of week and date from request parameters
        day_of_week = request.GET.get('day_of_week')
        date_str = request.GET.get('date')
        
        if not day_of_week and not date_str:
            return JsonResponse({
                'error': 'Either day_of_week or date parameter is required',
                'working_hours': []
            }, status=400)
        
        # If date is provided, get the day of week from it
        if date_str:
            try:
                # Parse date with timezone awareness
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Apply timezone awareness if needed
                if settings.USE_TZ:
                    # Convert to an aware datetime at midnight in the current timezone
                    selected_date_aware = timezone.make_aware(
                        datetime.combine(selected_date, datetime.min.time()),
                        timezone.get_current_timezone()
                    )
                    
                    # Extract just the date part again
                    selected_date = selected_date_aware.date()
                
                day_of_week = selected_date.weekday()
            except ValueError as e:
                return JsonResponse({
                    'error': f'Invalid date format: {str(e)}',
                    'working_hours': []
                }, status=400)
        else:
            # If only day_of_week is provided, set date to next occurrence of this day
            day_of_week = int(day_of_week)
            today = timezone.now().date()
            days_ahead = (day_of_week - today.weekday()) % 7
            selected_date = today + timezone.timedelta(days=days_ahead)
        
        # Get working hours for this day
        working_hours = WorkingHours.objects.filter(
            doctor=doctor,
            day_of_week=day_of_week,
            is_active=True
        )
        
        # Get booked appointments for this date
        booked_appointments = Appointment.objects.filter(
            doctor=doctor,
            date=selected_date,
            status__in=['accepted', 'pending', 'scheduled']
        )
        
        # Create list of booked slots
        booked_slots = []
        for appointment in booked_appointments:
            start_time, end_time = appointment.time_slot.split('-')
            booked_slots.append({
                'start_time': start_time.strip(),
                'end_time': end_time.strip(),
                'status': appointment.status
            })
        
        # Format working hours for response
        working_hours_data = []
        for wh in working_hours:
            working_hours_data.append({
                'id': wh.id,
                'day_of_week': wh.day_of_week,
                'day_name': dict(WorkingHours.DAYS_OF_WEEK).get(wh.day_of_week),
                'start_time': wh.start_time.strftime('%H:%M'),
                'end_time': wh.end_time.strftime('%H:%M'),
                'appointment_duration': wh.appointment_duration
            })
        
        return JsonResponse({
            'working_hours': working_hours_data,
            'booked_slots': booked_slots,
            'date': date_str,
            'day_of_week': day_of_week
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': f'An error occurred: {str(e)}',
            'working_hours': []
        }, status=500)

@login_required
def make_payment(request, appointment_id):
    """
    Display payment form for the appointment
    Also handles initial payment setup for Razorpay
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check - only patient should be able to pay
    if appointment.patient != request.user:
        messages.error(request, "You don't have permission to make a payment for this appointment.")
        return redirect('appointments:patient_dashboard')
    
    if appointment.is_paid:
        messages.info(request, "This appointment has already been paid for.")
        return redirect('appointments:patient_dashboard')
    
    # Get or create payment object
    payment, created = Payment.objects.get_or_create(
        appointment=appointment,
        defaults={
            'amount': appointment.doctor.consultation_fee,
            'tax': appointment.doctor.consultation_fee * Decimal('0.18'),  # 18% tax
            'total_amount': appointment.doctor.consultation_fee * Decimal('1.18'),
            'status': 'pending'
        }
    )
    
    # Set up Razorpay integration
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            print(f"[DEBUG] Processing payment setup for appointment {appointment_id}")
            print(f"[DEBUG] Request headers: {request.headers}")
            import razorpay
            from django.conf import settings
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Add verification info
            print(f"[DEBUG] Using Razorpay key: {settings.RAZORPAY_KEY_ID[:5]}***")
            print(f"[DEBUG] Content-Type: {request.headers.get('content-type')}")
            
            # Convert to paisa (Razorpay requires amount in smallest currency unit)
            amount_in_paisa = int(payment.total_amount * 100)
            print(f"[DEBUG] Amount in paisa: {amount_in_paisa}")
            
            # Create Razorpay order
            order_data = {
                'amount': amount_in_paisa,
                'currency': 'INR',
                'receipt': f'receipt_appointment_{appointment.id}',
                'notes': {
                    'appointment_id': appointment.id,
                    'patient_name': request.user.get_full_name(),
                    'doctor_name': appointment.doctor.user.get_full_name()
                }
            }
            
            print(f"[DEBUG] Creating Razorpay order with data: {order_data}")
            try:
                order = client.order.create(data=order_data)
                print(f"[DEBUG] Order created: {order}")
            except Exception as order_error:
                print(f"[DEBUG] Error creating order: {str(order_error)}")
                import traceback
                traceback.print_exc()
                raise order_error
            
            response_data = {
                'status': 'success',
                'key_id': settings.RAZORPAY_KEY_ID,
                'order_id': order['id'],
                'amount': amount_in_paisa,
                'name': request.user.get_full_name(),
                'email': request.user.email,
                'phone': request.user.phone_number if hasattr(request.user, 'phone_number') else ''
            }
            print(f"[DEBUG] Returning response: {response_data}")
            return JsonResponse(response_data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[DEBUG] Error in Razorpay setup: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    # For normal GET requests, just show the payment form
    context = {
        'appointment': appointment,
        'payment': payment,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'doctor': appointment.doctor,
        'fee': payment.amount,
        'tax': payment.tax,
        'total': payment.total_amount
    }
    
    return render(request, 'appointments/make_payment.html', context)

@login_required
def process_payment(request, appointment_id):
    """
    Process the payment for an appointment with Razorpay
    """
    import razorpay
    from django.conf import settings
    import json
    
    print(f"[DEBUG] Processing payment verification for appointment {appointment_id}")
    print(f"[DEBUG] Request method: {request.method}")
    print(f"[DEBUG] Request headers: {request.headers}")
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check
    if appointment.patient != request.user:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': "You don't have permission to make this payment."
            }, status=403)
        messages.error(request, "You don't have permission to make a payment for this appointment.")
        return redirect('appointments:patient_dashboard')
    
    if request.method != 'POST':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': "Invalid request method."
            }, status=405)
        return redirect('appointments:make_payment', appointment_id=appointment_id)
    
    # Get payment
    try:
        payment = Payment.objects.get(appointment=appointment)
        print(f"[DEBUG] Found payment: {payment.id}, status: {payment.status}")
    except Payment.DoesNotExist:
        print(f"[DEBUG] Payment not found for appointment {appointment_id}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': "Payment not found."
            }, status=404)
        messages.error(request, "Payment not found.")
        return redirect('appointments:make_payment', appointment_id=appointment_id)
    
    # Parse JSON data if the request has a JSON content type
    if request.headers.get('content-type') == 'application/json':
        try:
            print(f"[DEBUG] Parsing JSON body")
            data = json.loads(request.body)
            print(f"[DEBUG] Parsed data: {data}")
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': "Invalid JSON data."
            }, status=400)
    else:
        print(f"[DEBUG] Using POST data")
        data = request.POST
        print(f"[DEBUG] POST data: {data}")
    
    # Get Razorpay payment data
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')
    
    print(f"[DEBUG] Payment ID: {razorpay_payment_id}")
    print(f"[DEBUG] Order ID: {razorpay_order_id}")
    print(f"[DEBUG] Signature: {razorpay_signature[:10]}***" if razorpay_signature else "None")
    
    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        print(f"[DEBUG] Missing Razorpay payment information")
        return JsonResponse({
            'status': 'error',
            'message': "Missing Razorpay payment information."
        }, status=400)
    
    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Verify payment signature
    try:
        print(f"[DEBUG] Verifying payment signature")
        client.utility.verify_payment_signature({
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_signature': razorpay_signature
        })
        print(f"[DEBUG] Payment signature verified successfully")
    except Exception as e:
        print(f"[DEBUG] Payment signature verification failed: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f"Invalid payment signature: {str(e)}"
        }, status=400)
    
    # Update payment record
    try:
        payment.status = 'completed'
        payment.transaction_id = razorpay_payment_id
        payment.payment_method = 'razorpay'
        payment.save()
        print(f"[DEBUG] Payment record updated successfully")
        
        # Mark appointment as paid and confirmed
        appointment.is_paid = True
        appointment.status = 'confirmed'
        appointment.save()
        print(f"[DEBUG] Appointment marked as paid and confirmed")
    except Exception as e:
        print(f"[DEBUG] Error updating records: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': f"Error updating records: {str(e)}"
        }, status=500)
    
    # Create notifications
    try:
        # Notification for doctor
        print(f"[DEBUG] Creating doctor notification")
        Notification.objects.create(
            user=appointment.doctor.user,
            message=f"Payment received for appointment with {appointment.patient.get_full_name()} on {appointment.date.strftime('%Y-%m-%d')} at {appointment.time_slot}",
            notification_type='payment',
            reference_id=appointment.id
        )
        
        # Notify admins
        print(f"[DEBUG] Creating admin notifications")
        for admin in User.objects.filter(is_staff=True, is_active=True):
            Notification.objects.create(
                user=admin,
                message=f"Payment received for appointment #{appointment.id}",
                notification_type='payment',
                reference_id=appointment.id
            )
        print(f"[DEBUG] All notifications created successfully")
    except Exception as e:
        # Log notification creation error but don't fail the payment
        print(f"[DEBUG] Error creating payment notification: {str(e)}")
    
    print(f"[DEBUG] Sending success response")
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': "Payment processed successfully."
        })
    
    messages.success(request, "Payment processed successfully.")
    return redirect('appointments:patient_dashboard')

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    # Only allow cancellation if the appointment is pending
    if appointment.status != 'pending':
        messages.error(request, "Only pending appointments can be cancelled.")
        return redirect('appointments:patient_dashboard')
    
    # Update the appointment status to cancelled
    appointment.status = 'cancelled'
    appointment.save()
    
    # Add a success message
    messages.success(request, "Your appointment has been cancelled successfully.")
    
    # Redirect to the patient dashboard
    return redirect('appointments:patient_dashboard')

# Static Pages
def about(request):
    return render(request, 'appointments/about.html')

def contact(request):
    return render(request, 'appointments/contact.html')

def visitor_information(request):
    return render(request, 'appointments/visitor_information.html')

@login_required
def create_payment_order(request):
    """
    Create a Razorpay payment order for an appointment
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        appointment_id = data.get('appointment_id')
        
        if not appointment_id:
            return JsonResponse({'status': 'error', 'message': 'Appointment ID is required'}, status=400)
        
        # Get the appointment
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Verify ownership
        if appointment.patient != request.user:
            return JsonResponse({'status': 'error', 'message': 'You do not have permission to pay for this appointment'}, status=403)
        
        # Verify appointment status
        if appointment.status != 'accepted':
            return JsonResponse({'status': 'error', 'message': 'This appointment is not ready for payment'}, status=400)
        
        # Check if already paid
        if appointment.is_paid:
            return JsonResponse({'status': 'error', 'message': 'This appointment is already paid'}, status=400)
        
        # Get the doctor's consultation fee
        amount = int(appointment.doctor.consultation_fee * 100)  # Convert to paisa
        
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create order
        receipt_id = f"receipt_{appointment.id}_{int(datetime.now().timestamp())}"
        order_data = {
            'amount': amount,
            'currency': 'INR',
            'receipt': receipt_id,
            'notes': {
                'appointment_id': str(appointment.id),
                'doctor_name': appointment.doctor.user.get_full_name(),
                'patient_name': request.user.get_full_name(),
                'date': str(appointment.date),
                'time': appointment.time_slot
            }
        }
        
        order = client.order.create(data=order_data)
        
        # Return order details to frontend
        return JsonResponse({
            'status': 'success',
            'key_id': settings.RAZORPAY_KEY_ID,
            'amount': amount,
            'currency': 'INR',
            'order_id': order['id'],
            'doctor_name': appointment.doctor.user.get_full_name(),
            'patient_name': request.user.get_full_name(),
            'patient_email': request.user.email,
            'patient_phone': request.user.phone_number
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def verify_payment(request):
    """
    Verify a Razorpay payment and update appointment status
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        appointment_id = data.get('appointment_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        
        if not all([appointment_id, razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
        
        # Get the appointment
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Verify ownership
        if appointment.patient != request.user:
            return JsonResponse({'status': 'error', 'message': 'You do not have permission to pay for this appointment'}, status=403)
        
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Verify signature
        params_dict = {
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Invalid payment signature'}, status=400)
        
        # Payment is valid, update appointment
        current_time = timezone.now()
        appointment.is_paid = True
        appointment.payment_status = 'paid'
        appointment.status = 'paid'
        appointment.payment_time = current_time
        appointment.transaction_id = razorpay_payment_id
        appointment.save()
        
        # Create payment record
        doctor_fee = appointment.doctor.consultation_fee
        tax_amount = doctor_fee * Decimal('0.18')  # 18% tax
        total_amount = doctor_fee + tax_amount
        
        # Generate unique invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{get_random_string(6).upper()}"
        
        payment = Payment.objects.create(
            appointment=appointment,
            amount=doctor_fee,
            tax=tax_amount,
            total_amount=total_amount,
            transaction_id=razorpay_payment_id,
            status='completed',
            payment_method='Razorpay',
            invoice_number=invoice_number
        )
        
        # Generate invoice PDF
        invoice_path = generate_invoice_pdf(payment)
        
        # Store the invoice URL in the appointment model
        invoice_url = f'/appointments/{appointment.id}/download-invoice/'
        appointment.invoice_url = invoice_url
        appointment.save()
        
        # Create notification for patient
        Notification.create_notification(
            recipient=request.user,
            title='Payment Successful',
            message=f'Your payment for appointment with Dr. {appointment.doctor.user.get_full_name()} has been completed successfully.',
            notification_type='system',
            related_link=f'/appointments/{appointment.id}/'
        )
        
        # Create notification for doctor
        Notification.create_notification(
            recipient=appointment.doctor.user,
            title='Payment Received',
            message=f'Payment received from {request.user.get_full_name()} for appointment on {appointment.date}.',
            notification_type='system',
            related_link=f'/appointments/{appointment.id}/'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Payment verified successfully',
            'invoice_url': invoice_url
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def generate_invoice_pdf(payment):
    """
    Generate a PDF invoice for a payment
    """
    appointment = payment.appointment
    patient = appointment.patient
    doctor = appointment.doctor
    
    # Create directory if it doesn't exist
    invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
    os.makedirs(invoice_dir, exist_ok=True)
    
    # Generate filename
    filename = f"invoice_{payment.invoice_number}.pdf"
    filepath = os.path.join(invoice_dir, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add title
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add invoice details
    elements.append(Paragraph(f"Invoice Number: {payment.invoice_number}", subtitle_style))
    elements.append(Paragraph(f"Date: {payment.created_at.strftime('%d %b, %Y')}", normal_style))
    elements.append(Paragraph(f"Transaction ID: {payment.transaction_id}", normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add patient and doctor details
    elements.append(Paragraph("Patient Details:", subtitle_style))
    elements.append(Paragraph(f"Name: {patient.get_full_name()}", normal_style))
    elements.append(Paragraph(f"Email: {patient.email}", normal_style))
    elements.append(Paragraph(f"Phone: {patient.phone_number}", normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    elements.append(Paragraph("Doctor Details:", subtitle_style))
    elements.append(Paragraph(f"Name: Dr. {doctor.user.get_full_name()}", normal_style))
    elements.append(Paragraph(f"Specialization: {doctor.specialization.name}", normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add appointment details
    elements.append(Paragraph("Appointment Details:", subtitle_style))
    elements.append(Paragraph(f"Date: {appointment.date.strftime('%d %b, %Y')}", normal_style))
    elements.append(Paragraph(f"Time: {appointment.time_slot}", normal_style))
    elements.append(Paragraph(f"Type: {appointment.get_appointment_type_display()}", normal_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Add payment details table
    data = [
        ["Description", "Amount (INR)"],
        ["Consultation Fee", f"{payment.amount:.2f}"],
        ["Tax (18%)", f"{payment.tax:.2f}"],
        ["", ""],
        ["Total", f"{payment.total_amount:.2f}"]
    ]
    
    table = Table(data, colWidths=[4*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, -1), (1, -1), colors.beige),
        ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (1, -2), 1, colors.black),
        ('BOX', (0, -1), (1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Add footer
    elements.append(Paragraph("Thank you for choosing our services!", normal_style))
    elements.append(Paragraph("This is a computer-generated invoice and does not require a signature.", normal_style))
    
    # Build PDF
    doc.build(elements)
    
    return filepath

@login_required
def download_invoice(request, appointment_id):
    """
    Download the invoice for an appointment
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if user is authorized (patient or doctor)
    if not (request.user == appointment.patient or request.user == appointment.doctor.user):
        messages.error(request, "You don't have permission to access this invoice.")
        return redirect('appointments:patient_dashboard')
    
    try:
        payment = Payment.objects.get(appointment=appointment)
    except Payment.DoesNotExist:
        messages.error(request, "No payment record found for this appointment.")
        return redirect('appointments:patient_dashboard')
    
    # Check if invoice exists, if not generate it
    invoice_filename = f"invoice_{payment.invoice_number}.pdf"
    invoice_path = os.path.join(settings.MEDIA_ROOT, 'invoices', invoice_filename)
    
    if not os.path.exists(invoice_path):
        invoice_path = generate_invoice_pdf(payment)
    
    # Serve the file
    if os.path.exists(invoice_path):
        with open(invoice_path, 'rb') as pdf:
            response = HttpResponse(pdf.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{invoice_filename}"'
            return response
    else:
        messages.error(request, "Invoice file not found.")
        return redirect('appointments:patient_dashboard')

@login_required
def my_appointments(request):
    """
    Display all appointments for the current patient.
    This is the full list view that can be accessed from the "View All" button.
    """
    user = request.user
    today = date.today()
    
    # Fetch all appointments and order by creation date (newest first)
    appointments = Appointment.objects.filter(patient=user).order_by('-created_at')
    
    # Get filter parameters if any
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply filters if provided
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            appointments = appointments.filter(date__gte=date_from_obj)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            appointments = appointments.filter(date__lte=date_to_obj)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    context = {
        'appointments': appointments,
        'today': today,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Appointment.STATUS_CHOICES
    }
    
    return render(request, 'appointments/my_appointments.html', context)

@login_required
def check_slot_availability(request):
    """
    API endpoint to check if a specific time slot is still available
    Returns JSON with availability status
    """
    # Check if this is an AJAX request
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    # Get query parameters
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    time_slot = request.GET.get('time_slot')
    
    # Validate required parameters
    if not all([doctor_id, date_str, time_slot]):
        return JsonResponse({
            'available': False,
            'message': 'Missing required parameters'
        }, status=400)
    
    try:
        # Parse date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get doctor
        doctor = get_object_or_404(Doctor, id=doctor_id)
        
        # Check if the slot is already booked
        existing_appointment = Appointment.objects.filter(
            doctor=doctor,
            date=date_obj,
            time_slot=time_slot
        ).exists()
        
        # Return availability status
        return JsonResponse({
            'available': not existing_appointment,
            'message': 'This time slot is already booked' if existing_appointment else 'Time slot is available'
        })
        
    except Exception as e:
        return JsonResponse({
            'available': False,
            'message': str(e)
        }, status=500)

@login_required
def reschedule_appointment_api(request, appointment_id):
    """
    API endpoint to reschedule an appointment
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    # Get the appointment
    try:
        appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
    except Appointment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Appointment not found'}, status=404)
    
    # Check if appointment can be rescheduled
    if appointment.status in ['cancelled', 'completed', 'rejected']:
        return JsonResponse({
            'status': 'error', 
            'message': f'Cannot reschedule a {appointment.status} appointment'
        }, status=400)
    
    # Parse request data
    data = json.loads(request.body)
    new_date = data.get('new_date')
    new_time = data.get('new_time')
    
    if not new_date or not new_time:
        return JsonResponse({
            'status': 'error', 
            'message': 'New date and time are required'
        }, status=400)
    
    try:
        # Parse date
        new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()
        
        # Update appointment
        appointment.date = new_date_obj
        appointment.time_slot = new_time
        appointment.save()
        
        # Format date for display
        formatted_date = new_date_obj.strftime('%b %d, %Y')
        
        # Format time for display (convert from "HH:MM-HH:MM" to a more readable format)
        time_parts = new_time.split('-')
        if len(time_parts) == 2:
            start_time = time_parts[0]
            end_time = time_parts[1]
            
            # Convert to 12-hour format
            try:
                start_hour, start_minute = start_time.split(':')
                end_hour, end_minute = end_time.split(':')
                
                start_hour = int(start_hour)
                end_hour = int(end_hour)
                
                start_am_pm = 'AM' if start_hour < 12 else 'PM'
                end_am_pm = 'AM' if end_hour < 12 else 'PM'
                
                if start_hour > 12:
                    start_hour -= 12
                elif start_hour == 0:
                    start_hour = 12
                    
                if end_hour > 12:
                    end_hour -= 12
                elif end_hour == 0:
                    end_hour = 12
                
                formatted_time = f"{start_hour}:{start_minute} {start_am_pm} - {end_hour}:{end_minute} {end_am_pm}"
            except ValueError:
                formatted_time = new_time
        else:
            formatted_time = new_time
        
        return JsonResponse({
            'status': 'success',
            'message': 'Appointment rescheduled successfully',
            'formatted_date': formatted_date,
            'formatted_time': formatted_time
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to reschedule appointment: {str(e)}'
        }, status=500)
