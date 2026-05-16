import sqlite3
import os
import uuid
from datetime import datetime

def get_db_path():
    return os.getenv('DATABASE_PATH', 'database/shiftiq.db')

def init_database():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS workers (worker_id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, max_hours_per_week INTEGER NOT NULL, is_active INTEGER DEFAULT 1)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS availability (availability_id TEXT PRIMARY KEY, worker_id TEXT NOT NULL, day_of_week TEXT NOT NULL, shift TEXT NOT NULL, is_available INTEGER DEFAULT 1, FOREIGN KEY (worker_id) REFERENCES workers(worker_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS coverage_requirements (requirement_id TEXT PRIMARY KEY, day_of_week TEXT NOT NULL, shift TEXT NOT NULL, min_workers INTEGER NOT NULL, preferred_workers INTEGER NOT NULL, role_required TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS schedules (schedule_id TEXT PRIMARY KEY, week_start_date TEXT NOT NULL, generated_at TIMESTAMP NOT NULL, agent_summary TEXT, status TEXT DEFAULT 'DRAFT')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS schedule_assignments (assignment_id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL, worker_id TEXT NOT NULL, day_of_week TEXT NOT NULL, shift TEXT NOT NULL, role TEXT NOT NULL, FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id), FOREIGN KEY (worker_id) REFERENCES workers(worker_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS conflicts (conflict_id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL, conflict_type TEXT NOT NULL, day_of_week TEXT NOT NULL, shift TEXT NOT NULL, description TEXT NOT NULL, FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id))''')
    
    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM workers')
    if cursor.fetchone()[0] == 0:
        seed_database(conn, cursor)
    conn.close()
    print(f"Database initialized at {db_path}")

def seed_database(conn, cursor):
    workers_data = [('Maria Rossi', 'Cashier', 40), ('Luca Bianchi', 'Cashier', 35), ('Sofia Romano', 'Supervisor', 40), ('Marco Ferrari', 'Technician', 40), ('Giulia Esposito', 'Cashier', 30), ('Alessandro Conti', 'Technician', 40), ('Francesca Ricci', 'Supervisor', 35), ('Giovanni Marino', 'Cashier', 25), ('Chiara Greco', 'Technician', 40), ('Matteo Bruno', 'Cashier', 30)]
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    shifts = ['Morning', 'Evening']
    worker_ids = []
    for name, role, max_hours in workers_data:
        worker_id = str(uuid.uuid4())
        worker_ids.append((worker_id, name, role))
        cursor.execute('INSERT INTO workers (worker_id, name, role, max_hours_per_week, is_active) VALUES (?, ?, ?, ?, 1)', (worker_id, name, role, max_hours))
    
    availability_patterns = {0: {'Monday': ['Morning', 'Evening'], 'Tuesday': ['Morning', 'Evening'], 'Wednesday': ['Morning'], 'Thursday': ['Morning', 'Evening'], 'Friday': ['Morning'], 'Saturday': ['Morning', 'Evening'], 'Sunday': []}, 1: {'Monday': ['Evening'], 'Tuesday': ['Morning', 'Evening'], 'Wednesday': ['Evening'], 'Thursday': ['Morning'], 'Friday': ['Evening'], 'Saturday': [], 'Sunday': ['Morning']}, 2: {'Monday': ['Morning', 'Evening'], 'Tuesday': ['Morning', 'Evening'], 'Wednesday': ['Morning', 'Evening'], 'Thursday': ['Morning', 'Evening'], 'Friday': ['Morning', 'Evening'], 'Saturday': ['Morning'], 'Sunday': []}, 3: {'Monday': ['Morning'], 'Tuesday': ['Morning'], 'Wednesday': ['Morning', 'Evening'], 'Thursday': ['Evening'], 'Friday': ['Morning', 'Evening'], 'Saturday': ['Evening'], 'Sunday': ['Morning']}, 4: {'Monday': ['Morning'], 'Tuesday': ['Evening'], 'Wednesday': ['Morning'], 'Thursday': ['Evening'], 'Friday': [], 'Saturday': ['Morning', 'Evening'], 'Sunday': ['Evening']}, 5: {'Monday': ['Evening'], 'Tuesday': ['Morning', 'Evening'], 'Wednesday': ['Evening'], 'Thursday': ['Morning', 'Evening'], 'Friday': ['Morning'], 'Saturday': ['Morning'], 'Sunday': []}, 6: {'Monday': ['Morning', 'Evening'], 'Tuesday': ['Morning'], 'Wednesday': ['Morning', 'Evening'], 'Thursday': ['Morning'], 'Friday': ['Evening'], 'Saturday': ['Morning', 'Evening'], 'Sunday': []}, 7: {'Monday': [], 'Tuesday': ['Evening'], 'Wednesday': ['Morning'], 'Thursday': ['Morning', 'Evening'], 'Friday': ['Morning'], 'Saturday': ['Evening'], 'Sunday': ['Morning', 'Evening']}, 8: {'Monday': ['Morning', 'Evening'], 'Tuesday': ['Morning'], 'Wednesday': ['Morning'], 'Thursday': ['Morning', 'Evening'], 'Friday': ['Evening'], 'Saturday': ['Morning'], 'Sunday': []}, 9: {'Monday': ['Evening'], 'Tuesday': ['Morning'], 'Wednesday': ['Evening'], 'Thursday': ['Morning'], 'Friday': [], 'Saturday': ['Morning'], 'Sunday': ['Evening']}}
    
    for idx, (worker_id, name, role) in enumerate(worker_ids):
        pattern = availability_patterns[idx]
        for day in days:
            for shift in shifts:
                availability_id = str(uuid.uuid4())
                is_available = 1 if shift in pattern.get(day, []) else 0
                cursor.execute('INSERT INTO availability (availability_id, worker_id, day_of_week, shift, is_available) VALUES (?, ?, ?, ?, ?)', (availability_id, worker_id, day, shift, is_available))
    
    coverage_reqs = [('Monday', 'Morning', 3, 4, None), ('Monday', 'Evening', 2, 3, None), ('Tuesday', 'Morning', 3, 4, None), ('Tuesday', 'Evening', 2, 3, None), ('Wednesday', 'Morning', 3, 4, None), ('Wednesday', 'Evening', 2, 3, None), ('Thursday', 'Morning', 3, 4, None), ('Thursday', 'Evening', 2, 3, None), ('Friday', 'Morning', 4, 5, None), ('Friday', 'Evening', 3, 4, 'Cashier'), ('Saturday', 'Morning', 3, 4, None), ('Saturday', 'Evening', 2, 3, None), ('Sunday', 'Morning', 2, 3, None), ('Sunday', 'Evening', 1, 2, None)]
    
    for day, shift, min_w, pref_w, role_req in coverage_reqs:
        req_id = str(uuid.uuid4())
        cursor.execute('INSERT INTO coverage_requirements (requirement_id, day_of_week, shift, min_workers, preferred_workers, role_required) VALUES (?, ?, ?, ?, ?, ?)', (req_id, day, shift, min_w, pref_w, role_req))
    
    conn.commit()
    print("Database seeded with 10 workers and coverage requirements")

if __name__ == '__main__':
    init_database()
