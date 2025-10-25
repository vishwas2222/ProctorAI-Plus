import sqlite3
import json
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

DATABASE_FILE = 'proctoring_data.db'

def generate_report(student_id, session_id, output_filename):
    """Queries the database for a specific session and generates a PDF report."""

    conn = sqlite3.connect(DATABASE_FILE)
    # Use params to prevent SQL injection
    query = f"SELECT * FROM events WHERE student_id = ? AND session_id = ? ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn, params=(student_id, session_id))
    conn.close()

    if df.empty:
        print(f"No data found for student {student_id} and session {session_id}")
        return None

    # (Process the data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Use a function to safely load JSON
    def safe_json_load(x):
        try:
            # Handle potential None values or empty strings
            if not x:
                return []
            return json.loads(x)
        except (json.JSONDecodeError, TypeError):
            return [] # Return empty list on failure
            
    df['metrics'] = df['metrics'].apply(safe_json_load)
    df['alerts'] = df['alerts'].apply(safe_json_load)

    # We need to find the total *unique* alert events, not every frame.
    # We will calculate this in the loop below.
        
    final_score = df['integrity_score'].mean().round(2)
    start_time = df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M:%S')
    end_time = df['timestamp'].iloc[-1].strftime('%H:%M:%S')

    # (Generate emotion summary)
    def get_emotion(x):
        if isinstance(x, dict):
            return x.get('emotion', 'N/A')
        return 'N/A'
        
    df['emotion'] = df['metrics'].apply(get_emotion)
    emotion_summary = df['emotion'].value_counts(normalize=True).mul(100).round(1).to_dict()

    # --- PDF Generation ---
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Add custom styles for the alert text
    styles.add(ParagraphStyle(name='AlertText', parent=styles['BodyText'], fontSize=9))
    styles.add(ParagraphStyle(name='AllClearText', parent=styles['BodyText'], fontSize=9, textColor=colors.green))
    
    story = []

    story.append(Paragraph("Proctoring Session Integrity Report", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    # --- ✨ NEW LOGIC: Calculate Total Alert Events Here ---
    # This logic now finds only *changes* in alert state.
    
    log_data_list = [] # We'll build the log data here
    previous_alerts_set = set() # Start with an empty set
    total_unique_events = 0

    # Iterate over the *full* dataframe to find changes, including "all clear"
    for _, row in df.iterrows():
        current_alerts_list = row['alerts']
        if not isinstance(current_alerts_list, list):
            current_alerts_list = []
            
        current_alerts_set = set(current_alerts_list)
        
        # This is the magic: only log if the set of alerts has changed
        if current_alerts_set == previous_alerts_set:
            continue
            
        # If we are here, the state has changed.
        
        if len(current_alerts_set) > 0:
            # This is a new alert event
            total_unique_events += 1
            alert_text = "<br/>".join(sorted(list(current_alerts_set)))
            log_data_list.append([
                row['timestamp'].strftime('%H:%M:%S'),
                Paragraph(alert_text, styles['AlertText']), # Red alert text
                str(row['integrity_score'])
            ])
        else:
            # This is an "All Clear" event
            log_data_list.append([
                row['timestamp'].strftime('%H:%M:%S'),
                Paragraph("--- All Clear ---", styles['AllClearText']), # Green clear text
                str(row['integrity_score'])
            ])

        # Update the state for the next iteration
        previous_alerts_set = current_alerts_set
    # --- End of New Logic ---


    # (Summary Table - Now uses the correct count)
    summary_data = [
        ['Student ID:', student_id],
        ['Session ID:', session_id],
        ['Exam Start Time:', start_time],
        ['Exam End Time:', end_time],
        ['Final Integrity Score:', f"{final_score} / 100"],
        ['Total Alert Events:', str(total_unique_events)], # ✨ Now shows the correct number
    ]
    summary_table = Table(summary_data, hAlign='LEFT', colWidths=[1.5 * inch, 4 * inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # (Emotion Summary)
    story.append(Paragraph("Emotion Distribution", styles['h2']))
    emotion_str = ", ".join([f"{k}: {v}%" for k, v in emotion_summary.items()])
    story.append(Paragraph(emotion_str, styles['BodyText']))
    story.append(Spacer(1, 0.3 * inch))

    # (Alert Timeline - Now uses the clean list)
    story.append(Paragraph("Critical Alert Timeline", styles['h2']))
    
    if total_unique_events > 0:
        # Add the header row
        log_data_table = [['Time', 'Alerts Triggered', 'Score']] + log_data_list
            
        log_table = Table(log_data_table, colWidths=[1 * inch, 4.5 * inch, 0.5 * inch])
        log_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(log_table)
    else:
        story.append(Paragraph("No alert events recorded.", styles['BodyText']))

    try:
        doc.build(story)
        return output_filename
    except Exception as e:
        print(f"Error building PDF: {e}")
        return None