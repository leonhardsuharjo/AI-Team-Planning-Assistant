import os
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from database.init_db import init_database
from agent.shiftiq_agent import run_agent

load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'shiftiq-local-key')

def get_db_connection():
    db_path = os.getenv('DATABASE_PATH', 'database/shiftiq.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/workers', methods=['GET'])
def get_workers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT worker_id, name, role, max_hours_per_week, is_active FROM workers WHERE is_active = 1')
    workers = []
    for row in cursor.fetchall():
        worker = dict(row)
        worker_id = worker['worker_id']
        cursor.execute('SELECT day_of_week, shift, is_available FROM availability WHERE worker_id = ?', (worker_id,))
        availability = {}
        for avail_row in cursor.fetchall():
            day = avail_row['day_of_week']
            shift = avail_row['shift']
            if day not in availability:
                availability[day] = {}
            availability[day][shift] = bool(avail_row['is_available'])
        worker['availability'] = availability
        workers.append(worker)
    conn.close()
    return jsonify(workers)

@app.route('/api/workers', methods=['POST'])
def create_worker():
    data = request.json
    name = data.get('name')
    role = data.get('role')
    max_hours = data.get('max_hours_per_week', 40)
    if not name or not role:
        return jsonify({'error': 'Name and role are required'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    worker_id = str(uuid.uuid4())
    cursor.execute('INSERT INTO workers (worker_id, name, role, max_hours_per_week, is_active) VALUES (?, ?, ?, ?, 1)', (worker_id, name, role, max_hours))
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    shifts = ['Morning', 'Evening']
    for day in days:
        for shift in shifts:
            availability_id = str(uuid.uuid4())
            cursor.execute('INSERT INTO availability (availability_id, worker_id, day_of_week, shift, is_available) VALUES (?, ?, ?, ?, 0)', (availability_id, worker_id, day, shift))
    conn.commit()
    conn.close()
    return jsonify({'worker_id': worker_id, 'name': name, 'role': role, 'max_hours_per_week': max_hours}), 201

@app.route('/api/workers/<worker_id>/availability', methods=['GET'])
def get_worker_availability(worker_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT day_of_week, shift, is_available FROM availability WHERE worker_id = ?', (worker_id,))
    availability = {}
    for row in cursor.fetchall():
        day = row['day_of_week']
        shift = row['shift']
        if day not in availability:
            availability[day] = {}
        availability[day][shift] = bool(row['is_available'])
    conn.close()
    return jsonify(availability)

@app.route('/api/workers/<worker_id>/availability', methods=['POST'])
def update_worker_availability(worker_id):
    data = request.json
    day_of_week = data.get('day_of_week')
    shift = data.get('shift')
    is_available = data.get('is_available', 1)
    if not day_of_week or not shift:
        return jsonify({'error': 'day_of_week and shift are required'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE availability SET is_available = ? WHERE worker_id = ? AND day_of_week = ? AND shift = ?', (is_available, worker_id, day_of_week, shift))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/coverage-requirements', methods=['GET'])
def get_coverage_requirements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT requirement_id, day_of_week, shift, min_workers, preferred_workers, role_required FROM coverage_requirements')
    requirements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(requirements)

@app.route('/api/coverage-requirements', methods=['POST'])
def upsert_coverage_requirement():
    data = request.json
    day_of_week = data.get('day_of_week')
    shift = data.get('shift')
    min_workers = data.get('min_workers')
    preferred_workers = data.get('preferred_workers')
    role_required = data.get('role_required')
    if not day_of_week or not shift or min_workers is None:
        return jsonify({'error': 'day_of_week, shift, and min_workers are required'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT requirement_id FROM coverage_requirements WHERE day_of_week = ? AND shift = ?', (day_of_week, shift))
    existing = cursor.fetchone()
    if existing:
        cursor.execute('UPDATE coverage_requirements SET min_workers = ?, preferred_workers = ?, role_required = ? WHERE day_of_week = ? AND shift = ?', (min_workers, preferred_workers, role_required, day_of_week, shift))
    else:
        requirement_id = str(uuid.uuid4())
        cursor.execute('INSERT INTO coverage_requirements (requirement_id, day_of_week, shift, min_workers, preferred_workers, role_required) VALUES (?, ?, ?, ?, ?, ?)', (requirement_id, day_of_week, shift, min_workers, preferred_workers, role_required))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/generate-schedule', methods=['POST'])
def generate_schedule():
    try:
        schedule_id = run_agent()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT schedule_id, week_start_date, generated_at, agent_summary, status FROM schedules WHERE schedule_id = ?', (schedule_id,))
        schedule = dict(cursor.fetchone())
        conn.close()
        return jsonify({'schedule_id': schedule_id, 'summary': schedule['agent_summary'], 'status': schedule['status']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT schedule_id, week_start_date, generated_at, agent_summary, status FROM schedules ORDER BY generated_at DESC')
    schedules = []
    for row in cursor.fetchall():
        schedule = dict(row)
        schedule_id = schedule['schedule_id']
        cursor.execute('SELECT COUNT(*) as count FROM schedule_assignments WHERE schedule_id = ?', (schedule_id,))
        schedule['assignment_count'] = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) as count FROM conflicts WHERE schedule_id = ?', (schedule_id,))
        schedule['conflict_count'] = cursor.fetchone()['count']
        schedules.append(schedule)
    conn.close()
    return jsonify(schedules)

@app.route('/api/schedules/<schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT schedule_id, week_start_date, generated_at, agent_summary, status FROM schedules WHERE schedule_id = ?', (schedule_id,))
    schedule_row = cursor.fetchone()
    if not schedule_row:
        conn.close()
        return jsonify({'error': 'Schedule not found'}), 404
    schedule = dict(schedule_row)
    cursor.execute('SELECT sa.assignment_id, sa.worker_id, w.name as worker_name, sa.day_of_week, sa.shift, sa.role FROM schedule_assignments sa JOIN workers w ON sa.worker_id = w.worker_id WHERE sa.schedule_id = ?', (schedule_id,))
    assignments = [dict(row) for row in cursor.fetchall()]
    cursor.execute('SELECT conflict_id, conflict_type, day_of_week, shift, description FROM conflicts WHERE schedule_id = ?', (schedule_id,))
    conflicts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    schedule['assignments'] = assignments
    schedule['conflicts'] = conflicts
    return jsonify(schedule)

@app.route('/api/schedules/<schedule_id>/confirm', methods=['POST'])
def confirm_schedule(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE schedules SET status = ? WHERE schedule_id = ?', ('CONFIRMED', schedule_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'status': 'CONFIRMED'})

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=True)
