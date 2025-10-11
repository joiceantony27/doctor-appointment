from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, UpdateView, DeleteView
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Q, Avg, ExpressionWrapper, FloatField
from django.db.models.functions import Cast
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib import messages
from .models import User, Doctor, Appointment, Payment, Review, Specialization, Notification, WorkingHours, BlockedTimeSlot
from datetime import datetime, timedelta
import csv
import json
from .decorators import admin_required

class AdminDashboardView(TemplateView):
    template_name = 'appointments/admin_dashboard.html'
    
    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Basic statistics
        context.update({
            'total_users': User.objects.count(),
            'total_doctors': Doctor.objects.count(),
            'today_appointments': Appointment.objects.filter(date=today).count(),
            'pending_payments': Payment.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_revenue': Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0,
            'avg_rating': Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0,
            'pending_approvals': Doctor.objects.filter(is_available=False).count(),
        })
        
        # Appointment trends (last 30 days)
        appointment_data = (Appointment.objects
            .filter(date__gte=today - timedelta(days=30))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date'))
        
        context['appointment_dates'] = json.dumps([d['date'].strftime('%Y-%m-%d') for d in appointment_data])
        context['appointment_counts'] = json.dumps([d['count'] for d in appointment_data])
        
        # Specialization distribution
        specialization_data = (Doctor.objects
            .values('specialization__name')
            .annotate(count=Count('id'))
            .order_by('-count'))
        
        context['specialization_labels'] = json.dumps([d['specialization__name'] for d in specialization_data])
        context['specialization_counts'] = json.dumps([d['count'] for d in specialization_data])
        
        # Recent activities
        context['recent_activities'] = self.get_recent_activities()
        
        # Recent appointments
        context['recent_appointments'] = (Appointment.objects
            .select_related('patient', 'doctor__user')
            .order_by('-created_at')[:10])
        
        # Recent users
        context['recent_users'] = User.objects.order_by('-date_joined')[:10]
        
        # Recent payments
        context['recent_payments'] = Payment.objects.select_related(
            'appointment__patient', 'appointment__doctor'
        ).order_by('-created_at')[:10]
        
        # Top doctors
        context['top_doctors'] = Doctor.objects.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
            appointment_count=Count('doctor_appointments'),
            total_revenue=Sum('doctor_appointments__payment__amount'),
            completion_rate=ExpressionWrapper(
                100.0 * Count('doctor_appointments', filter=Q(doctor_appointments__status='completed')) /
                Cast(Count('doctor_appointments'), FloatField()),
                output_field=FloatField()
            )
        ).filter(
            is_available=True
        ).order_by('-avg_rating', '-review_count')[:6]
        
        # Add notifications
        context['unread_notifications_count'] = Notification.objects.filter(
            recipient=self.request.user,
            is_read=False
        ).count()
        
        context['recent_notifications'] = Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')[:5]
        
        # Revenue data
        revenue_data = Payment.objects.values('status').annotate(total=Sum('amount')).order_by('status')
        
        # Create a dictionary for easier lookup
        revenue_dict = {item['status']: item['total'] for item in revenue_data}
        
        context['revenue_data'] = [
            revenue_dict.get('completed', 0),
            revenue_dict.get('pending', 0),
            revenue_dict.get('cancelled', 0),
        ]
        
        return context
    
    def get_recent_activities(self):
        activities = []
        
        # Recent appointments
        appointments = Appointment.objects.select_related('patient', 'doctor__user')[:10]
        for apt in appointments:
            activities.append({
                'action': 'Appointment',
                'user': apt.patient.get_full_name(),
                'description': f'Booked appointment with Dr. {apt.doctor.user.get_full_name()}',
                'created_at': apt.created_at
            })
        
        # Recent user registrations
        registrations = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7))
        for user in registrations:
            activities.append({
                'action': 'Registration',
                'user': user.get_full_name(),
                'description': f'New {user.user_type} registration',
                'created_at': user.date_joined
            })
        
        # Recent payments
        payments = Payment.objects.select_related('appointment__patient')[:10]
        for payment in payments:
            activities.append({
                'action': 'Payment',
                'user': payment.appointment.patient.get_full_name(),
                'description': f'Payment of ${payment.amount} processed',
                'created_at': payment.created_at
            })
        
        # Sort by created_at and return most recent 10
        return sorted(activities, key=lambda x: x['created_at'], reverse=True)[:10]

