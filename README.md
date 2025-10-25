# ProctorAI+

**ProctorAI+** is a next-generation, AI-powered exam proctoring system designed with a privacy-first philosophy.  
It goes beyond simple gaze tracking by creating a holistic, multi-modal understanding of a student's test-taking environment and behavior.

The system analyzes video and audio feeds in real-time on the student's local machine (at the edge) to detect potential academic dishonesty.  
All sensitive video/audio data remains on the user's device, ensuring privacy. Only anonymized, encrypted alerts are sent to the administrator's dashboard.

This repository contains the full-stack web application for managing, taking, and reviewing proctored exams.

---

## ✨ Core Features

### 🤖 AI Proctoring Agent (Python Client)
- **Dual Attention Model:** Correlates head pose (MediaPipe) with voice activity (VAD) to reduce false positives from innocent glances.  
- **Ambient Environment Detection:** Uses YOLOv8 to detect unauthorized objects like mobile phones, open books, or additional people in the room.  
- **Micro Gesture Analysis:** Employs MediaPipe Holistic to track hand-to-face gestures or movements suggesting the use of a hidden earpiece or device.  
- **Cognitive Load Meter:** Estimates student stress and confusion by analyzing biometric proxies like blink rate (EAR) and facial expressions.  
- **Adaptive Fairness Mode:** Calibrates AI sensitivity at startup based on ambient lighting and webcam quality to ensure fairness.

### 💻 Web Portal (React Frontend)
- **Dual Authentication:** Secure login and registration for two distinct user types: *Admin* (Exam Creator) and *Student* (Exam Taker).  
- **Admin Dashboard:** Admins can create new exams, view all exams, and assign specific exams to registered students.  
- **Student Dashboard:** Students see a clean list of only the exams they have been assigned.  
- **Web-Based Proctoring:** Automatically detects tab-switching and loss of browser focus, logging these events to the backend.

### 🚀 Backend & Reporting (Flask API)
- **Secure REST API:** Endpoints for user auth, exam creation/assignment, and data logging.  
- **Consolidated Event Logging:** A single API endpoint (`/log_data`) receives alerts from both the AI Agent and frontend.  
- **Admin Session Review:** Admins can view all completed proctoring sessions for any given exam.  
- **PDF Report Generation:** Download tamper-proof PDF reports detailing all flagged events and the final integrity score.

---

## 🛠️ Tech Stack

| Component | Technology |
|------------|-------------|
| **Frontend** | React (Vite), Tailwind CSS, react-router-dom, axios |
| **Backend** | Flask, Python, SQLite |
| **AI Agent** | Python, OpenCV, MediaPipe, Ultralytics (YOLOv8), SpeechRecognition |
| **Deployment** | Vercel (Frontend), PyInstaller (Client Agent) |

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Node.js (v18+)
- Python (v3.9+)
- pip virtual environment (Recommended)

### 1️⃣ Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python api/app.py
```
Backend runs at: **http://127.0.0.1:5000**

### 2️⃣ Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: **http://localhost:5173**  
Ensure API URLs in your `.jsx` files point to `http://127.0.0.1:5000`.

### 3️⃣ Client-Agent Setup
```bash
cd client-agent
python main.py --username student1 --exam_id 1
```

---

## 📋 How to Use (Local Test Flow)

1. **Register Accounts**
   - Admin: `admin / password`
   - Student: `student1 / password`

2. **Create & Assign Exam**
   - Log in as Admin → Create Exam → Assign to `student1`.

3. **Take Exam**
   - Log in as Student → Start Exam.
   - Launch Python agent manually:
     ```bash
     python main.py --username student1 --exam_id 1
     ```

4. **Submit & Review**
   - Admin → View Sessions → Download PDF Report.

---

© 2025 ProctorAI+. All rights reserved.
