from .models import Notification

def notifications(request):
    """Add notifications to template context"""
    if request.user.is_authenticated:
        return {
            'notifications': Notification.objects.filter(user=request.user).order_by('-created_at')[:5],
            'unread_notifications_count': Notification.get_unread_count(request.user)
        }
    return {} 