class UserManagementView(ListView):
    model = User
    template_name = 'appointments/admin/user_management.html'
    context_object_name = 'users'
    paginate_by = 10
    
    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = User.objects.all()
        search_query = self.request.GET.get('search', '')
        user_type = self.request.GET.get('user_type', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        return queryset.order_by('-date_joined')

class DoctorVerificationView(ListView):
    model = Doctor
    template_name = 'appointments/admin/doctor_verification.html'
    context_object_name = 'doctors'
    paginate_by = 10
    
    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return Doctor.objects.filter(is_available=False).select_related('user', 'specialization')
    
    def post(self, request, *args, **kwargs):
        doctor_id = request.POST.get('doctor_id')
        action = request.POST.get('action')
        
        if doctor_id and action in ['approve', 'reject']:
            doctor = get_object_or_404(Doctor, id=doctor_id)
            if action == 'approve':
                doctor.is_available = True
                doctor.save()
                messages.success(request, f'Dr. {doctor.user.get_full_name()} has been approved.')
            else:
                doctor.user.is_active = False
                doctor.user.save()
                messages.success(request, f'Dr. {doctor.user.get_full_name()} has been rejected.')
        
        return redirect('appointments:doctor_verification')

class AppointmentManagementView(ListView):
    model = Appointment
    template_name = 'appointments/admin/appointment_management.html'
    context_object_name = 'appointments'
    paginate_by = 20
    
    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = Appointment.objects.select_related('patient', 'doctor__user')
        status = self.request.GET.get('status', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-time_slot')

class PaymentOverviewView(ListView):
    model = Payment
    template_name = 'appointments/admin/payment_overview.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Payment statistics
        total_payments = Payment.objects.filter(status='completed')
        context['total_amount'] = total_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_transactions'] = total_payments.count()
        
        # Recent transactions
        context['recent_transactions'] = Payment.objects.select_related(
            'appointment__patient', 'appointment__doctor'
        ).order_by('-created_at')[:10]
        
        return context

@login_required
@admin_required
def export_appointments_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="appointments.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Time', 'Patient', 'Doctor', 'Status', 'Payment Status'])
    
    appointments = Appointment.objects.select_related('patient', 'doctor__user').all()
    
    for appointment in appointments:
        writer.writerow([
            appointment.date,
            appointment.time_slot,
            appointment.patient.get_full_name(),
            appointment.doctor.user.get_full_name(),
            appointment.status,
            appointment.payment_status
        ])
    
    return response

@login_required
@admin_required
def export_payments_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Invoice', 'Patient', 'Doctor', 'Amount', 'Status'])
    
    payments = Payment.objects.select_related('appointment__patient', 'appointment__doctor__user').all()
    
    for payment in payments:
        writer.writerow([
            payment.created_at.date(),
            payment.invoice_number,
            payment.appointment.patient.get_full_name(),
            payment.appointment.doctor.user.get_full_name(),
            payment.amount,
            payment.status
        ])
    
    return response

@login_required
@admin_required
def load_section(request, section):
    """Load admin dashboard section content via AJAX."""
    template_map = {
        'users': 'appointments/admin/user_management.html',
        'doctors': 'appointments/admin/doctor_verification.html',
        'appointments': 'appointments/admin/appointment_management.html',
        'payments': 'appointments/admin/payment_overview.html',
        'reports': 'appointments/admin/reports.html',
        'settings': 'appointments/admin/settings.html',
    }
    
    if section not in template_map:
        return HttpResponse("Section not found", status=404)
    
    context = {}
    
    # Add section-specific data
    if section == 'users':
        context['users'] = User.objects.all().order_by('-date_joined')[:10]
    elif section == 'doctors':
        context['pending_doctors'] = Doctor.objects.filter(is_available=False)
    elif section == 'appointments':
        context['recent_appointments'] = Appointment.objects.all().order_by('-date')[:10]
    elif section == 'payments':
        context['recent_payments'] = Payment.objects.all().order_by('-created_at')[:10]
    
    return render(request, template_map[section], context)

def get_recent_activities():
    activities = []
    
    # Recent appointments
    appointments = Appointment.objects.select_related('patient', 'doctor__user')[:10]
    for apt in appointments:
        activities.append({
            'action': 'Appointment',
            'user': apt.patient.get_full_name(),
            'description': f'Booked appointment with Dr. {apt.doctor.user.get_full_name()}',
            'created_at': apt.created_at
        })
    
    # Recent user registrations
    registrations = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7))
    for user in registrations:
        activities.append({
            'action': 'Registration',
            'user': user.get_full_name(),
            'description': f'New {user.user_type} registration',
            'created_at': user.date_joined
        })
    
    # Recent payments
    payments = Payment.objects.select_related('appointment__patient')[:10]
    for payment in payments:
        activities.append({
            'action': 'Payment',
            'user': payment.appointment.patient.get_full_name(),
            'description': f'Payment of ${payment.amount} processed',
            'created_at': payment.created_at
        })
    
    # Sort by created_at and return most recent 10
    return sorted(activities, key=lambda x: x['created_at'], reverse=True)[:10]

