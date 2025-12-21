/**
 * Modern WebRTC & UI Manager for DefAI Videoconference
 * Implements Google Meet-like layout logic (Grid/Spotlight),
 * Glassmorphism UI controls, and robust state management.
 */

// ==========================================
// STATE MANAGEMENT
// ==========================================
const State = {
    localStream: null,
    screenStream: null,
    peers: {}, // userId -> SimplePeer instance
    participants: new Map(), // userId -> { name, isAudioOn, isVideoOn, isSharingScreen, ... }

    // UI State
    layoutMode: 'grid', // 'grid' | 'spotlight'
    spotlightId: null, // userId focused in spotlight
    isSidebarOpen: false,
    activeSidebarTab: 'participants', // 'participants' | 'chat'

    // Media State
    audioEnabled: true,
    videoEnabled: true,
    isSharingScreen: false,

    // Devices
    videoDevice: null,
    audioDevice: null
};

// ==========================================
// CONFIGURATION & UTILS
// ==========================================
const socket = io();
const DOM = {
    layoutContainer: document.getElementById('layout-container'),
    preflightModal: document.getElementById('preflight-modal'),
    sidePanel: document.getElementById('side-panel'),
    toastZone: document.getElementById('toast-zone'),

    // Buttons
    btnMic: document.getElementById('btn-mic'),
    btnCam: document.getElementById('btn-cam'),
    btnScreen: document.getElementById('btn-screen'),
    btnLeave: document.getElementById('btn-leave'),
    btnChat: document.getElementById('btn-chat'),
    btnParticipants: document.getElementById('btn-participants'),
    btnClosePanel: document.getElementById('close-panel'),

    // Preflight
    preflightVideo: document.getElementById('preflight-video'),
    preflightPlaceholder: document.getElementById('preflight-placeholder'),
    micSelect: document.getElementById('microphone-select'),
    camSelect: document.getElementById('camera-select'),
    joinBtn: document.getElementById('preflight-join')
};

// Logger (Simplified)
const Logger = {
    log: (msg, data) => console.log(`[DefAI] ${msg}`, data || ''),
    error: (msg, err) => console.error(`[DefAI Error] ${msg}`, err || '')
};

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', init);

async function init() {
    Logger.log('Initializing Videoconference...');

    setupEventListeners();
    await initDeviceSelection();
    startPreflightLoop();

    // Handle initial tooltips
    setupTooltips();
}

function setupEventListeners() {
    // Media Controls
    DOM.btnMic.addEventListener('click', toggleAudio);
    DOM.btnCam.addEventListener('click', toggleVideo);
    DOM.btnScreen.addEventListener('click', toggleScreenShare);
    DOM.btnLeave.addEventListener('click', () => window.location.href = '/');

    // Sidebar Controls
    DOM.btnChat.addEventListener('click', () => toggleSidebar('chat'));
    DOM.btnParticipants.addEventListener('click', () => toggleSidebar('participants'));
    DOM.btnClosePanel.addEventListener('click', () => toggleSidebar(null)); // Close

    // Preflight
    DOM.joinBtn.addEventListener('click', joinRoom);
    document.getElementById('preflight-cancel').addEventListener('click', () => window.location.href = '/');

    // Chat
    document.getElementById('chat-form').addEventListener('submit', sendChatMessage);

    // Socket Events
    socket.on('connect', () => Logger.log('Socket Connected', socket.id));
    socket.on('room_info', handleRoomInfo);
    socket.on('user_joined', handleUserJoined);
    socket.on('user_left', handleUserLeft);
    socket.on('offer', handleOffer);
    socket.on('answer', handleAnswer);
    socket.on('ice_candidate', handleIceCandidate);
    socket.on('user_audio_changed', handleRemoteAudioChange);
    socket.on('user_video_changed', handleRemoteVideoChange);
    socket.on('screen_share_started', handleRemoteScreenShareStart);
    socket.on('screen_share_stopped', handleRemoteScreenShareStop);
    socket.on('new_chat_message', handleNewChatMessage);
}

