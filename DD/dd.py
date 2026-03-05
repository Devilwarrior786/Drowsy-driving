#!/usr/bin/env python3
"""
Drowsy Driving Detection Server
NO EXTERNAL PACKAGES REQUIRED - Pure Python only
"""

import http.server
import socketserver
import json
import base64
import random
import time
import threading
from datetime import datetime

# Configuration
HOST = "0.0.0.0"
PORT = 8000

# Storage
users = {}
detection_history = []
alert_count = 0

# Simulated EAR values for demo (since no OpenCV)
def simulate_ear():
    """Generate realistic EAR values"""
    # Normal: 0.25-0.35, Drowsy: 0.10-0.20
    base = 0.28
    variation = random.uniform(-0.08, 0.08)
    return round(max(0.10, min(0.40, base + variation)), 2)

# HTML Frontend - Complete single page
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drowsy Driving Detection System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        header { 
            display: flex; justify-content: space-between; align-items: center; 
            margin-bottom: 30px; padding: 20px;
            background: rgba(30, 41, 59, 0.8); border-radius: 16px;
            border: 1px solid #334155;
        }
        .logo { font-size: 28px; font-weight: 700; color: #06b6d4; }
        .status { 
            display: flex; align-items: center; gap: 8px;
            padding: 8px 16px; background: #0f172a;
            border-radius: 20px; font-size: 14px;
        }
        .status-dot { 
            width: 10px; height: 10px; border-radius: 50%; 
            background: #ef4444; transition: all 0.3s;
        }
        .status-dot.connected { background: #22c55e; box-shadow: 0 0 10px #22c55e; }
        
        .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
        
        .video-box {
            position: relative; background: #000;
            border-radius: 16px; overflow: hidden;
            border: 2px solid #334155; aspect-ratio: 16/9;
        }
        #webcam { 
            width: 100%; height: 100%; object-fit: cover;
            transform: scaleX(-1);
        }
        .alert-box {
            position: absolute; inset: 0;
            display: none; flex-direction: column;
            align-items: center; justify-content: center;
            background: rgba(220, 38, 38, 0.95);
            z-index: 10;
        }
        .alert-box.active { display: flex; animation: pulse 0.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 0.9; } 50% { opacity: 1; } }
        .alert-title { font-size: 60px; font-weight: 900; text-transform: uppercase; }
        .alert-sub { font-size: 20px; margin-top: 10px; }
        
        .controls {
            position: absolute; bottom: 20px; left: 20px; right: 20px;
            display: flex; justify-content: space-between; z-index: 5;
        }
        button {
            padding: 12px 24px; border: none; border-radius: 8px;
            font-size: 14px; font-weight: 600; cursor: pointer;
            transition: all 0.3s;
        }
        .btn-start { background: #06b6d4; color: white; }
        .btn-start:hover { background: #0891b2; }
        .btn-stop { background: #ef4444; color: white; }
        .btn-test { background: #f59e0b; color: white; }
        
        .stats-bar {
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 15px; margin-top: 20px;
        }
        .stat-card {
            background: rgba(30, 41, 59, 0.6);
            padding: 20px; border-radius: 12px;
            text-align: center; border: 1px solid #334155;
        }
        .stat-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; }
        .stat-value { font-size: 28px; font-weight: 700; color: #06b6d4; }
        
        .sidebar { display: flex; flex-direction: column; gap: 20px; }
        .card {
            background: rgba(30, 41, 59, 0.6);
            padding: 20px; border-radius: 16px;
            border: 1px solid #334155;
        }
        .card h3 { color: #06b6d4; margin-bottom: 15px; font-size: 14px; text-transform: uppercase; }
        
        .gauge-wrap { text-align: center; margin: 20px 0; }
        .gauge {
            width: 150px; height: 150px; margin: 0 auto;
            position: relative; display: inline-block;
        }
        .gauge-bg {
            fill: none; stroke: #334155; stroke-width: 10;
        }
        .gauge-fill {
            fill: none; stroke: #22c55e; stroke-width: 10;
            stroke-linecap: round;
            transform: rotate(-90deg);
            transform-origin: 50% 50%;
            transition: all 0.3s;
        }
        .gauge-text {
            position: absolute; inset: 0;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
        }
        .gauge-val { font-size: 36px; font-weight: 800; }
        .gauge-lbl { font-size: 12px; color: #64748b; }
        
        .info-row {
            display: flex; justify-content: space-between;
            padding: 10px 0; border-bottom: 1px solid #334155;
        }
        .info-row:last-child { border-bottom: none; }
        .badge {
            padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
            background: rgba(34, 197, 94, 0.1); color: #22c55e;
        }
        .badge.alert { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
        
        input[type="range"] {
            width: 100%; margin: 10px 0;
            -webkit-appearance: none; height: 6px;
            background: #334155; border-radius: 3px; outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none; width: 18px; height: 18px;
            background: #06b6d4; border-radius: 50%; cursor: pointer;
        }
        
        .event-log {
            max-height: 200px; overflow-y: auto;
            font-size: 12px;
        }
        .event-item {
            padding: 8px; margin-bottom: 5px;
            background: #0f172a; border-radius: 6px;
            border-left: 3px solid #22c55e;
        }
        .event-item.alert { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
        
        .modal {
            position: fixed; inset: 0;
            background: rgba(15, 23, 42, 0.98);
            display: flex; align-items: center; justify-content: center;
            z-index: 1000;
        }
        .modal.hidden { display: none; }
        .modal-box {
            background: #1e293b; padding: 40px;
            border-radius: 20px; width: 90%; max-width: 400px;
            border: 1px solid #334155;
        }
        .modal-box h2 { color: #06b6d4; margin-bottom: 20px; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; margin-bottom: 5px; color: #94a3b8; font-size: 14px; }
        .input-group input {
            width: 100%; padding: 12px; border: 1px solid #334155;
            background: #0f172a; color: white; border-radius: 8px;
        }
        .btn-block { width: 100%; margin-top: 10px; }
        .text-center { text-align: center; margin-top: 15px; color: #64748b; font-size: 14px; }
        .text-center a { color: #06b6d4; text-decoration: none; }
        .hidden { display: none !important; }
        
        .error-toast {
            position: fixed; top: 20px; right: 20px;
            background: #ef4444; color: white;
            padding: 15px 20px; border-radius: 8px;
            display: none; z-index: 1001;
        }
        .error-toast.show { display: block; }
    </style>
</head>
<body>
    <div id="errorToast" class="error-toast"></div>
    
    <div id="authModal" class="modal">
        <div class="modal-box">
            <h2 id="authTitle">Welcome Back</h2>
            <div id="loginForm">
                <div class="input-group">
                    <label>Username</label>
                    <input type="text" id="loginUser" placeholder="Enter username">
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input type="password" id="loginPass" placeholder="Enter password">
                </div>
                <button class="btn-start btn-block" onclick="login()">Sign In</button>
                <div class="text-center">New user? <a href="#" onclick="showRegister()">Create account</a></div>
            </div>
            <div id="registerForm" class="hidden">
                <div class="input-group">
                    <label>Username</label>
                    <input type="text" id="regUser" placeholder="Choose username">
                </div>
                <div class="input-group">
                    <label>Email</label>
                    <input type="email" id="regEmail" placeholder="Enter email">
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input type="password" id="regPass" placeholder="Create password">
                </div>
                <button class="btn-start btn-block" onclick="register()">Create Account</button>
                <div class="text-center">Have account? <a href="#" onclick="showLogin()">Sign in</a></div>
            </div>
        </div>
    </div>

    <div class="container">
        <header>
            <div class="logo">🚗 SafeDrive AI</div>
            <div class="status">
                <div id="connDot" class="status-dot"></div>
                <span id="connText">Connecting...</span>
            </div>
        </header>

        <div class="grid">
            <div>
                <div class="video-box">
                    <video id="webcam" autoplay playsinline></video>
                    <div id="alertBox" class="alert-box">
                        <div class="alert-title">WAKE UP!</div>
                        <div class="alert-sub">Drowsiness Detected - Pull Over Safely</div>
                    </div>
                    <div class="controls">
                        <button id="toggleBtn" class="btn-start" onclick="toggleDetection()">▶ Start Detection</button>
                        <button class="btn-test" onclick="testAlert()">⚠ Test Alert</button>
                    </div>
                </div>
                
                <div class="stats-bar">
                    <div class="stat-card">
                        <div class="stat-label">Session Time</div>
                        <div id="sessionTime" class="stat-value">00:00</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Frames</div>
                        <div id="frameCount" class="stat-value">0</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Alerts</div>
                        <div id="alertCount" class="stat-value" style="color: #ef4444;">0</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Mode</div>
                        <div class="stat-value" style="font-size: 14px; margin-top: 8px;">SIMULATION</div>
                    </div>
                </div>
            </div>

            <div class="sidebar">
                <div class="card">
                    <h3>👁 Eye Aspect Ratio</h3>
                    <div class="gauge-wrap">
                        <div class="gauge">
                            <svg width="150" height="150" viewBox="0 0 100 100">
                                <circle class="gauge-bg" cx="50" cy="50" r="40"/>
                                <circle id="gaugeFill" class="gauge-fill" cx="50" cy="50" r="40" 
                                    stroke-dasharray="251.2" stroke-dashoffset="62.8"/>
                            </svg>
                            <div class="gauge-text">
                                <div id="earValue" class="gauge-val">0.30</div>
                                <div class="gauge-lbl">EAR</div>
                            </div>
                        </div>
                    </div>
                    <div class="info-row">
                        <span>Eye Status</span>
                        <span id="eyeStatus" class="badge">OPEN</span>
                    </div>
                </div>

                <div class="card">
                    <h3>⚙️ Settings</h3>
                    <label style="font-size: 13px; color: #94a3b8;">Drowsiness Threshold</label>
                    <input type="range" id="threshold" min="0.10" max="0.30" step="0.01" value="0.20" 
                        oninput="updateThreshold(this.value)">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-top: 5px;">
                        <span>Strict (0.10)</span>
                        <span id="threshDisplay">0.20</span>
                        <span>Lenient (0.30)</span>
                    </div>
                </div>

                <div class="card">
                    <h3>📋 Event Log</h3>
                    <div id="eventLog" class="event-log">
                        <div class="event-item">System initialized</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Auto-detect server URL
        const API_URL = window.location.origin;
        
        // State
        let isRunning = false;
        let stream = null;
        let frameCount = 0;
        let alertCount = 0;
        let sessionStart = null;
        let earThreshold = 0.20;
        let timerInterval = null;
        let frameInterval = null;
        let clientId = null;
        
        const video = document.getElementById('webcam');
        const alertBox = document.getElementById('alertBox');
        const toggleBtn = document.getElementById('toggleBtn');
        const connDot = document.getElementById('connDot');
        const connText = document.getElementById('connText');
        
        // Check server on load
        async function checkServer() {
            try {
                const res = await fetch(`${API_URL}/ping`);
                if (res.ok) {
                    connDot.classList.add('connected');
                    connText.textContent = 'Connected';
                    return true;
                }
            } catch (e) {
                showError('Server not found. Make sure server is running on port 8000');
            }
            return false;
        }
        
        function showError(msg) {
            const toast = document.getElementById('errorToast');
            toast.textContent = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 4000);
        }
        
        // Auth UI
        function showRegister() {
            document.getElementById('loginForm').classList.add('hidden');
            document.getElementById('registerForm').classList.remove('hidden');
            document.getElementById('authTitle').textContent = 'Create Account';
        }
        function showLogin() {
            document.getElementById('registerForm').classList.add('hidden');
            document.getElementById('loginForm').classList.remove('hidden');
            document.getElementById('authTitle').textContent = 'Welcome Back';
        }
        
        // API calls
        async function postJSON(endpoint, data) {
            try {
                const res = await fetch(`${API_URL}${endpoint}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                return await res.json();
            } catch (e) {
                showError('Connection failed');
                return {error: 'Connection failed'};
            }
        }
        
        async function register() {
            const res = await postJSON('/register', {
                username: document.getElementById('regUser').value,
                email: document.getElementById('regEmail').value,
                password: document.getElementById('regPass').value
            });
            if (res.error) showError(res.error);
            else {
                alert('Account created! Please login.');
                showLogin();
            }
        }
        
        async function login() {
            const res = await postJSON('/login', {
                username: document.getElementById('loginUser').value,
                password: document.getElementById('loginPass').value
            });
            if (res.error) showError(res.error);
            else {
                clientId = res.client_id;
                document.getElementById('authModal').classList.add('hidden');
                startCamera();
            }
        }
        
        async function startCamera() {
            if (!(await checkServer())) return;
            
            try {
                stream = await navigator.mediaDevices.getUserMedia({video: true});
                video.srcObject = stream;
                addEvent('Camera started - ready for detection');
            } catch (e) {
                showError('Camera access denied');
            }
        }
        
        // Detection control
        async function toggleDetection() {
            if (isRunning) {
                stopDetection();
            } else {
                startDetection();
            }
        }
        
        function startDetection() {
            if (!stream) {
                showError('Start camera first');
                return;
            }
            
            isRunning = true;
            toggleBtn.textContent = '⏸ Stop Detection';
            toggleBtn.className = 'btn-stop';
            
            sessionStart = Date.now();
            updateTimer();
            timerInterval = setInterval(updateTimer, 1000);
            
            // Start sending frames (5 FPS to avoid overload)
            processFrame();
            frameInterval = setInterval(processFrame, 200);
            
            addEvent('Detection started');
        }
        
        function stopDetection() {
            isRunning = false;
            toggleBtn.textContent = '▶ Start Detection';
            toggleBtn.className = 'btn-start';
            
            clearInterval(timerInterval);
            clearInterval(frameInterval);
            alertBox.classList.remove('active');
            
            addEvent('Detection stopped');
        }
        
        async function processFrame() {
            if (!isRunning) return;
            
            // Capture frame
            const canvas = document.createElement('canvas');
            canvas.width = 320;
            canvas.height = 240;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, 320, 240);
            
            const imageData = canvas.toDataURL('image/jpeg', 0.7);
            
            // Send to server
            const result = await postJSON('/detect', {
                client_id: clientId,
                image: imageData,
                threshold: earThreshold
            });
            
            if (!result.error) {
                updateDisplay(result.ear, result.is_drowsy);
                frameCount++;
                document.getElementById('frameCount').textContent = frameCount;
                
                if (result.is_drowsy) {
                    triggerAlert();
                }
            }
        }
        
        function updateDisplay(ear, isDrowsy) {
            document.getElementById('earValue').textContent = ear.toFixed(2);
            
            const fill = document.getElementById('gaugeFill');
            const offset = 251.2 - ((ear - 0.1) / 0.3 * 251.2);
            fill.style.strokeDashoffset = Math.max(0, offset);
            
            const status = document.getElementById('eyeStatus');
            
            if (isDrowsy || ear < earThreshold) {
                fill.style.stroke = '#ef4444';
                status.textContent = 'CLOSED';
                status.className = 'badge alert';
            } else {
                fill.style.stroke = '#22c55e';
                status.textContent = 'OPEN';
                status.className = 'badge';
                alertBox.classList.remove('active');
            }
        }
        
        function triggerAlert() {
            if (alertBox.classList.contains('active')) return;
            
            alertBox.classList.add('active');
            alertCount++;
            document.getElementById('alertCount').textContent = alertCount;
            addEvent('⚠️ DROWSINESS DETECTED!', true);
            
            // Play alert sound
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                
                oscillator.frequency.value = 800;
                oscillator.type = 'square';
                gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
                
                oscillator.start();
                oscillator.stop(audioCtx.currentTime + 0.5);
            } catch(e) {}
            
            // Auto dismiss
            setTimeout(() => {
                alertBox.classList.remove('active');
            }, 3000);
        }
        
        function testAlert() {
            triggerAlert();
            addEvent('Test alert triggered');
        }
        
        function updateThreshold(val) {
            earThreshold = parseFloat(val);
            document.getElementById('threshDisplay').textContent = earThreshold.toFixed(2);
        }
        
        function updateTimer() {
            if (!sessionStart) return;
            const elapsed = Math.floor((Date.now() - sessionStart) / 1000);
            const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const secs = (elapsed % 60).toString().padStart(2, '0');
            document.getElementById('sessionTime').textContent = `${mins}:${secs}`;
        }
        
        function addEvent(msg, isAlert = false) {
            const div = document.createElement('div');
            div.className = 'event-item' + (isAlert ? ' alert' : '');
            div.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong> ${msg}`;
            const log = document.getElementById('eventLog');
            log.insertBefore(div, log.firstChild);
            if (log.children.length > 20) log.lastChild.remove();
        }
        
        // Init
        checkServer();
    </script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logs
    
    def do_GET(self):
        if self.path in ['/', '/index.html']:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif self.path == '/ping':
            self.send_json({"status": "ok"})
        else:
            self.send_error(404)
    
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            data = json.loads(body) if body else {}
            
            if self.path == '/register':
                self.handle_register(data)
            elif self.path == '/login':
                self.handle_login(data)
            elif self.path == '/detect':
                self.handle_detect(data)
            else:
                self.send_error(404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_register(self, data):
        user = data.get('username')
        if not user:
            self.send_json({"error": "Username required"}, 400)
            return
        if user in users:
            self.send_json({"error": "User exists"}, 400)
            return
        
        users[user] = {
            'email': data.get('email'),
            'password': data.get('password')
        }
        self.send_json({"success": True, "client_id": user + "_" + str(int(time.time()))})
    
    def handle_login(self, data):
        user = data.get('username')
        pwd = data.get('password')
        if user in users and users[user]['password'] == pwd:
            self.send_json({"success": True, "client_id": user + "_" + str(int(time.time()))})
        else:
            self.send_json({"error": "Invalid login"}, 401)
    
    def handle_detect(self, data):
        global alert_count, detection_history
        
        # Simulate EAR detection (since no OpenCV)
        ear = simulate_ear()
        threshold = data.get('threshold', 0.20)
        is_drowsy = ear < threshold
        
        if is_drowsy:
            alert_count += 1
        
        detection_history.append({
            "time": datetime.now().isoformat(),
            "ear": ear,
            "is_drowsy": is_drowsy
        })
        
        self.send_json({
            "ear": ear,
            "is_drowsy": is_drowsy,
            "mode": "simulation"
        })
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True


def main():
    print("=" * 60)
    print("DROWSY DRIVING DETECTION SERVER")
    print("NO INSTALLATION REQUIRED - Pure Python")
    print("=" * 60)
    print(f"Server running at: http://localhost:{PORT}")
    print(f"Open this URL in your browser")
    print("=" * 60)
    print("Features:")
    print("- User registration/login")
    print("- Simulated eye detection (no OpenCV needed)")
    print("- Real-time drowsiness alerts")
    print("- Session statistics")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    server = ThreadedServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()