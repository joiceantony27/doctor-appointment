from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import admin_views

app_name = 'appointments'

urlpatterns = [
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('forget-password/', views.forget_password, name='forget_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),

    # Home and Dashboard
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('patient-dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Static Pages
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('visitor-information/', views.visitor_information, name='visitor_information'),

    # Doctor Management
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/new/', views.manage_doctor_profile, name='new_doctor'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('doctors/<int:doctor_id>/edit/', views.edit_doctor_profile, name='edit_doctor_profile'),
    path('doctors/register/', views.register_doctor, name='register_doctor'),

    # Working Hours Management
    path('working-hours/update/', views.update_availability, name='update_availability'),
    path('working-hours/<int:working_hour_id>/delete/', views.delete_working_hour, name='delete_working_hour'),
    path('working-hours/<int:working_hour_id>/', views.get_working_hour, name='get_working_hour'),

    # Appointment Management
    path('appointments/book/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('appointments/my/', views.my_appointments, name='my_appointments'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/<int:appointment_id>/payment/', views.make_payment, name='make_payment'),
    path('appointments/<int:appointment_id>/approve/', views.approve_appointment, name='approve_appointment'),
    path('appointments/<int:appointment_id>/reject/', views.reject_appointment, name='reject_appointment'),
    path('appointments/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('update-appointment-status/<int:appointment_id>/', views.update_appointment_status, name='update_appointment_status'),

    # Review Management
    path('doctors/<int:doctor_id>/write-review/', views.add_review, name='write_review'),
    path('reviews/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),

    # Message Management
    path('doctors/<int:doctor_id>/send-message/', views.send_message, name='send_message'),

    # Profile Management
    path('profile/share/<int:doctor_id>/', views.share_profile, name='share_profile'),
    path('profile/edit/', views.edit_patient_profile, name='edit_patient_profile'),

    # API Endpoints
    path('api/available-slots/', views.get_available_slots, name='available_slots'),
    path('api/process-payment/<int:appointment_id>/', views.process_payment, name='process_payment'),
    path('api/doctors/<int:doctor_id>/save/', views.save_doctor, name='save_doctor'),
    path('api/doctors/<int:doctor_id>/slots/<str:date>/', views.get_available_slots, name='get_available_slots'),
    path('appointment/<int:appointment_id>/pdf/', views.generate_appointment_pdf, name='generate_appointment_pdf'),
    path('appointments/api/doctors/<int:doctor_id>/time-slots/', views.get_available_time_slots, name='get_time_slots'),
    path('api/doctors/<int:doctor_id>/working-hours/', views.get_doctor_working_hours, name='get_doctor_working_hours'),
    path('api/my-appointments/status/', views.get_appointment_status_updates, name='appointment_status_updates'),
    path('api/check-slot-availability/', views.check_slot_availability, name='check_slot_availability'),

    # Doctor Dashboard URLs
    path('save-time-slot/', views.save_time_slot, name='save_time_slot'),
    path('delete-time-slot/<int:slot_id>/', views.delete_time_slot, name='delete_time_slot'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/appointment/<int:appointment_id>/handle/', views.handle_appointment, name='handle_appointment'),
    path('doctor/appointment/<int:appointment_id>/complete/', views.complete_appointment, name='complete_appointment'),

    # Payment URLs
    path('appointments/<int:appointment_id>/process-payment/', views.process_payment, name='process_payment'),
    path('appointments/<int:appointment_id>/download-receipt/', views.download_receipt, name='download_receipt'),
    path('appointments/create_payment_order/', views.create_payment_order, name='create_payment_order'),
    path('appointments/verify_payment/', views.verify_payment, name='verify_payment'),
    path('appointments/<int:appointment_id>/download-invoice/', views.download_invoice, name='download_invoice'),

    # Notes URLs
    path('notes/', views.notes_list, name='notes_list'),
    path('notes/create/', views.create_note, name='create_note'),
    path('notes/<int:note_id>/edit/', views.edit_note, name='edit_note'),
    path('notes/<int:note_id>/delete/', views.delete_note, name='delete_note'),

    # Admin Dashboard URLs
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/dashboard/users/', admin_views.users_section, name='admin_users'),
    path('admin/dashboard/doctors/', admin_views.doctors_section, name='admin_doctors'),
    path('admin/dashboard/doctors/add/', views.AddDoctorView.as_view(), name='add_doctor'),
    path('admin/dashboard/doctors/export/', admin_views.export_doctors, name='export_doctors'),
    path('admin/dashboard/appointments/', admin_views.appointments_section, name='admin_appointments'),
    path('admin/dashboard/working-hours/', admin_views.working_hours_section, name='admin_working_hours'),
    path('admin/dashboard/payments/', admin_views.payments_section, name='admin_payments'),
    path('admin/dashboard/blocked-slots/', admin_views.blocked_slots_section, name='admin_blocked_slots'),
    path('admin/dashboard/schedules/', admin_views.schedules_section, name='admin_schedules'),
    path('admin/dashboard/specializations/', admin_views.specializations_section, name='admin_specializations'),
    path('admin/activity/<int:activity_id>/', admin_views.activity_details, name='admin_activity_details'),
    path('admin/user/<int:user_id>/', admin_views.get_user_details, name='admin_user_details'),
    path('admin/user/<int:user_id>/update-status/', admin_views.update_user_status, name='admin_update_user_status'),
    path('admin/user/<int:user_id>/delete/', admin_views.delete_user, name='admin_delete_user'),
    path('admin/profile/edit/', admin_views.edit_admin_profile, name='edit_admin_profile'),
    path('admin/user/<int:user_id>/disable/', admin_views.disable_user, name='disable_user'),
    path('admin/user/<int:user_id>/enable/', admin_views.enable_user, name='admin_enable_user'),
    path('admin/user/<int:user_id>/cancel/', admin_views.cancel_user, name='cancel_user'),
    path('admin/patient/<int:id>/', admin_views.view_patient_detail, name='view_patient'),

    # Admin AJAX URLs
    path('admin/doctor/<int:doctor_id>/update-status/', admin_views.update_doctor_status, name='admin_update_doctor_status'),
    path('admin/appointment/<int:appointment_id>/update-status/', admin_views.update_appointment_status, name='admin_update_appointment_status'),
    path('admin/payment/<int:payment_id>/update-status/', admin_views.update_payment_status, name='admin_update_payment_status'),
    path('admin/deactivate_doctor/<int:doctor_id>/', admin_views.deactivate_doctor, name='deactivate_doctor'),
    path('admin/delete_doctor/<int:doctor_id>/', admin_views.delete_doctor, name='delete_doctor'),

    # Doctor-Patient Notes
    path('create-doctor-note/', views.create_doctor_note, name='create_doctor_note'),
    path('reply-to-note/<int:note_id>/', views.reply_to_patient_note, name='reply_to_patient_note'),
    path('mark-note-as-read/<int:note_id>/', views.mark_note_as_read, name='mark_note_as_read'),

    # New API endpoint for reschedule
    path('api/reschedule/<int:appointment_id>/', views.reschedule_appointment_api, name='reschedule_appointment_api'),
    
    # Health check endpoint
    path('health/', views.health_check, name='health_check'),
]