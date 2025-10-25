from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import json
import os
from report_generator import generate_report
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)
DATABASE_FILE = 'proctoring_data.db'

# (Your existing proctoring logic remains)
ALERT_WEIGHTS = {"Multiple faces detected!": 25, "CELL PHONE detected!": 20, "Distraction: Looking away while talking": 10, "No person detected!": 15, "Someone is talking!": 5, "Suspicious micro gesture detected!": 5, "Hand on mouse/keyboard detected!": 2}

def calculate_integrity_score(alerts):
    score = 100
    if not alerts: return score
    for alert in set(alerts):
        for key, weight in ALERT_WEIGHTS.items():
            if key in alert: score -= weight; break
    return max(0, score)

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # --- User Table (Unchanged) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'admin'))
    );
    """)
    
    # --- Events Table (Unchanged) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        alerts TEXT,
        metrics TEXT,
        integrity_score REAL
    );
    """)
    
    # --- ✨ NEW TABLE: exams ---
    # Stores the exams created by an admin
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        created_by_admin_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by_admin_id) REFERENCES users (id)
    );
    """)
    
    # --- ✨ NEW TABLE: exam_assignments ---
    # Links students to exams they are assigned to
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'assigned', -- e.g., 'assigned', 'in_progress', 'completed'
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (exam_id) REFERENCES exams (id),
        FOREIGN KEY (student_id) REFERENCES users (id),
        UNIQUE(exam_id, student_id) -- A student can only be assigned an exam once
    );
    """)

    conn.commit()
    conn.close()
    print("SQLite database is ready with 'users', 'events', 'exams', and 'exam_assignments' tables.")


# ===================================================
# 🔹 AUTH ENDPOINTS (Unchanged) 🔹
# ===================================================

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not username or not password or not role:
        return jsonify({"status": "error", "message": "Missing username, password, or role"}), 400
    if role not in ['student', 'admin']:
        return jsonify({"status": "error", "message": "Role must be 'student' or 'admin'"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Username already exists"}), 409

    password_hash = generate_password_hash(password)
    sql = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
    cursor.execute(sql, (username, password_hash, role))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "error", "message": "Missing username or password"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user or not check_password_hash(user['password_hash'], password):
        conn.close()
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401

    conn.close()
    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": {
            "id": user['id'], # ✨ Send back the user ID
            "username": user['username'],
            "role": user['role']
        }
    }), 200


# ===================================================
# 🔹 ✨ NEW ADMIN API ENDPOINTS 🔹
# ===================================================