// ==========================================
// PREFLIGHT & DEVICES
// ==========================================
async function initDeviceSelection() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();

        DOM.micSelect.innerHTML = '';
        DOM.camSelect.innerHTML = '';

        devices.forEach(device => {
            const opt = document.createElement('option');
            opt.value = device.deviceId;
            opt.text = device.label || `${device.kind} ${DOM.micSelect.length + 1}`;

            if (device.kind === 'audioinput') DOM.micSelect.appendChild(opt);
            if (device.kind === 'videoinput') DOM.camSelect.appendChild(opt);
        });

        // Listen for changes
        DOM.micSelect.addEventListener('change', () => startPreflightLoop());
        DOM.camSelect.addEventListener('change', () => startPreflightLoop());

    } catch (e) {
        Logger.error('Device enumeration failed', e);
        showToast('Impossible de lister les périphériques', 'error');
    }
}

async function startPreflightLoop() {
    if (State.localStream) {
        State.localStream.getTracks().forEach(t => t.stop());
    }

    const audioId = DOM.micSelect.value;
    const videoId = DOM.camSelect.value;

    const constraints = {
        audio: audioId ? { deviceId: { exact: audioId } } : true,
        video: videoId ? { deviceId: { exact: videoId }, width: { ideal: 1280 }, height: { ideal: 720 } } : true
    };

    try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        State.localStream = stream;
        DOM.preflightVideo.srcObject = stream;
        DOM.preflightPlaceholder.style.display = 'none';

        // Connect Audio Visualizer for Preflight
        setupAudioVisualizer(stream, 'preflight-audio-bar');

        State.videoDevice = videoId;
        State.audioDevice = audioId;
        State.videoEnabled = true;
        State.audioEnabled = true;

    } catch (e) {
        Logger.error('Preflight media failed', e);
        DOM.preflightVideo.srcObject = null;
        DOM.preflightPlaceholder.style.display = 'flex';
    }
}

// ==========================================
// JOINING ROOM
// ==========================================
async function joinRoom() {
    DOM.preflightModal.classList.add('hidden'); // Hide modal based on new class handling or direct style
    DOM.preflightModal.style.display = 'none';

    // Add local user to UI
    addParticipantToUI(window.USER_ID, window.USER_NAME, true, State.localStream);

    // Join Socket Room
    socket.emit('join_room', {
        room_token: window.ROOM_ID,
        user_id: window.USER_ID,
        username: window.USER_NAME
    });

    // Start audio monitoring for local user
    setupAudioVisualizer(State.localStream, null, window.USER_ID);
}

// ==========================================
// WEBRTC LOGIC (SimplePeer)
// ==========================================
function createPeer(targetId, initiator) {
    const peer = new SimplePeer({
        initiator: initiator,
        trickle: true,
        stream: State.isSharingScreen ? State.screenStream : State.localStream
        // ICE servers usually configured here or default
    });

    peer.on('signal', data => {
        const type = data.type || (data.candidate ? 'ice_candidate' : 'offer'); // Normalize
        if (data.type === 'offer') socket.emit('offer', { to: targetId, from: window.USER_ID, offer: data });
        if (data.type === 'answer') socket.emit('answer', { to: targetId, from: window.USER_ID, answer: data });
        if (data.candidate) socket.emit('ice_candidate', { to: targetId, from: window.USER_ID, candidate: data });
    });

    peer.on('stream', stream => {
        handleRemoteStream(targetId, stream);
    });

    peer.on('close', () => removeParticipant(targetId));
    peer.on('error', err => Logger.error('Peer error', err));

    State.peers[targetId] = peer;
    return peer;
}

function handleRoomInfo(data) {
    const participants = data.participants;
    participants.forEach(p => {
        if (p.id == window.USER_ID) return; // Skip self

        // Determine initiator (lower ID calls higher ID)
        // Using string comparison is fine for UUIDs/ActiveRecord IDs
        const isInitiator = window.USER_ID < p.id;

        // Wait for specific signaling if not initiator
        if (isInitiator) createPeer(p.id, true);

        // Add placeholder UI until stream arrives or just add to map
        State.participants.set(p.id, { name: p.username });
        updateParticipantListUI();
    });
}

