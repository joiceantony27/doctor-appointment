// Document Ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Handle alert dismissal
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        if (!alert.classList.contains('alert-permanent')) {
            setTimeout(function() {
                alert.classList.add('fade');
                setTimeout(function() {
                    alert.remove();
                }, 150);
            }, 5000);
        }
    });

    // Handle save doctor functionality
    var saveButtons = document.querySelectorAll('.save-doctor');
    saveButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var doctorId = this.dataset.doctorId;
            fetch('/api/save-doctor/' + doctorId + '/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.innerHTML = data.is_saved ? 
                        '<i class="fas fa-bookmark"></i> Saved' : 
                        '<i class="far fa-bookmark"></i> Save';
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });

    // Share functionality
    var shareButtons = document.querySelectorAll('.share-button');
    shareButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var url = this.dataset.url;
            var platform = this.dataset.platform;
            
            var shareUrls = {
                facebook: 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
                twitter: 'https://twitter.com/intent/tweet?url=' + encodeURIComponent(url),
                whatsapp: 'https://api.whatsapp.com/send?text=' + encodeURIComponent(url)
            };

            if (platform === 'copy') {
                navigator.clipboard.writeText(url).then(function() {
                    showToast('Link copied to clipboard!');
                }).catch(function(err) {
                    console.error('Failed to copy text: ', err);
                });
            } else if (shareUrls[platform]) {
                window.open(shareUrls[platform], '_blank');
            }
        });
    });
});

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Toast notification function
function showToast(message) {
    var toast = document.createElement('div');
    toast.className = 'toast show position-fixed bottom-0 end-0 m-3';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(function() {
        toast.remove();
    }, 3000);
} 