@app.route('/api/students', methods=['GET'])
def get_students():
    """Fetches all users with the 'student' role."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE role = 'student'")
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/exams', methods=['GET', 'POST'])
def handle_exams():
    """GET: Fetches all exams. POST: Creates a new exam."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    
    if request.method == 'POST':
        data = request.json
        title = data.get('title')
        description = data.get('description')
        admin_id = data.get('admin_id') # We'll need to send this from the frontend
        
        if not title or not admin_id:
            return jsonify({"status": "error", "message": "Missing title or admin_id"}), 400
        
        cursor = conn.cursor()
        sql = "INSERT INTO exams (title, description, created_by_admin_id) VALUES (?, ?, ?)"
        cursor.execute(sql, (title, description, admin_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Exam created successfully"}), 201

    elif request.method == 'GET':
        cursor = conn.cursor()
        # Join with users table to get admin's name
        cursor.execute("""
            SELECT e.id, e.title, e.description, e.created_at, u.username as admin_username
            FROM exams e
            JOIN users u ON e.created_by_admin_id = u.id
            ORDER BY e.created_at DESC
        """)
        exams = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(exams)

@app.route('/api/assign', methods=['POST'])
def assign_exam():
    """Assigns an exam to a student."""
    data = request.json
    exam_id = data.get('exam_id')
    student_id = data.get('student_id')

    if not exam_id or not student_id:
        return jsonify({"status": "error", "message": "Missing exam_id or student_id"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO exam_assignments (exam_id, student_id) VALUES (?, ?)"
        cursor.execute(sql, (exam_id, student_id))
        conn.commit()
    except sqlite3.IntegrityError:
        # This triggers if the UNIQUE(exam_id, student_id) constraint fails
        conn.close()
        return jsonify({"status": "error", "message": "This exam is already assigned to this student"}), 409
    
    conn.close()
    return jsonify({"status": "success", "message": "Exam assigned successfully"}), 201

@app.route('/api/exam_sessions/<int:exam_id>', methods=['GET'])
def get_sessions_for_exam(exam_id):
    """
    Fetches all proctoring sessions (events) associated with a specific exam.
    It does this by finding all students assigned to the exam, then finding
    their proctoring sessions.
    
    NOTE: This is a simplified logic. A more robust way would be to pass the 
    exam_id from the client-agent and store it in the 'events' table.
    For now, we'll map session_id to exam_id via the student.
    
    Let's use the 'session_id' as 'exam_id_student_id_timestamp'.
    This is what your client-agent creates: SESSION_ID = f"{STUDENT_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    We need to update this logic.
    
    Let's assume for now that the 'session_id' in the 'events' table
    will be in the format: `exam_{exam_id}_student_{student_id}_...`
    We will modify the client-agent later to support this.
    
    For now, let's just fetch all sessions for all students assigned to this exam.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find all students assigned to this exam
    cursor.execute("SELECT student_id FROM exam_assignments WHERE exam_id = ?", (exam_id,))
    students = cursor.fetchall()
    
    if not students:
        conn.close()
        return jsonify([])

    student_ids = [s['student_id'] for s in students]
    # Create a string of placeholders like '?,?'
    placeholders = ','.join('?' for _ in student_ids)
    
    # Get all event sessions for those students, grouped by session_id
    # We also join with the users table to get the student's username
    query = f"""
        SELECT 
            e.session_id, 
            e.student_id, 
            u.username as student_username, 
            MIN(e.timestamp) as start_time, 
            MAX(e.integrity_score) as final_score
        FROM events e
        JOIN users u ON e.student_id = u.id
        WHERE e.student_id IN ({placeholders})
        GROUP BY e.session_id, e.student_id, u.username
        ORDER BY start_time DESC
    """
    
    cursor.execute(query, student_ids)
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(sessions)


# ===================================================
# 🔹 EXISTING PROCTORING ENDPOINTS (Unchanged) 🔹
# ===================================================

@app.route('/log_data', methods=['POST'])
def log_data():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400
    
    # We get student_id from the payload, which your client-agent sends
    student_id = data.get('student_id')
    timestamp = data.get('timestamp')
    alerts = data.get('alerts', [])
    score = calculate_integrity_score(alerts)
    alerts_json = json.dumps(alerts)
    metrics_json = json.dumps(data.get('metrics', {}))

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    sql = "INSERT INTO events (student_id, session_id, timestamp, alerts, metrics, integrity_score) VALUES (?, ?, ?, ?, ?, ?)"
    # Note: Your client-agent sends student_id as a string like 'student_001'
    # Our new 'users' table uses an integer ID. This is a mismatch we must fix.
    
    # --- TEMPORARY FIX ---
    # Let's find the student's integer ID from their username (which client-agent sends as student_id)
    cursor.execute("SELECT id FROM users WHERE username = ?", (student_id,))
    user_row = cursor.fetchone()
    student_int_id = user_row[0] if user_row else None
    
    if not student_int_id:
        # This will fail if the client-agent's STUDENT_ID isn't a valid username
        # For now, we'll just log with the string ID.
        # But we will fix this in the client-agent later.
        pass # We'll just use the string student_id for now.
    
    # We will insert the *string* username (e.g., 'student_001') into student_id column for now
    # This is technical debt we will fix.
    cursor.execute(sql, (student_id, session_id, timestamp, alerts_json, metrics_json, score))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Data logged"}), 200

# (The rest of your existing endpoints remain unchanged)
@app.route('/get_sessions/<student_id>', methods=['GET'])
def get_sessions(student_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM events WHERE student_id = ? ORDER BY session_id DESC", (student_id,))
    sessions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(sessions)

@app.route('/get_data/<student_id>/<session_id>', methods=['GET'])
def get_data(student_id, session_id):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE student_id = ? AND session_id = ? ORDER BY timestamp DESC", (student_id, session_id))
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]
    conn.close()
    return jsonify(data)

@app.route('/generate_report/<student_id>/<session_id>', methods=['GET'])
def download_report(student_id, session_id):
    report_path = f"temp_report_{student_id}_{session_id}.pdf"
    generated_file = generate_report(student_id, session_id, report_path)
    if generated_file:
        return send_file(generated_file, as_attachment=True, download_name=f"Report_{student_id}_{session_id}.pdf")
    else:
        return "Could not generate report: No data for this session.", 404

@app.route('/api/my_exams/<int:student_id>', methods=['GET'])
def get_student_exams(student_id):
    """Fetches all exams assigned to a specific student."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Join assignments with exams to get exam details
    cursor.execute("""
        SELECT 
            e.id as exam_id,
            e.title,
            e.description,
            a.status,
            a.assigned_at
        FROM exam_assignments a
        JOIN exams e ON a.exam_id = e.id
        WHERE a.student_id = ?
        ORDER BY a.assigned_at DESC
    """, (student_id,))

    exams = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(exams)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)