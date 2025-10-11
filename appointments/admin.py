from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Doctor, Appointment, Review, Schedule, Payment, Specialization, WorkingHours, BlockedTimeSlot, Notification
from django.core.exceptions import ValidationError

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_active')
    list_filter = ('user_type', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'user_type', 'phone_number', 'address', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'specialization', 'experience', 'consultation_fee', 'is_available', 'created_at')
    list_filter = ('specialization', 'is_available', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'specialization__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {'fields': ('user', 'profile_picture')}),
        ('Professional Information', {
            'fields': (
                'specialization', 
                'experience', 
                'education', 
                'bio',
                'consultation_fee'
            )
        }),
        ('Availability', {
            'fields': (
                'is_available',
                'available_days',
                'available_hours'
            )
        }),
        ('Statistics', {
            'fields': (
                'created_at',
                'updated_at'
            )
        })
    )

    def get_name(self, obj):
        return f"Dr. {obj.user.get_full_name()}"
    get_name.short_description = 'Name'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'time_slot', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'date', 'doctor')
    search_fields = ('patient__username', 'doctor__user__username', 'doctor__user__first_name', 'doctor__user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-date', '-time_slot')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'doctor_profile'):
                queryset = queryset.filter(doctor=request.user.doctor_profile)
            else:
                queryset = queryset.filter(patient=request.user)
        return queryset

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('patient__username', 'doctor__user__username', 'comment')
    readonly_fields = ('created_at',)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'doctor')
    search_fields = ('doctor__user__username',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'amount', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('appointment__patient__username', 'appointment__doctor__user__username', 'transaction_id')
    readonly_fields = ('created_at', 'invoice_number')
    
    fieldsets = (
        ('Payment Details', {'fields': ('appointment', 'amount', 'tax', 'total_amount', 'status', 'payment_method', 'transaction_id')}),
        ('Invoice Information', {'fields': ('invoice_number', 'invoice_pdf')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )

@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'get_day_of_week_display', 'start_time', 'end_time', 'is_active')
    list_filter = ('doctor', 'day_of_week', 'is_active')
    ordering = ('doctor', 'day_of_week', 'start_time')
    search_fields = ('doctor__user__first_name', 'doctor__user__last_name')
    
    def get_day_of_week_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_of_week_display.short_description = 'Day of Week'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['day_of_week'].widget.attrs.update({'class': 'form-select'})
        return form

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            # Check if working hours already exist for this day
            if WorkingHours.objects.filter(doctor=obj.doctor, day_of_week=obj.day_of_week).exists():
                raise ValidationError('Working hours already exist for this day')
        super().save_model(request, obj, form, change)

@admin.register(BlockedTimeSlot)
class BlockedTimeSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'date', 'start_time', 'end_time', 'reason', 'is_recurring')
    list_filter = ('doctor', 'date', 'is_recurring')
    search_fields = ('doctor__user__username', 'doctor__user__email', 'reason')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('date', 'start_time')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'title', 'message', 'notification_type', 'related_link')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(recipient=request.user)
        return queryset