@login_required
@admin_required
def admin_dashboard(request):
    today = timezone.now().date()
    
    # Basic statistics
    context = {
        'total_users': User.objects.filter(user_type='patient').count(),
        'active_doctors': Doctor.objects.filter(is_available=True).count(),
        'today_appointments': Appointment.objects.filter(date=today).count(),
        'pending_payments': Payment.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_revenue': Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0,
        'avg_rating': Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    
    # Get recent patients only
    context['recent_users'] = User.objects.filter(user_type='patient').order_by('-date_joined')[:10]
    
    # Appointment trends (last 30 days)
    appointment_data = (Appointment.objects
        .filter(date__gte=today - timedelta(days=30))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date'))
    
    context['appointment_dates'] = [d['date'].strftime('%Y-%m-%d') for d in appointment_data]
    context['appointment_counts'] = [d['count'] for d in appointment_data]
    
    # Revenue data
    revenue_data = Payment.objects.values('status').annotate(total=Sum('amount')).order_by('status')
    
    # Create a dictionary for easier lookup
    revenue_dict = {item['status']: item['total'] for item in revenue_data}
    
    context['revenue_data'] = [
        revenue_dict.get('completed', 0),
        revenue_dict.get('pending', 0),
        revenue_dict.get('cancelled', 0),
    ]
    
    # Specialization distribution
    specialization_data = (Doctor.objects
        .values('specialization__name')
        .annotate(count=Count('id'))
        .order_by('-count'))
    
    context['specialization_names'] = [d['specialization__name'] for d in specialization_data]
    context['specialization_counts'] = [d['count'] for d in specialization_data]
    
    # User registration trends
    user_reg_data = (User.objects
        .filter(date_joined__gte=today - timedelta(days=30))
        .values('date_joined__date')
        .annotate(
            patient_count=Count('id', filter=Q(user_type='patient')),
            doctor_count=Count('id', filter=Q(user_type='doctor'))
        )
        .order_by('date_joined__date'))
    
    context['user_reg_dates'] = [d['date_joined__date'].strftime('%Y-%m-%d') for d in user_reg_data]
    context['patient_reg_counts'] = [d['patient_count'] for d in user_reg_data]
    context['doctor_reg_counts'] = [d['doctor_count'] for d in user_reg_data]
    
    # Calendar events
    appointments = Appointment.objects.filter(
        date__gte=today - timedelta(days=7),
        date__lte=today + timedelta(days=30)
    ).select_related('patient', 'doctor')
    
    context['calendar_events'] = [{
        'id': apt.id,
        'title': f"{apt.patient.get_full_name()} - Dr. {apt.doctor.user.get_full_name()}",
        'start': f"{apt.date.isoformat()}T{apt.time_slot}",
        'end': f"{apt.date.isoformat()}T{apt.get_end_time()}",
        'className': f"bg-{apt.get_status_color()}"
    } for apt in appointments]
    
    # Recent activities
    context['recent_activities'] = get_recent_activities()
    
    # Notifications
    context['unread_notifications_count'] = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    context['recent_notifications'] = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:5]
    
    # Top doctors
    context['top_doctors'] = Doctor.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews'),
        appointment_count=Count('doctor_appointments'),
        total_revenue=Sum('doctor_appointments__payment__amount'),
        completion_rate=ExpressionWrapper(
            100.0 * Count('doctor_appointments', filter=Q(doctor_appointments__status='completed')) /
            Cast(Count('doctor_appointments'), FloatField()),
            output_field=FloatField()
        )
    ).filter(
        is_available=True
    ).order_by('-avg_rating', '-review_count')[:6]
    
    return render(request, 'appointments/admin_dashboard.html', context)

@login_required
@admin_required
def users_section(request):
    # Get query parameters
    search_query = request.GET.get('search', '')
    
    # Base queryset - only get patients
    users = User.objects.filter(user_type='patient')
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Order by most recent first
    users = users.order_by('-date_joined')
    
    context = {
        'users': users,
        'search_query': search_query
    }
    
    return render(request, 'appointments/sections/users.html', context)

@login_required
@admin_required
def get_user_details(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, 'appointments/sections/user_details.html', {'user': user})

