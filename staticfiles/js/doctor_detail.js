document.addEventListener('DOMContentLoaded', function() {
    // WebRTC variables
    let localStream;
    let remoteStream;
    let peerConnection;
    let isCallActive = false;

    // Initialize WebRTC configuration
    const configuration = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' }
        ]
    };

    // Consultation type buttons
    const consultationBtns = document.querySelectorAll('.consultation-btn');
    consultationBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            consultationBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            updateBookingButton();
        });
    });

    // Time slot buttons
    const timeSlotBtns = document.querySelectorAll('.time-slot-btn');
    timeSlotBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            timeSlotBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            updateBookingButton();
        });
    });

    // Share button
    const shareBtn = document.querySelector('.share-btn');
    if (shareBtn) {
        shareBtn.addEventListener('click', function() {
            const shareModal = new bootstrap.Modal(document.getElementById('shareModal'));
            shareModal.show();
        });
    }

    // Save button
    const saveBtn = document.querySelector('.save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', async function() {
            const doctorId = this.dataset.doctorId;
            try {
                const response = await fetch(`/api/doctors/${doctorId}/save/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    this.classList.toggle('saved');
                    const isSaved = this.classList.contains('saved');
                    this.innerHTML = `<i class="fas fa-heart"></i> ${isSaved ? 'Saved' : 'Save'}`;
                }
            } catch (error) {
                console.error('Error saving doctor:', error);
            }
        });
    }

    // Book Appointment button
    const bookBtn = document.getElementById('bookAppointmentBtn');
    if (bookBtn) {
        bookBtn.addEventListener('click', async function() {
            const consultationType = document.querySelector('.consultation-btn.active').dataset.type;
            const timeSlot = document.querySelector('.time-slot-btn.active')?.dataset.slot;
            
            if (!timeSlot) {
                alert('Please select a time slot');
                return;
            }

            if (consultationType === 'video') {
                startVideoConsultation();
            } else {
                bookInPersonAppointment(timeSlot);
            }
        });
    }

    // Video consultation functions
    async function startVideoConsultation() {
        try {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            document.getElementById('localVideo').srcObject = localStream;
            
            // Initialize WebRTC peer connection
            peerConnection = new RTCPeerConnection(configuration);
            
            // Add local stream to peer connection
            localStream.getTracks().forEach(track => {
                peerConnection.addTrack(track, localStream);
            });

            // Handle incoming stream
            peerConnection.ontrack = event => {
                document.getElementById('remoteVideo').srcObject = event.streams[0];
            };

            // Show video call modal
            const videoModal = new bootstrap.Modal(document.getElementById('videoCallModal'));
            videoModal.show();

            // Initialize call controls
            initializeCallControls();
            
            // Connect to signaling server and start call
            // This part would need to be implemented with your backend
            connectToSignalingServer();

        } catch (error) {
            console.error('Error starting video consultation:', error);
            alert('Could not start video consultation. Please check your camera and microphone permissions.');
        }
    }

    async function bookInPersonAppointment(timeSlot) {
        try {
            const response = await fetch('/api/appointments/book/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    doctor_id: document.querySelector('.save-btn').dataset.doctorId,
                    time_slot: timeSlot,
                    appointment_type: 'in-person'
                })
            });

            if (response.ok) {
                const result = await response.json();
                window.location.href = result.payment_url;
            } else {
                alert('Could not book appointment. Please try again.');
            }
        } catch (error) {
            console.error('Error booking appointment:', error);
            alert('An error occurred while booking the appointment.');
        }
    }

    function initializeCallControls() {
        const toggleMicBtn = document.getElementById('toggleMicBtn');
        const toggleVideoBtn = document.getElementById('toggleVideoBtn');
        const endCallBtn = document.getElementById('endCallBtn');

        toggleMicBtn.addEventListener('click', () => {
            const audioTrack = localStream.getAudioTracks()[0];
            audioTrack.enabled = !audioTrack.enabled;
            toggleMicBtn.innerHTML = `<i class="fas fa-microphone${audioTrack.enabled ? '' : '-slash'}"></i>`;
        });

        toggleVideoBtn.addEventListener('click', () => {
            const videoTrack = localStream.getVideoTracks()[0];
            videoTrack.enabled = !videoTrack.enabled;
            toggleVideoBtn.innerHTML = `<i class="fas fa-video${videoTrack.enabled ? '' : '-slash'}"></i>`;
        });

        endCallBtn.addEventListener('click', endCall);
    }

    function endCall() {
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
        }
        if (peerConnection) {
            peerConnection.close();
        }
        const videoModal = bootstrap.Modal.getInstance(document.getElementById('videoCallModal'));
        videoModal.hide();
    }

    // Share functions
    window.shareOnWhatsApp = function() {
        const url = encodeURIComponent(window.location.href);
        window.open(`https://wa.me/?text=${url}`);
    };

    window.shareOnFacebook = function() {
        const url = encodeURIComponent(window.location.href);
        window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}`);
    };

    window.shareOnTwitter = function() {
        const url = encodeURIComponent(window.location.href);
        const text = encodeURIComponent('Check out this doctor\'s profile!');
        window.open(`https://twitter.com/intent/tweet?url=${url}&text=${text}`);
    };

    window.copyLink = function() {
        navigator.clipboard.writeText(window.location.href).then(() => {
            alert('Link copied to clipboard!');
        });
    };

    // Helper function to get CSRF token
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

    // Update booking button state
    function updateBookingButton() {
        const timeSlot = document.querySelector('.time-slot-btn.active');
        const bookBtn = document.getElementById('bookAppointmentBtn');
        bookBtn.disabled = !timeSlot;
    }
}); 