function handleUserJoined(data) {
    if (data.user_id == window.USER_ID) return;
    showToast(`${data.username} a rejoint la réunion.`);

    const isInitiator = window.USER_ID < data.user_id; // Logic consistency
    if (isInitiator) createPeer(data.user_id, true);

    State.participants.set(data.user_id, { name: data.username });
    updateParticipantListUI();
}

function handleUserLeft(data) {
    removeParticipant(data.user_id);
    showToast(`Un participant a quitté la réunion.`);
}

function removeParticipant(userId) {
    if (State.peers[userId]) {
        State.peers[userId].destroy();
        delete State.peers[userId];
    }

    // Remove UI
    const card = document.getElementById(`video-card-${userId}`);
    if (card) card.remove();

    State.participants.delete(userId);

    // If pinned user left, unpin
    if (State.spotlightId === userId) {
        setSpotlight(null);
    } else {
        updateLayout();
    }
    updateParticipantListUI();
}

// Signaling Handlers
function handleOffer(data) {
    if (!State.peers[data.from]) createPeer(data.from, false);
    State.peers[data.from].signal(data.offer);
}
function handleAnswer(data) {
    if (State.peers[data.from]) State.peers[data.from].signal(data.answer);
}
function handleIceCandidate(data) {
    if (State.peers[data.from]) State.peers[data.from].signal(data.candidate);
}

// ==========================================
// UI HANDLING & LAYOUT ENGINE
// ==========================================
function addParticipantToUI(userId, name, isLocal, stream) {
    // Create Video Card
    const card = document.createElement('div');
    card.className = 'video-card group';
    card.id = `video-card-${userId}`;
    card.onclick = () => setSpotlight(userId); // Click to pin

    // Video Element
    const video = document.createElement('video');
    video.autoplay = true;
    video.muted = isLocal; // Mute self
    video.playsInline = true;
    if (stream) video.srcObject = stream;
    if (isLocal) video.style.transform = 'scaleX(-1)'; // Mirror local

    // Avatar Placeholder (hidden by default if stream active)
    const avatar = document.createElement('div');
    avatar.className = 'avatar-placeholder ' + (stream && stream.getVideoTracks()[0]?.enabled ? 'hidden' : '');
    avatar.innerHTML = `<div class="w-20 h-20 rounded-full bg-blue-600 flex items-center justify-center text-2xl font-bold text-white">${getInitials(name)}</div>`;

    // Label
    const label = document.createElement('div');
    label.className = 'participant-label';
    label.innerHTML = `
        <span class="truncate max-w-[120px]">${name} ${isLocal ? '(Vous)' : ''}</span>
        <i class="fas fa-microphone-slash text-red-500 text-xs hidden" id="mute-icon-${userId}"></i>
    `;

    // Active Speaker Ring
    const ring = document.createElement('div');
    ring.className = 'active-speaker-ring';

    // Pin Overlay
    const pinOverlay = document.createElement('div');
    pinOverlay.className = 'pin-overlay';
    pinOverlay.innerHTML = '<i class="fas fa-thumbtack text-white text-3xl drop-shadow-lg"></i>';

    // Assemble
    card.appendChild(video);
    card.appendChild(avatar);
    card.appendChild(label);
    card.appendChild(ring);
    card.appendChild(pinOverlay);

    DOM.layoutContainer.appendChild(card);

    // Initial Layout update
    updateLayout();
    updateParticipantListUI();
}

function handleRemoteStream(userId, stream) {
    let card = document.getElementById(`video-card-${userId}`);
    if (!card) {
        const p = State.participants.get(userId);
        addParticipantToUI(userId, p ? p.name : 'Utilisateur', false, stream);
    } else {
        const video = card.querySelector('video');
        video.srcObject = stream;
    }

    setupAudioVisualizer(stream, null, userId);
}

