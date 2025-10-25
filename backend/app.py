from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import sqlite3
import json
import os
from report_generator import generate_report
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
# ✨ MODIFIED: Make CORS explicit to solve any lingering issues
CORS(app, resources={r"/*": {"origins": "*"}})
DATABASE_FILE = 'proctoring_data.db'

# (Alert weights are unchanged)
ALERT_WEIGHTS = {
    "Multiple faces detected!": 25,
    "CELL PHONE detected!": 20,
    "Distraction: Looking away while talking": 10,
    "No person detected!": 15,
    "Someone is talking!": 5,
    "VOICE:": 10,
    "Suspicious micro gesture detected!": 5,
    "Hand on mouse/keyboard detected!": 2,
    "WEB: Switched tabs": 8,
    "WEB: Left focus": 5
}

# --- ✨ NEW: Server-side cache ---
# This dictionary will store the last known alerts for each active session
# We use this to avoid flooding the database
SESSION_LAST_ALERTS = {}

def calculate_integrity_score(alerts):
    score = 100
    if not alerts: return score
    for alert in set(alerts):
        for key, weight in ALERT_WEIGHTS.items():
            if key in alert: score -= weight; break
    return max(0, score)

# (init_db is unchanged)
def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'admin'))
    );
    """)
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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'assigned',
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (exam_id) REFERENCES exams (id),
        FOREIGN KEY (student_id) REFERENCES users (id),
        UNIQUE(exam_id, student_id)
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
    # ... (endpoint is unchanged) ...
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
    # ... (endpoint is unchanged) ...
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
            "id": user['id'],
            "username": user['username'],
            "role": user['role']
        }
    }), 200

# ===================================================
# 🔹 ADMIN API ENDPOINTS (Unchanged) 🔹
# ===================================================
@app.route('/api/students', methods=['GET'])
def get_students():
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE role = 'student'")
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/exams', methods=['GET', 'POST'])
def handle_exams():
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        data = request.json
        title = data.get('title')
        description = data.get('description')
        admin_id = data.get('admin_id')
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
    # ... (endpoint is unchanged) ...
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
        conn.close()
        return jsonify({"status": "error", "message": "This exam is already assigned to this student"}), 409
    conn.close()
    return jsonify({"status": "success", "message": "Exam assigned successfully"}), 201

@app.route('/api/exam_details/<int:exam_id>', methods=['GET'])
def get_exam_details(exam_id):
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM exams WHERE id = ?", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        return jsonify({"status": "error", "message": "Exam not found"}), 404
    conn.close()
    return jsonify(dict(exam))

@app.route('/api/exam_sessions/<int:exam_id>', methods=['GET'])
def get_sessions_for_exam(exam_id):
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.username 
        FROM exam_assignments a
        JOIN users u ON a.student_id = u.id
        WHERE a.exam_id = ?
    """, (exam_id,))
    students = cursor.fetchall()
    if not students:
        conn.close()
        return jsonify([])
    student_usernames = [s['username'] for s in students]
    placeholders = ','.join('?' for _ in student_usernames)
    query = f"""
        SELECT 
            e.session_id, 
            e.student_id as student_username, 
            MIN(e.timestamp) as start_time, 
            MAX(e.integrity_score) as final_score
        FROM events e
        WHERE e.student_id IN ({placeholders}) AND e.session_id LIKE ?
        GROUP BY e.session_id, e.student_id
        ORDER BY start_time DESC
    """
    params = student_usernames + [f"exam_{exam_id}_%"]
    cursor.execute(query, params)
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(sessions)