@login_required
@admin_required
def view_patient_detail(request, id):
    """
    Returns patient details in JSON format for AJAX requests
    """
    try:
        patient = get_object_or_404(User, id=id, user_type='patient')
        
        # Get patient statistics
        total_appointments = Appointment.objects.filter(patient=patient).count()
        completed_appointments = Appointment.objects.filter(patient=patient, status='completed').count()
        pending_appointments = Appointment.objects.filter(patient=patient, status='pending').count()
        
        # Get recent appointments
        recent_appointments = Appointment.objects.filter(patient=patient).order_by('-date')[:5]
        appointment_list = []
        
        for appointment in recent_appointments:
            appointment_list.append({
                'id': appointment.id,
                'doctor_name': appointment.doctor.user.get_full_name(),
                'date': appointment.date.strftime('%Y-%m-%d'),
                'time': str(appointment.time_slot),
                'status': appointment.status,
                'reason': appointment.reason
            })
        
        # Build patient data
        patient_data = {
            'id': patient.id,
            'full_name': patient.get_full_name(),
            'email': patient.email,
            'phone': patient.phone,
            'gender': patient.gender,
            'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else None,
            'blood_group': patient.blood_group,
            'address': patient.address,
            'is_active': patient.is_active,
            'date_joined': patient.date_joined.strftime('%Y-%m-%d'),
            'profile_picture': patient.profile_picture.url if patient.profile_picture else None,
            'statistics': {
                'total_appointments': total_appointments,
                'completed_appointments': completed_appointments,
                'pending_appointments': pending_appointments
            },
            'recent_appointments': appointment_list
        }
        
        return JsonResponse({'status': 'success', 'patient': patient_data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@admin_required
def update_user_status(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:  # Prevent self-deactivation
            user.is_active = not user.is_active
            user.save()
            return JsonResponse({
                'status': 'success',
                'is_active': user.is_active
            })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@admin_required
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:  # Prevent self-deletion
            try:
                user.delete()
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@admin_required
def doctors_section(request):
    doctors = Doctor.objects.select_related('user', 'specialization').all()
    return render(request, 'appointments/sections/doctors.html', {'doctors': doctors})

@login_required
@admin_required
def appointments_section(request):
    appointments = Appointment.objects.select_related('patient', 'doctor').all()
    return render(request, 'appointments/sections/appointments.html', {'appointments': appointments})

@login_required
@admin_required
def working_hours_section(request):
    working_hours = WorkingHours.objects.select_related('doctor').all()
    return render(request, 'appointments/sections/working_hours.html', {'working_hours': working_hours})

@login_required
@admin_required
def payments_section(request):
    payments = Payment.objects.select_related('appointment').all()
    return render(request, 'appointments/sections/payments.html', {'payments': payments})

@login_required
@admin_required
def blocked_slots_section(request):
    blocked_slots = BlockedTimeSlot.objects.select_related('doctor').all()
    return render(request, 'appointments/sections/blocked_slots.html', {'blocked_slots': blocked_slots})

@login_required
@admin_required
def schedules_section(request):
    schedules = WorkingHours.objects.select_related('doctor').all()
    return render(request, 'appointments/sections/schedules.html', {'schedules': schedules})

@login_required
@admin_required
def specializations_section(request):
    specializations = Specialization.objects.all()
    return render(request, 'appointments/sections/specializations.html', {'specializations': specializations})

@login_required
@admin_required
def activity_details(request, activity_id):
    activity = get_object_or_404(Appointment, id=activity_id)
    return render(request, 'appointments/sections/activity_details.html', {'activity': activity})

@login_required
@admin_required
def update_doctor_status(request, doctor_id):
    if request.method == 'POST':
        doctor = get_object_or_404(Doctor, id=doctor_id)
        doctor.is_available = not doctor.is_available
        doctor.save()
        return JsonResponse({'status': 'success', 'is_available': doctor.is_available})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@admin_required
def update_appointment_status(request, appointment_id):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, id=appointment_id)
        new_status = request.POST.get('status')
        if new_status in ['pending', 'confirmed', 'completed', 'cancelled']:
            appointment.status = new_status
            appointment.save()
            return JsonResponse({'status': 'success', 'new_status': new_status})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@admin_required
def update_payment_status(request, payment_id):
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)
        new_status = request.POST.get('status')
        if new_status in ['pending', 'completed', 'cancelled']:
            payment.status = new_status
            payment.save()
            return JsonResponse({'status': 'success', 'new_status': new_status})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@admin_required
def edit_admin_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('appointments:admin_dashboard')
    
    return render(request, 'appointments/admin/edit_profile.html', {
        'user': request.user
    })

@login_required
@admin_required
def disable_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:  # Prevent self-deactivation
            if user.user_type == 'doctor':
                # Deactivate doctor's account
                user.is_active = False
                user.save()
                
                # Also deactivate the doctor profile
                doctor = user.doctor
                doctor.is_available = False
                doctor.save()
                
                messages.success(request, f'Doctor {user.get_full_name()} has been deactivated.')
            else:
                # Deactivate user's account
                user.is_active = False
                user.save()
                messages.success(request, f'User {user.get_full_name()} has been deactivated.')
            return JsonResponse({'status': 'success', 'message': 'User account disabled successfully'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@admin_required
def enable_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:  # Prevent self-modification
            user.is_active = True
            user.save()
            messages.success(request, f'User account {user.get_full_name()} has been enabled.')
            return JsonResponse({'status': 'success', 'message': 'User account enabled successfully'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@admin_required
def cancel_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:  # Prevent self-deletion
            try:
                full_name = user.get_full_name()
                user.delete()
                messages.success(request, f'User account {full_name} has been deleted.')
                return JsonResponse({'status': 'success', 'message': 'User account deleted successfully'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@admin_required
def deactivate_doctor(request, doctor_id):
    """
    Sets doctor.user.is_active to enable or disable a doctor
    Only accepts POST requests
    Returns JSON response
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'failure', 'message': 'Only POST requests are allowed'}, status=405)
    
    try:
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        user = doctor.user
        
        # Check the requested action (activate or deactivate)
        action = request.POST.get('action', 'deactivate')
        
        # Set user active/inactive based on action
        if action == 'activate':
            user.is_active = True
            doctor.is_available = True
            status_message = "activated"
            notification_type = "doctor_activated"
        else:
            user.is_active = False
            doctor.is_available = False
            status_message = "deactivated"
            notification_type = "doctor_deactivated"
        
        user.save()
        doctor.save()
        
        # Create notification for admin
        Notification.objects.create(
            recipient=request.user,
            title=f"Doctor {status_message.capitalize()}",
            message=f"Dr. {user.get_full_name()} (ID: {doctor_id}) has been {status_message}.",
            notification_type=notification_type
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Dr. {user.get_full_name()} has been {status_message} successfully',
            'doctor_id': doctor_id,
            'is_active': user.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'failure',
            'message': str(e)
        }, status=500)

@login_required
@admin_required
def delete_doctor(request, doctor_id):
    """
    Permanently deletes doctor and associated user from the database
    Only accepts POST requests
    Returns JSON response or redirect based on request
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'failure', 'message': 'Only POST requests are allowed'}, status=405)
    
    try:
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        user = doctor.user
        doctor_name = user.get_full_name()
        
        # Delete doctor which also cascades to delete appointments, reviews, etc.
        # Then delete the user account
        doctor.delete()
        user.delete()
        
        # Create notification for admin
        Notification.objects.create(
            recipient=request.user,
            title="Doctor Deleted",
            message=f"Dr. {doctor_name} (ID: {doctor_id}) has been permanently deleted from the system.",
            notification_type="doctor_deleted"
        )
        
        # Success message
        messages.success(request, f'Dr. {doctor_name} has been permanently deleted')
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': f'Dr. {doctor_name} has been permanently deleted',
                'doctor_id': doctor_id
            })
        else:
            # Regular form submission - redirect to admin dashboard
            return redirect('appointments:admin_dashboard')
        
    except Exception as e:
        error_message = str(e)
        messages.error(request, f"Error deleting doctor: {error_message}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'failure',
                'message': error_message
            }, status=500)
        else:
            # Regular form submission - redirect with error
            return redirect('appointments:admin_dashboard')

def export_doctors(request):
    """
    Export doctors data as a CSV file
    """
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    from .models import Doctor

    # Create a response with CSV content type
    response = HttpResponse(content_type='text/csv')
    
    # Set the filename with current timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="doctors_export_{timestamp}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write CSV header
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Specialization', 'Qualification', 
                    'Experience', 'Status', 'Date Joined'])
    
    # Get all doctors
    doctors = Doctor.objects.select_related('user', 'specialization').all()
    
    # Write doctor data rows
    for doctor in doctors:
        writer.writerow([
            doctor.id,
            doctor.user.get_full_name(),
            doctor.user.email,
            doctor.user.phone_number,
            doctor.specialization.name if doctor.specialization else 'Not specified',
            doctor.qualification,
            f"{doctor.experience} years" if doctor.experience else 'Not specified',
            'Active' if doctor.user.is_active else 'Inactive',
            doctor.user.date_joined.strftime('%Y-%m-%d')
        ])
    
    return response 