// Core Layout Function
function updateLayout() {
    const cards = Array.from(DOM.layoutContainer.children);
    const count = cards.length;

    if (State.spotlightId && document.getElementById(`video-card-${State.spotlightId}`)) {
        // SPOTLIGHT MODE
        DOM.layoutContainer.className = 'layout-spotlight p-4';

        let existingStage = DOM.layoutContainer.querySelector('.stage-area');
        if (!existingStage) {
            existingStage = document.createElement('div');
            existingStage.className = 'stage-area';
            DOM.layoutContainer.prepend(existingStage);
        }

        let existingFilmstrip = DOM.layoutContainer.querySelector('.filmstrip-area');
        if (!existingFilmstrip) {
            existingFilmstrip = document.createElement('div');
            existingFilmstrip.className = 'filmstrip-area';
            DOM.layoutContainer.appendChild(existingFilmstrip);
        }

        cards.forEach(card => {
            if (card.classList.contains('stage-area') || card.classList.contains('filmstrip-area')) return;

            // Check if this card is the spotlight
            const isSpotlight = card.id === `video-card-${State.spotlightId}`;
            if (isSpotlight) {
                existingStage.appendChild(card);
                card.style.height = '100%';
                card.style.width = '100%';
            } else {
                existingFilmstrip.appendChild(card);
                card.style.height = '100%';
                card.style.width = '220px';
            }
        });

    } else {
        // GRID MODE
        DOM.layoutContainer.className = 'layout-grid p-4';

        // Remove structural divs if they exist
        const stage = DOM.layoutContainer.querySelector('.stage-area');
        const filmstrip = DOM.layoutContainer.querySelector('.filmstrip-area');

        if (stage) {
            while (stage.firstChild) DOM.layoutContainer.appendChild(stage.firstChild);
            stage.remove();
        }
        if (filmstrip) {
            while (filmstrip.firstChild) DOM.layoutContainer.appendChild(filmstrip.firstChild);
            filmstrip.remove();
        }

        // Reset styles
        cards.forEach(card => {
            if (card.tagName === 'DIV') { // Safety check
                card.style.height = '';
                card.style.width = '';
            }
        });
    }
}

function setSpotlight(userId) {
    if (State.spotlightId === userId) {
        // Toggle off if clicking same
        State.spotlightId = null;
    } else {
        State.spotlightId = userId;
    }
    updateLayout();
}

// ==========================================
// MEDIA CONTROLS
// ==========================================
function toggleAudio() {
    State.audioEnabled = !State.audioEnabled;
    State.localStream.getAudioTracks().forEach(t => t.enabled = State.audioEnabled);

    updateControlState(DOM.btnMic, State.audioEnabled, 'fa-microphone', 'fa-microphone-slash');
    onLocalMediaChange('audio', State.audioEnabled);
}

function toggleVideo() {
    State.videoEnabled = !State.videoEnabled;
    State.localStream.getVideoTracks().forEach(t => t.enabled = State.videoEnabled);

    updateControlState(DOM.btnCam, State.videoEnabled, 'fa-video', 'fa-video-slash');

    // Update local placeholder
    const card = document.getElementById(`video-card-${window.USER_ID}`);
    const ph = card.querySelector('.avatar-placeholder');
    if (ph) ph.classList.toggle('hidden', State.videoEnabled);

    onLocalMediaChange('video', State.videoEnabled);
}

async function toggleScreenShare() {
    if (State.isSharingScreen) {
        // Stop sharing
        stopScreenShare();
    } else {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
            State.screenStream = stream;
            State.isSharingScreen = true;

            // Listen for system stop
            stream.getVideoTracks()[0].onended = stopScreenShare;

            // Replace tracks in all peers
            replaceTracksInPeers(State.localStream, State.screenStream);

            // Update local view
            const localVid = document.querySelector(`#video-card-${window.USER_ID} video`);
            if (localVid) {
                localVid.srcObject = stream;
                localVid.style.transform = 'none'; // No mirror for screen
            }

            DOM.btnScreen.classList.add('bg-blue-600', 'text-white');

            socket.emit('screen_share_started', { room_token: window.ROOM_ID, user_id: window.USER_ID, username: window.USER_NAME });

        } catch (e) {
            Logger.error('Screen share failed', e);
        }
    }
}

