from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Doctor, Appointment, Review, Specialization
from django.utils import timezone
from datetime import datetime
import bleach
import time
from django.contrib.auth.hashers import make_password

class UserRegistrationForm(forms.ModelForm):
    user_type = forms.ChoiceField(choices=[('patient', 'Patient'), ('doctor', 'Doctor'), ('admin', 'Admin')], required=True)
    specialization = forms.ModelChoiceField(queryset=Specialization.objects.all(), required=False)
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'user_type', 'profile_picture', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("Username is required.")
        if not username.isalnum():
            raise forms.ValidationError("Username must be alphanumeric.")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise forms.ValidationError("First name is required.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise forms.ValidationError("Last name is required.")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")
        # Add additional validation for phone number format if needed
        return phone_number

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if not address:
            raise forms.ValidationError("Address is required.")
        return address

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError("Password is required.")
        if len(password1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        if not any(char.isupper() for char in password1):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in password1):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        if not any(char.isdigit() for char in password1):
            raise forms.ValidationError("Password must contain at least one digit.")
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for char in password1):
            raise forms.ValidationError("Password must contain at least one special character.")
        return password1

    def clean_password2(self):
        password2 = self.cleaned_data.get('password2')
        password1 = self.cleaned_data.get('password1')
        if not password2:
            raise forms.ValidationError("Please confirm your password.")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        specialization = cleaned_data.get('specialization')
        if user_type == 'doctor' and not specialization:
            raise forms.ValidationError("Specialization is required for doctors.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = self.cleaned_data['user_type']
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user

class DoctorProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Doctor
        fields = [
            'specialization',
            'experience',
            'education',
            'bio',
            'profile_picture',
            'consultation_fee',
            'is_available',
            'available_days',
            'available_hours'
        ]
        widgets = {
            'specialization': forms.Select(attrs={'class': 'form-select'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'education': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'consultation_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'available_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Monday,Tuesday,Wednesday'}),
            'available_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00-12:00,14:00-17:00'})
        }
        help_texts = {
            'specialization': 'Select your medical specialization',
            'experience': 'Enter your years of medical experience',
            'education': 'List your educational qualifications',
            'bio': 'Tell us about your professional background and expertise',
            'profile_picture': 'Upload a professional profile picture',
            'consultation_fee': 'Enter your consultation fee',
            'is_available': 'Check if you are currently accepting new patients',
            'available_days': 'Comma-separated days (e.g., Monday,Tuesday,Wednesday)',
            'available_hours': 'Comma-separated time ranges (e.g., 9:00-12:00,14:00-17:00)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
        
        # Debug print for file field
        if kwargs.get('files'):
            print(f"Files in form initialization: {kwargs['files'].keys()}")

    def save(self, commit=True):
        doctor = super().save(commit=False)
        
        # Debug print - profile picture field
        if 'profile_picture' in self.files:
            file_obj = self.files['profile_picture']
            print(f"Profile picture in form save: {file_obj.name}, size: {file_obj.size}")
        
        # Create or update associated user
        if not hasattr(doctor, 'user') or not doctor.user:
            # Create new user
            user = User.objects.create(
                username=self.cleaned_data['email'],
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                user_type='doctor'
            )
            doctor.user = user
        else:
            # Update existing user
            doctor.user.first_name = self.cleaned_data['first_name']
            doctor.user.last_name = self.cleaned_data['last_name']
            doctor.user.email = self.cleaned_data['email']
            doctor.user.save()
        
        if commit:
            doctor.save()
        return doctor

    def clean_qualifications(self):
        qualifications = self.cleaned_data.get('qualifications')
        if qualifications:
            # Split qualifications by newline and remove empty lines
            qualifications = '\n'.join([q.strip() for q in qualifications.split('\n') if q.strip()])
        return qualifications

    def clean_bio(self):
        bio = self.cleaned_data.get('bio')
        if bio:
            # Clean HTML tags if any
            bio = bleach.clean(bio, tags=['p', 'br', 'strong', 'em'], strip=True)
        return bio

class DoctorRegistrationForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['specialization', 'experience', 'consultation_fee']

    def clean_specialization(self):
        specialization = self.cleaned_data.get('specialization')
        if not specialization:
            raise forms.ValidationError("Specialization is required.")
        return specialization

    def clean_experience(self):
        experience = self.cleaned_data.get('experience')
        if experience is None:
            raise forms.ValidationError("Experience is required.")
        if experience < 0:
            raise forms.ValidationError("Experience cannot be negative.")
        return experience

    def clean_consultation_fee(self):
        consultation_fee = self.cleaned_data.get('consultation_fee')
        if consultation_fee is None:
            raise forms.ValidationError("Consultation fee is required.")
        if consultation_fee < 0:
            raise forms.ValidationError("Consultation fee cannot be negative.")
        return consultation_fee

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date', 'time_slot']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True
            }),
            'time_slot': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            })
        }

    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        if self.doctor:
            self.fields['date'].widget.attrs.update({
                'min': timezone.now().date().isoformat()
            })
            
            # Initialize time slots
            self.fields['time_slot'].choices = []
            
            # Add validation for date field
            self.fields['date'].validators = [
                forms.validators.MinValueValidator(timezone.now().date())
            ]

    def clean_time_slot(self):
        time_slot = self.cleaned_data.get('time_slot')
        if time_slot:
            try:
                # Validate time format
                time.strptime(time_slot, '%H:%M')
            except ValueError:
                raise forms.ValidationError('Time slot must be in HH:MM format')
            
            # Validate time slot length
            if len(time_slot) != 5:
                raise forms.ValidationError('Time slot must be exactly 5 characters (HH:MM)')
            
            # Validate hours and minutes
            hours, minutes = time_slot.split(':')
            if not (0 <= int(hours) <= 23):
                raise forms.ValidationError('Hours must be between 00 and 23')
            if not (0 <= int(minutes) <= 59):
                raise forms.ValidationError('Minutes must be between 00 and 59')
        
        return time_slot

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time_slot = cleaned_data.get('time_slot')
        
        if not date:
            raise forms.ValidationError({
                'date': ['Please select a valid date']
            })
            
        if not time_slot:
            raise forms.ValidationError({
                'time_slot': ['Please select a valid time slot']
            })
            
        if date and time_slot and self.doctor:
            # Check if the selected date is one of the doctor's available days
            available_days = self.doctor.get_available_days_list()
            selected_day = date.strftime('%A')
            if selected_day not in available_days:
                raise forms.ValidationError({
                    'date': [f"Doctor is not available on {selected_day}"]
                })
            
            # Check if the selected time slot is within the doctor's available hours
            available_hours = self.doctor.get_available_hours_list()
            selected_time = datetime.datetime.strptime(time_slot, '%H:%M').time()
            
            for hour_range in available_hours:
                start, end = hour_range.split('-')
                start_time = datetime.datetime.strptime(start.strip(), '%H:%M').time()
                end_time = datetime.datetime.strptime(end.strip(), '%H:%M').time()
                
                if start_time <= selected_time <= end_time:
                    break
            else:
                raise forms.ValidationError({
                    'time_slot': [f"Selected time is not within doctor's available hours"]
                })

            # Check for existing appointments at the same time
            existing_appointments = Appointment.objects.filter(
                doctor=self.doctor,
                date=date,
                time_slot=time_slot
            )
            if existing_appointments.exists():
                raise forms.ValidationError({
                    '__all__': ["This time slot is already booked"]
                })

        return cleaned_data

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class AddDoctorForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    specialization = forms.ModelChoiceField(
        queryset=Specialization.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    experience_years = forms.IntegerField(
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
    )

    class Meta:
        model = Doctor
        fields = ['first_name', 'last_name', 'email', 'password', 'confirm_password', 
                 'phone_number', 'specialization', 'experience_years', 'profile_picture', 'bio']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        # Create User instance
        user = User.objects.create(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=make_password(self.cleaned_data['password']),
            is_doctor=True,
            is_active=True,
            user_type='doctor'
        )

        # Create Doctor instance
        doctor = super().save(commit=False)
        doctor.user = user
        doctor.specialization = self.cleaned_data['specialization']
        doctor.experience = self.cleaned_data['experience_years']
        doctor.phone_number = self.cleaned_data['phone_number']
        if self.cleaned_data.get('profile_picture'):
            doctor.profile_picture = self.cleaned_data['profile_picture']
        doctor.bio = self.cleaned_data.get('bio', '')
        doctor.is_available = True

        if commit:
            doctor.save()
        return doctor 