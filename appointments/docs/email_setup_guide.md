# Gmail Configuration Guide for Prescripto Application

## Issue: "Username and Password not accepted" Error

This error occurs because Google has increased security measures and doesn't allow less secure apps to access Gmail accounts directly. You need to set up an "App Password" to allow the Django application to send emails through your Gmail account.

## Solution: Set Up an App Password

Follow these steps to create an app password for your Gmail account:

### Step 1: Enable 2-Step Verification

1. Go to your Google Account settings: https://myaccount.google.com/
2. Select "Security" from the left sidebar
3. Under "Signing in to Google," select "2-Step Verification"
4. Follow the steps to turn on 2-Step Verification

### Step 2: Create an App Password

1. Go back to the Security page
2. Under "Signing in to Google," select "App passwords" (you'll only see this option if 2-Step Verification is enabled)
3. At the bottom, select "Select app" and choose "Other (Custom name)"
4. Enter "Prescripto" or any name you'll recognize
5. Click "Generate"
6. Google will display a 16-character app password. **Copy this password**

### Step 3: Update Your Django Settings

1. Open the `settings.py` file in your Django project
2. Locate the email configuration section
3. Update the settings with your Gmail address and the app password:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'  # Your actual Gmail address
EMAIL_HOST_PASSWORD = 'your-app-password'  # The 16-character app password you generated
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

4. Replace 'your-email@gmail.com' with your actual Gmail address
5. Replace 'your-app-password' with the 16-character app password you copied

### Step 4: Restart Your Django Server

After making these changes, restart your Django development server for the changes to take effect.

## Important Notes

- Never share your app password with anyone
- If you need to revoke access, you can delete the app password from your Google Account security settings
- You may need to create different app passwords for different devices or applications

If you continue to experience issues, consult the [Google Account Help](https://support.google.com/accounts/answer/185833) for more information about app passwords. 