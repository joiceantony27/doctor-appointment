from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import mark_safe
from django.conf import settings
import json
import time

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='patient')
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    @property
    def is_doctor(self):
        return self.user_type == 'doctor'

    def __str__(self):
        return self.username

class Specialization(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fa-user-md')  # Font Awesome icon class
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.ForeignKey(Specialization, on_delete=models.SET_NULL, null=True)
    experience = models.IntegerField()
    education = models.TextField()
    bio = models.TextField()
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    available_days = models.CharField(max_length=255, help_text="Comma-separated days, e.g., Monday,Tuesday")
    available_hours = models.CharField(max_length=255, help_text="Comma-separated hours, e.g., 9:00-12:00,14:00-17:00")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

    def get_average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0

    def get_total_reviews(self):
        return self.reviews.count()

    def get_available_days_list(self):
        return self.available_days.split(',') if self.available_days else []

    def get_available_hours_list(self):
        return self.available_hours.split(',') if self.available_hours else []

    class Meta:
        ordering = ['-created_at']

class WorkingHours(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    appointment_duration = models.IntegerField(default=30, help_text="Duration of each appointment in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['doctor', 'day_of_week', 'is_active']),
            models.Index(fields=['doctor', 'start_time']),
        ]

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.start_time.strftime('%I:%M %p')} to {self.end_time.strftime('%I:%M %p')}"

    def clean(self):
        if not self.start_time or not self.end_time:
            return

        if self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time')
        
        # Validate appointment duration
        if self.appointment_duration <= 0:
            raise ValidationError('Appointment duration must be greater than 0 minutes')
        
        # Calculate total minutes between start and end time
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        total_minutes = end_minutes - start_minutes
        
        if total_minutes < self.appointment_duration:
            raise ValidationError('Time slot duration must be at least equal to appointment duration')
        
        # Check for overlapping time slots for the same doctor and day
        overlapping = WorkingHours.objects.filter(
            doctor=self.doctor,
            day_of_week=self.day_of_week,
            is_active=True
        ).exclude(pk=self.pk)
        
        # Convert current slot times to minutes for easier comparison
        current_start_mins = start_minutes
        current_end_mins = end_minutes
        
        for slot in overlapping:
            # Convert existing slot times to minutes
            slot_start_mins = slot.start_time.hour * 60 + slot.start_time.minute
            slot_end_mins = slot.end_time.hour * 60 + slot.end_time.minute
            
            # Check if slots overlap
            if (current_start_mins < slot_end_mins and current_end_mins > slot_start_mins):
                # If new slot completely contains existing slot, delete the existing slot
                if current_start_mins <= slot_start_mins and current_end_mins >= slot_end_mins:
                    slot.delete()
                    continue
                
                # If existing slot completely contains new slot or there's any overlap,
                # merge them into one continuous slot
                new_start_mins = min(current_start_mins, slot_start_mins)
                new_end_mins = max(current_end_mins, slot_end_mins)
                
                # Update the current slot's times
                self.start_time = timezone.datetime.strptime(f"{new_start_mins//60:02d}:{new_start_mins%60:02d}", "%H:%M").time()
                self.end_time = timezone.datetime.strptime(f"{new_end_mins//60:02d}:{new_end_mins%60:02d}", "%H:%M").time()
                
                # Delete the overlapping slot
                slot.delete()
                
                # Update the current minutes for further comparisons
                current_start_mins = new_start_mins
                current_end_mins = new_end_mins

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class BlockedTimeSlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.date} {self.start_time}-{self.end_time} - {self.reason}"

    def overlaps_with(self, other_start, other_end):
        return not (self.end_time <= other_start or self.start_time >= other_end)