function stopScreenShare() {
    if (!State.isSharingScreen) return;

    if (State.screenStream) {
        State.screenStream.getTracks().forEach(t => t.stop());
    }

    // Restore local stream
    replaceTracksInPeers(State.screenStream, State.localStream);

    const localVid = document.querySelector(`#video-card-${window.USER_ID} video`);
    if (localVid) {
        localVid.srcObject = State.localStream;
        localVid.style.transform = 'scaleX(-1)'; // Restore mirror
    }

    State.isSharingScreen = false;
    State.screenStream = null;
    DOM.btnScreen.classList.remove('bg-blue-600', 'text-white');

    socket.emit('screen_share_stopped', { room_token: window.ROOM_ID, user_id: window.USER_ID, username: window.USER_NAME });
}

function replaceTracksInPeers(oldStream, newStream) {
    if (!newStream) return;

    const oldVideoTrack = oldStream ? oldStream.getVideoTracks()[0] : null;
    const newVideoTrack = newStream.getVideoTracks()[0];

    if (newVideoTrack) {
        Object.values(State.peers).forEach(peer => {
            if (oldVideoTrack) {
                peer.replaceTrack(oldVideoTrack, newVideoTrack, oldStream);
            } else {
                peer.addTrack(newVideoTrack, oldStream); // Fallback
            }
        });
    }
}

// ==========================================
// HELPERS
// ==========================================
function updateControlState(btn, isActive, activeIcon, inactiveIcon) {
    const icon = btn.querySelector('i');
    if (isActive) {
        btn.classList.remove('bg-red-600', 'hover:bg-red-700');
        btn.classList.add('bg-slate-700', 'hover:bg-slate-600');
        icon.className = `fas ${activeIcon}`;
    } else {
        btn.classList.remove('bg-slate-700', 'hover:bg-slate-600');
        btn.classList.add('bg-red-600', 'hover:bg-red-700');
        icon.className = `fas ${inactiveIcon}`;
    }
}

function showToast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = 'toast-animate bg-slate-800 text-white px-4 py-3 rounded-lg shadow-xl border border-slate-700 flex items-center gap-3';
    el.innerHTML = `
        <i class="fas ${type === 'error' ? 'fa-exclamation-circle text-red-500' : 'fa-info-circle text-blue-500'}"></i>
        <span class="text-sm font-medium">${msg}</span>
    `;
    DOM.toastZone.appendChild(el);
    setTimeout(() => {
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 300);
    }, 4000);
}

function getInitials(name) {
    return name ? name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : '?';
}

function handleRemoteAudioChange(data) {
    const icon = document.getElementById(`mute-icon-${data.user_id}`);
    if (icon) icon.classList.toggle('hidden', !data.is_muted);
}

function handleRemoteVideoChange(data) {
    const card = document.getElementById(`video-card-${data.user_id}`);
    if (card) {
        const ph = card.querySelector('.avatar-placeholder');
        if (ph) ph.classList.toggle('hidden', !data.is_off); // is_off=true -> hidden=false (show placeholder)
    }
}

function handleRemoteScreenShareStart(data) {
    const card = document.getElementById(`video-card-${data.user_id}`);
    if (card) {
        card.classList.add('screen-share');
        // Auto Spotlight screen share
        setSpotlight(data.user_id);
    }
}

function handleRemoteScreenShareStop(data) {
    const card = document.getElementById(`video-card-${data.user_id}`);
    if (card) card.classList.remove('screen-share');
    if (State.spotlightId == data.user_id) setSpotlight(null);
}

function onLocalMediaChange(type, isEnabled) {
    socket.emit(`toggle_${type}`, {
        room_token: window.ROOM_ID,
        user_id: window.USER_ID,
        [type === 'video' ? 'is_off' : 'is_muted']: !isEnabled
    });
}