# ===================================================
# 🔹 STUDENT API ENDPOINTS (Unchanged) 🔹
# ===================================================
@app.route('/api/my_exams/<int:student_id>', methods=['GET'])
def get_student_exams(student_id):
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            e.id as exam_id, e.title, e.description, a.status, a.assigned_at
        FROM exam_assignments a
        JOIN exams e ON a.exam_id = e.id
        WHERE a.student_id = ?
        ORDER BY a.assigned_at DESC
    """, (student_id,))
    exams = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(exams)

# ===================================================
# 🔹 PROCTORING DATA ENDPOINT (✨ HEAVILY MODIFIED) 🔹
# ===================================================

@app.route('/log_data', methods=['POST'])
def log_data():
    data = request.json
    
    is_web_alert = data.get('source') == 'web'
    student_id = data.get('student_id')
    session_id = data.get('session_id')
    
    if not student_id or not session_id:
        return jsonify({"status": "error", "message": "student_id and session_id are required"}), 400

    # Get the set of alerts from the payload
    current_alerts_list = data.get('alerts', [])
    current_alerts_set = set(current_alerts_list)

    # --- ✨ NEW EFFICIENCY LOGIC ---
    # We only write to the DB if it's a web alert OR if the Python alerts have changed.
    
    # Get the last known alerts for this session from our cache
    last_alerts_set = SESSION_LAST_ALERTS.get(session_id, set())

    # Check if we should skip writing this log
    if not is_web_alert and current_alerts_set == last_alerts_set:
        # It's a Python alert, and nothing has changed.
        # We just return "success" without flooding the database.
        return jsonify({"status": "success", "message": "Data received, no change"}), 200

    # If we are here, it's either a web alert or a *new* Python alert.
    # We must write it to the database.
    
    # Update the cache with the new state
    SESSION_LAST_ALERTS[session_id] = current_alerts_set
    
    # --- End of new logic ---

    if is_web_alert:
        metrics = {"source": "web"}
        timestamp = datetime.utcnow().isoformat() + "Z"
    else:
        metrics = data.get('metrics', {})
        timestamp = data.get('timestamp')

    score = calculate_integrity_score(current_alerts_list)
    alerts_json = json.dumps(current_alerts_list)
    metrics_json = json.dumps(metrics)

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    sql = "INSERT INTO events (student_id, session_id, timestamp, alerts, metrics, integrity_score) VALUES (?, ?, ?, ?, ?, ?)"
    cursor.execute(sql, (student_id, session_id, timestamp, alerts_json, metrics_json, score))
    conn.commit()
    conn.close()
    
    # If the alerts list is now empty, it means this was an "all clear" event.
    # We can clear the session from our cache to save memory.
    if not current_alerts_list:
        SESSION_LAST_ALERTS.pop(session_id, None)
        
    return jsonify({"status": "success", "message": "Data logged"}), 200

# ===================================================
# 🔹 REPORTING ENDPOINTS (Unchanged) 🔹
# ===================================================
@app.route('/get_sessions/<student_id>', methods=['GET'])
def get_sessions(student_id):
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM events WHERE student_id = ? ORDER BY session_id DESC", (student_id,))
    sessions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(sessions)

@app.route('/get_data/<student_id>/<session_id>', methods=['GET'])
def get_data(student_id, session_id):
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE student_id = ? AND session_id = ? ORDER BY timestamp DESC", (student_id, session_id))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/generate_report/<student_id>/<session_id>', methods=['GET'])
def download_report(student_id, session_id):
    # Clean up the cache for this session, as it's now considered "over"
    SESSION_LAST_ALERTS.pop(session_id, None)

    # ✨ MODIFIED: Use a more robust temporary path
    # Create a unique filename in a 'temp' subdirectory (if it doesn't exist)
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_reports')
    os.makedirs(temp_dir, exist_ok=True)
    report_filename = f"Report_{student_id}_{session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    report_path = os.path.join(temp_dir, report_filename)

    print(f"Generating report at: {report_path}") # Debug print

    generated_file_path = generate_report(student_id, session_id, report_path)

    if generated_file_path:
        # ✨ NEW: Use after_this_request for reliable cleanup
        @after_this_request
        def remove_file(response):
            try:
                print(f"Attempting to remove temporary file: {generated_file_path}") # Debug print
                os.remove(generated_file_path)
                print(f"Successfully removed: {generated_file_path}") # Debug print
            except Exception as error:
                app.logger.error(f"Error removing or closing downloaded file handle: {error}")
            return response

        # Send the file
        return send_file(
            generated_file_path,
            as_attachment=True,
            download_name=f"Report_{student_id}_{session_id}.pdf" # Keep the user-friendly name
        )
    else:
        return "Could not generate report: No data for this session.", 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)