class TimeSlot(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('booked', 'Booked'),
    )
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['doctor', 'date', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"
    
    @property
    def is_booked(self):
        return self.status == 'booked'
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def save(self, *args, **kwargs):
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time")
        super().save(*args, **kwargs)

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
    )

    RESPONSE_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed')
    )

    APPOINTMENT_TYPE_CHOICES = (
        ('regular', 'Regular Checkup'),
        ('follow_up', 'Follow-up Visit'),
        ('consultation', 'Consultation'),
        ('emergency', 'Emergency'),
        ('video', 'Video Consultation'),
        ('specialist', 'Specialist Visit')
    )

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='doctor_appointments')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_appointments')
    date = models.DateField()
    time_slot = models.CharField(max_length=15, help_text="Time slot in HH:MM-HH:MM format")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_status = models.CharField(max_length=20, choices=RESPONSE_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES, default='regular')
    is_video_consultation = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_confirmed = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    payment_time = models.DateTimeField(null=True, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    invoice_url = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-date', '-time_slot']
        unique_together = ['doctor', 'date', 'time_slot']

    def __str__(self):
        return f"Appointment with {self.doctor.user.get_full_name()} on {self.date} at {self.time_slot}"

    def clean(self):
        # Validate time slot format
        if self.time_slot:
            try:
                # Split the time slot into start and end times
                start_time, end_time = self.time_slot.split('-')
                # Validate both start and end times
                time.strptime(start_time.strip(), '%H:%M')
                time.strptime(end_time.strip(), '%H:%M')
            except (ValueError, AttributeError):
                raise ValidationError({
                    'time_slot': ['Time slot must be in HH:MM-HH:MM format (e.g., 09:00-10:00)']
                })
        
        # Check for overlapping appointments
        if self.date and self.time_slot:
            overlapping = Appointment.objects.filter(
                doctor=self.doctor,
                date=self.date,
                time_slot=self.time_slot,
                status__in=['accepted', 'scheduled']
            ).exclude(pk=self.pk)
            
            if overlapping.exists():
                raise ValidationError({
                    'time_slot': ['This time slot is already booked']
                })

    def save(self, *args, **kwargs):
        # Update is_video_consultation based on appointment_type
        self.is_video_consultation = (self.appointment_type == 'video')
        # Clean and validate before saving
        self.clean()
        super().save(*args, **kwargs)

    def get_total_fee(self):
        return self.doctor.consultation_fee

    def get_payment_status_display(self):
        return dict(self.PAYMENT_STATUS_CHOICES).get(self.payment_status, 'Unknown')

    def accept_appointment(self):
        self.response_status = 'accepted'
        self.status = 'scheduled'
        self.save()

    def reject_appointment(self, reason=None):
        self.response_status = 'rejected'
        self.status = 'rejected'
        self.rejection_reason = reason
        self.save()

    def mark_as_completed(self):
        self.status = 'completed'
        self.save()

    def can_reschedule(self):
        return self.status in ['pending', 'accepted', 'scheduled']

    def can_cancel(self):
        return self.status in ['pending', 'accepted', 'scheduled']

    def get_status_color(self):
        status_colors = {
            'pending': 'warning',
            'accepted': 'info',
            'rejected': 'danger',
            'scheduled': 'primary',
            'completed': 'success',
            'canceled': 'secondary'
        }
        return status_colors.get(self.status, 'secondary')

    def get_end_time(self):
        """
        Get the end time of the appointment based on the time slot.
        The time_slot is in format 'HH:MM-HH:MM'.
        Returns the end time in HH:MM format.
        """
        try:
            _, end_time = self.time_slot.split('-')
            return end_time.strip()
        except (ValueError, AttributeError):
            # If there's any error parsing the time slot, return a default duration
            # This is a fallback that shouldn't normally be needed due to validation
            try:
                start_time = self.time_slot.strip()
                # Parse the start time
                hours, minutes = map(int, start_time.split(':'))
                # Add default duration (30 minutes)
                minutes += 30
                if minutes >= 60:
                    hours += minutes // 60
                    minutes = minutes % 60
                hours = hours % 24  # Handle day wraparound
                return f"{hours:02d}:{minutes:02d}"
            except:
                return "00:00"  # Ultimate fallback

class Schedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=[(i, i) for i in range(1, 8)])
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Schedule for Dr. {self.doctor.user.get_full_name()} on day {self.day_of_week}"

class Review(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='reviews')
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['doctor', 'patient']

    def __str__(self):
        return f"Review by {self.patient.get_full_name()} for {self.doctor.user.get_full_name()}"

class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)

    def __str__(self):
        return f"Payment for appointment {self.appointment.id} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Payment.objects.order_by('-id').first()
            invoice_num = 1 if not last_invoice else last_invoice.id + 1
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m')}-{invoice_num:04d}"
        super().save(*args, **kwargs)

class SavedDoctor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_doctors')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'doctor')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved Dr. {self.doctor.user.get_full_name()}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.sender.get_full_name()} to {self.recipient.get_full_name()}"

    def mark_as_read(self):
        self.is_read = True
        self.save()

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=15, null=True, blank=True)
    medical_history = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - Patient"

    class Meta:
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('appointment', 'Appointment'),
        ('message', 'Message'),
        ('review', 'Review'),
        ('system', 'System'),
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    related_link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title} for {self.recipient.username}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()

    @property
    def short_message(self):
        return self.message[:100] + '...' if len(self.message) > 100 else self.message

    @classmethod
    def create_notification(cls, recipient, title, message, notification_type, related_link=None):
        return cls.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            related_link=related_link
        )

class Note(models.Model):
    CATEGORY_CHOICES = (
        ('MEDICATION', 'Medication'),
        ('SYMPTOMS', 'Symptoms'),
        ('QUESTIONS', 'Questions'),
        ('DIET', 'Diet'),
        ('EXERCISE', 'Exercise'),
        ('OTHER', 'Other')
    )

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    share_with_doctor = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.title}"

    @property
    def word_count(self):
        return len(self.content.split())

class DoctorPatientNote(models.Model):
    """Model for direct communication between doctors and patients"""
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notes')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='received_notes')
    message = models.TextField()
    reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    is_read_by_doctor = models.BooleanField(default=False)
    is_read_by_patient = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f'Note from {self.patient.get_full_name()} to Dr. {self.doctor.user.get_full_name()}'
