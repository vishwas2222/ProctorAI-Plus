import sqlite3
import json
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

DATABASE_FILE = 'proctoring_data.db'

# ✨ MODIFIED to accept session_id
def generate_report(student_id, session_id, output_filename):
    """Queries the database for a specific session and generates a PDF report."""
    
    conn = sqlite3.connect(DATABASE_FILE)
    # ✨ MODIFIED query to filter by session_id
    query = f"SELECT * FROM events WHERE student_id = '{student_id}' AND session_id = '{session_id}' ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return None

    # (The rest of the PDF generation logic is the same)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['metrics'] = df['metrics'].apply(json.loads)
    df['alerts'] = df['alerts'].apply(json.loads)
    
    final_score = df['integrity_score'].iloc[-1]
    start_time = df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M:%S')
    end_time = df['timestamp'].iloc[-1].strftime('%H:%M:%S')
    
    alert_events = df[df['alerts'].apply(len) > 0]
    total_alerts = len(alert_events)
    
    df['emotion'] = df['metrics'].apply(lambda x: x.get('emotion', 'N/A'))
    emotion_summary = df['emotion'].value_counts(normalize=True).mul(100).round(1).to_dict()

    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Proctoring Session Integrity Report", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    summary_data = [
        ['Student ID:', student_id],
        ['Session ID:', session_id], # Add session to summary
        ['Exam Start Time:', start_time],
        ['Exam End Time:', end_time],
        ['Final Integrity Score:', f"{final_score} / 100"],
        ['Total Alert Events:', str(total_alerts)],
    ]
    # ... (rest of the table and PDF styling is the same)
    summary_table = Table(summary_data, hAlign='LEFT', colWidths=[1.5 * inch, 4 * inch])
    summary_table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'), ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 1, colors.lightgrey)]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Emotion Distribution", styles['h2']))
    emotion_str = ", ".join([f"{k}: {v}%" for k, v in emotion_summary.items()])
    story.append(Paragraph(emotion_str, styles['BodyText']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Critical Alert Timeline", styles['h2']))
    if not alert_events.empty:
        log_data = [['Time', 'Alerts Triggered', 'Score']]
        for _, row in alert_events.iterrows():
            log_data.append([row['timestamp'].strftime('%H:%M:%S'), Paragraph(", ".join(row['alerts']), styles['BodyText']), str(row['integrity_score'])])
        log_table = Table(log_data, colWidths=[1 * inch, 4.5 * inch, 0.5 * inch])
        log_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        story.append(log_table)
    else:
        story.append(Paragraph("No alert events recorded.", styles['BodyText']))

    doc.build(story)
    return output_filename