// WebRTC configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
};

let localStream = null;
let remoteStream = null;
let peerConnection = null;
let roomId = null;
let isInitiator = false;

// DOM elements
const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');
const muteAudioBtn = document.getElementById('muteAudio');
const muteVideoBtn = document.getElementById('muteVideo');
const endCallBtn = document.getElementById('endCall');

// WebSocket connection for signaling
const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
const wsPath = `${wsScheme}://${window.location.host}/ws/video/${appointmentId}/`;
const socket = new WebSocket(wsPath);

// WebSocket event handlers
socket.onmessage = async function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'room_created':
            handleRoomCreated(data);
            break;
        case 'offer':
            handleOffer(data);
            break;
        case 'answer':
            handleAnswer(data);
            break;
        case 'candidate':
            handleCandidate(data);
            break;
        case 'ready':
            if (isInitiator) {
                makeCall();
            }
            break;
    }
};

socket.onclose = function(event) {
    console.log('WebSocket connection closed');
};

// Initialize video call
async function initCall() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({
            audio: true,
            video: true
        });
        localVideo.srcObject = localStream;
        
        createPeerConnection();
        
        socket.send(JSON.stringify({
            type: 'join',
            room: appointmentId
        }));
    } catch (error) {
        console.error('Error accessing media devices:', error);
    }
}

// Create RTCPeerConnection
function createPeerConnection() {
    peerConnection = new RTCPeerConnection(configuration);
    
    // Add local stream
    localStream.getTracks().forEach(track => {
        peerConnection.addTrack(track, localStream);
    });
    
    // Handle incoming stream
    peerConnection.ontrack = event => {
        remoteVideo.srcObject = event.streams[0];
        remoteStream = event.streams[0];
    };
    
    // Handle ICE candidates
    peerConnection.onicecandidate = event => {
        if (event.candidate) {
            socket.send(JSON.stringify({
                type: 'candidate',
                candidate: event.candidate
            }));
        }
    };
}

// Make call (create and send offer)
async function makeCall() {
    try {
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        socket.send(JSON.stringify({
            type: 'offer',
            offer: offer
        }));
    } catch (error) {
        console.error('Error creating offer:', error);
    }
}

// Handle received offer
async function handleOffer(data) {
    if (!peerConnection) {
        createPeerConnection();
    }
    
    try {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        
        socket.send(JSON.stringify({
            type: 'answer',
            answer: answer
        }));
    } catch (error) {
        console.error('Error handling offer:', error);
    }
}

// Handle received answer
async function handleAnswer(data) {
    try {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
    } catch (error) {
        console.error('Error handling answer:', error);
    }
}

// Handle received ICE candidate
async function handleCandidate(data) {
    try {
        await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
    } catch (error) {
        console.error('Error handling ICE candidate:', error);
    }
}

// Handle room created
function handleRoomCreated(data) {
    roomId = data.room;
    isInitiator = data.is_initiator;
}

// UI Controls
muteAudioBtn.addEventListener('click', () => {
    const audioTrack = localStream.getAudioTracks()[0];
    audioTrack.enabled = !audioTrack.enabled;
    muteAudioBtn.innerHTML = audioTrack.enabled ? 
        '<i class="fas fa-microphone"></i>' : 
        '<i class="fas fa-microphone-slash"></i>';
});

muteVideoBtn.addEventListener('click', () => {
    const videoTrack = localStream.getVideoTracks()[0];
    videoTrack.enabled = !videoTrack.enabled;
    muteVideoBtn.innerHTML = videoTrack.enabled ? 
        '<i class="fas fa-video"></i>' : 
        '<i class="fas fa-video-slash"></i>';
});

endCallBtn.addEventListener('click', () => {
    if (peerConnection) {
        peerConnection.close();
    }
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
    }
    if (remoteStream) {
        remoteStream.getTracks().forEach(track => track.stop());
    }
    window.location.href = '/appointments/';
});

// Picture-in-Picture support
localVideo.addEventListener('click', async () => {
    try {
        if (document.pictureInPictureElement) {
            await document.exitPictureInPicture();
        } else if (document.pictureInPictureEnabled) {
            await localVideo.requestPictureInPicture();
        }
    } catch (error) {
        console.error('Error toggling picture-in-picture:', error);
    }
});

// Initialize call when page loads
document.addEventListener('DOMContentLoaded', initCall); 