function setupAudioVisualizer(stream, barId, userId) {
    if (!stream || !stream.getAudioTracks().length) return;

    // Simplistic visualizer for preflight or active speaker
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx();
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);

    const data = new Uint8Array(analyser.frequencyBinCount);

    const loop = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((a, b) => a + b) / data.length;

        // Update bar (Preflight)
        if (barId) {
            const el = document.getElementById(barId);
            if (el) el.style.width = `${Math.min(100, avg * 2)}%`;
        }

        // Active Speaker (Room)
        if (userId) {
            const card = document.getElementById(`video-card-${userId}`);
            if (card) {
                card.classList.toggle('is-speaking', avg > 20); // Threshold
            }
        }

        requestAnimationFrame(loop);
    };
    loop();
}

// Side Panel
function toggleSidebar(view) {
    if (view === State.activeSidebarTab && State.isSidebarOpen) {
        // Close if click same
        DOM.sidePanel.classList.add('translate-x-full');
        State.isSidebarOpen = false;
    } else if (view) {
        // Open
        DOM.sidePanel.classList.remove('translate-x-full');
        State.isSidebarOpen = true;
        State.activeSidebarTab = view;

        document.getElementById('participants-view').classList.toggle('hidden', view !== 'participants');
        document.getElementById('chat-view').classList.toggle('hidden', view !== 'chat');
        document.getElementById('panel-title').innerText = view === 'participants' ? 'Participants' : 'Chat';
    } else {
        // Force Close
        DOM.sidePanel.classList.add('translate-x-full');
        State.isSidebarOpen = false;
    }
}

function updateParticipantListUI() {
    const container = document.getElementById('participants-view');
    container.innerHTML = '';

    // Add local
    addListEntry(window.USER_ID, window.USER_NAME + ' (Vous)', true);

    State.participants.forEach((p, id) => {
        addListEntry(id, p.name, false);
    });

    // Update badge
    document.getElementById('badge-count').innerText = State.participants.size + 1;
    document.getElementById('badge-count').classList.remove('hidden');
}

function addListEntry(id, name, isLocal) {
    const div = document.createElement('div');
    div.className = 'flex items-center justify-between p-2 rounded hover:bg-white/5';
    div.innerHTML = `
        <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold">${getInitials(name)}</div>
            <span class="text-sm truncate max-w-[150px]">${name}</span>
        </div>
        ${!isLocal ? `<div class="text-xs text-slate-500"><i class="fas fa-signal"></i></div>` : ''}
    `;
    document.getElementById('participants-view').appendChild(div);
}

// Simple Chat Logic (Minimal implementation)
function sendChatMessage(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const txt = input.value.trim();
    if (!txt) return;

    socket.emit('chat_message', {
        room_token: window.ROOM_ID,
        user_id: window.USER_ID,
        message: txt
    });

    input.value = '';
    // Optimistic append? Or wait for socket back? Meet waits usually, but let's append
    // handleNewChatMessage({ user_id: window.USER_ID, message: txt, username: window.USER_NAME });
}

function handleNewChatMessage(data) {
    const box = document.getElementById('chat-messages');
    const isMe = data.user_id == window.USER_ID;

    const bubble = document.createElement('div');
    bubble.className = `flex flex-col ${isMe ? 'items-end' : 'items-start'}`;
    bubble.innerHTML = `
        <div class="text-[10px] text-slate-400 mb-1 px-1">${isMe ? 'Vous' : data.username || 'Utilisateur'}</div>
        <div class="bg-slate-700 rounded-2xl px-4 py-2 text-sm max-w-[90%] ${isMe ? 'bg-blue-600 text-white rounded-br-sm' : 'rounded-bl-sm'}">
            ${data.message}
        </div>
    `;
    box.appendChild(bubble);
    box.scrollTop = box.scrollHeight;

    if (!isMe && State.activeSidebarTab !== 'chat') {
        document.getElementById('badge-chat').classList.remove('hidden');
    }
}

function setupTooltips() {
    // Simple custom tooltip logic if needed, or browser default 'title'
    // For now, let's rely on standard browser tooltips to keep it lightweight
    document.querySelectorAll('.tooltip-trigger').forEach(el => {
        el.title = el.dataset.tooltip || '';
    });
}