import os
import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

try:
    from ibm_watson_machine_learning.foundation_models import Model
    from ibm_watson_machine_learning.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False
    print("Warning: ibm-watson-machine-learning not available. Using fallback mode.")

def get_db_connection():
    db_path = os.getenv('DATABASE_PATH', 'database/shiftiq.db')
    return sqlite3.connect(db_path)

def get_worker_availability() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT w.worker_id, w.name, w.role, w.max_hours_per_week, a.day_of_week, a.shift, a.is_available FROM workers w JOIN availability a ON w.worker_id = a.worker_id WHERE w.is_active = 1 ORDER BY w.name, a.day_of_week, a.shift''')
    rows = cursor.fetchall()
    conn.close()
    workers = {}
    for worker_id, name, role, max_hours, day, shift, is_available in rows:
        if worker_id not in workers:
            workers[worker_id] = {'name': name, 'role': role, 'max_hours_per_week': max_hours, 'availability': {}}
        if day not in workers[worker_id]['availability']:
            workers[worker_id]['availability'][day] = {}
        workers[worker_id]['availability'][day][shift] = bool(is_available)
    return workers

def get_coverage_requirements() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT day_of_week, shift, min_workers, preferred_workers, role_required FROM coverage_requirements ORDER BY CASE day_of_week WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 END, CASE shift WHEN 'Morning' THEN 1 WHEN 'Evening' THEN 2 WHEN 'Night' THEN 3 END''')
    requirements = []
    for row in cursor.fetchall():
        requirements.append({'day_of_week': row[0], 'shift': row[1], 'min_workers': row[2], 'preferred_workers': row[3], 'role_required': row[4]})
    conn.close()
    return requirements

def detect_conflicts(workers: Dict, requirements: List[Dict]) -> List[Dict[str, Any]]:
    conflicts = []
    for req in requirements:
        day = req['day_of_week']
        shift = req['shift']
        min_workers = req['min_workers']
        role_required = req['role_required']
        available_workers = []
        for worker_id, worker_data in workers.items():
            if worker_data['availability'].get(day, {}).get(shift, False):
                if role_required is None or worker_data['role'] == role_required:
                    available_workers.append(worker_data['name'])
        if len(available_workers) < min_workers:
            conflicts.append({'type': 'UNDERSTAFFED', 'day_of_week': day, 'shift': shift, 'description': f"{day} {shift} needs {min_workers} workers but only {len(available_workers)} available", 'available_workers': available_workers, 'required': min_workers})
    return conflicts

def generate_schedule_with_granite(workers: Dict, requirements: List[Dict], conflicts: List[Dict]) -> Dict[str, Any]:
    if not WATSONX_AVAILABLE or not os.getenv('IBMWATSONX_API_KEY'):
        return fallback_schedule_generation(workers, requirements, conflicts)
    try:
        credentials = {"url": os.getenv('IBMWATSONX_URL', 'https://us-south.ml.cloud.ibm.com'), "apikey": os.getenv('IBMWATSONX_API_KEY')}
        project_id = os.getenv('IBMWATSONX_PROJECT_ID')
        model_id = "ibm/granite-13b-instruct-v2"
        parameters = {GenParams.DECODING_METHOD: "greedy", GenParams.MAX_NEW_TOKENS: 2000, GenParams.MIN_NEW_TOKENS: 100, GenParams.TEMPERATURE: 0.7, GenParams.TOP_K: 50, GenParams.TOP_P: 1}
        model = Model(model_id=model_id, params=parameters, credentials=credentials, project_id=project_id)
        prompt = build_granite_prompt(workers, requirements, conflicts)
        response = model.generate_text(prompt=prompt, guardrails=False)
        return parse_granite_response(response, workers, requirements, conflicts)
    except Exception as e:
        print(f"Granite API error: {e}. Falling back to rule-based scheduling.")
        return fallback_schedule_generation(workers, requirements, conflicts)

def build_granite_prompt(workers: Dict, requirements: List[Dict], conflicts: List[Dict]) -> str:
    prompt = "You are an AI shift scheduling assistant. Generate a weekly work schedule based on the following information.\n\nWORKERS AND AVAILABILITY:\n"
    for worker_id, worker_data in workers.items():
        prompt += f"\n{worker_data['name']} ({worker_data['role']}, max {worker_data['max_hours_per_week']}h/week):\n"
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            avail = worker_data['availability'].get(day, {})
            morning = "✓" if avail.get('Morning', False) else "✗"
            evening = "✓" if avail.get('Evening', False) else "✗"
            prompt += f"  {day}: Morning {morning}, Evening {evening}\n"
    prompt += "\nCOVERAGE REQUIREMENTS:\n"
    for req in requirements:
        role_note = f" ({req['role_required']} required)" if req['role_required'] else ""
        prompt += f"{req['day_of_week']} {req['shift']}: {req['min_workers']}-{req['preferred_workers']} workers{role_note}\n"
    prompt += "\nDETECTED CONFLICTS:\n"
    for conflict in conflicts:
        prompt += f"- {conflict['description']}\n"
    prompt += "\nTASK: Generate a complete weekly schedule that:\n1. Assigns workers to shifts based on their availability\n2. Meets minimum staffing requirements where possible\n3. Respects worker max hours per week\n4. Resolves the detected conflicts\n\nOUTPUT FORMAT (provide exactly this structure):\nASSIGNMENTS:\nDay|Shift|Worker|Role\n[List all assignments in this format]\n\nSUMMARY:\n[2-3 sentence summary of the schedule]\n\nCONFLICT RESOLUTIONS:\n[Explain how each conflict was resolved]\n\nQUALITY: [Optimal/Acceptable/Understaffed]\n\nRECOMMENDATIONS:\n[2-3 recommendations for improving future schedules]\n"
    return prompt

def parse_granite_response(response: str, workers: Dict, requirements: List[Dict], conflicts: List[Dict]) -> Dict[str, Any]:
    assignments = []
    summary = ""
    quality = "Acceptable"
    recommendations = []
    conflict_resolutions = {}
    lines = response.split('\n')
    section = None
    for line in lines:
        line = line.strip()
        if line.startswith('ASSIGNMENTS:'):
            section = 'assignments'
            continue
        elif line.startswith('SUMMARY:'):
            section = 'summary'
            continue
        elif line.startswith('CONFLICT RESOLUTIONS:'):
            section = 'resolutions'
            continue
        elif line.startswith('QUALITY:'):
            section = 'quality'
            quality_match = line.replace('QUALITY:', '').strip()
            if quality_match in ['Optimal', 'Acceptable', 'Understaffed']:
                quality = quality_match
            continue
        elif line.startswith('RECOMMENDATIONS:'):
            section = 'recommendations'
            continue
        if section == 'assignments' and '|' in line and not line.startswith('Day|'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                assignments.append({'day_of_week': parts[0], 'shift': parts[1], 'worker_name': parts[2], 'role': parts[3]})
        elif section == 'summary' and line:
            summary += line + " "
        elif section == 'resolutions' and line:
            conflict_resolutions[len(conflict_resolutions)] = line
        elif section == 'recommendations' and line and line.startswith('-'):
            recommendations.append(line[1:].strip())
    if not assignments:
        return fallback_schedule_generation(workers, requirements, conflicts)
    return {'assignments': assignments, 'summary': summary.strip(), 'quality': quality, 'recommendations': recommendations, 'conflict_resolutions': conflict_resolutions, 'used_fallback': False}

def fallback_schedule_generation(workers: Dict, requirements: List[Dict], conflicts: List[Dict]) -> Dict[str, Any]:
    assignments = []
    worker_hours = {wid: 0 for wid in workers.keys()}
    for req in requirements:
        day = req['day_of_week']
        shift = req['shift']
        min_workers = req['min_workers']
        role_required = req['role_required']
        available = []
        for worker_id, worker_data in workers.items():
            if worker_data['availability'].get(day, {}).get(shift, False):
                if role_required is None or worker_data['role'] == role_required:
                    if worker_hours[worker_id] + 8 <= worker_data['max_hours_per_week']:
                        available.append((worker_id, worker_data))
        available.sort(key=lambda x: worker_hours[x[0]])
        assigned_count = min(len(available), min_workers)
        for i in range(assigned_count):
            worker_id, worker_data = available[i]
            assignments.append({'day_of_week': day, 'shift': shift, 'worker_name': worker_data['name'], 'role': worker_data['role']})
            worker_hours[worker_id] += 8
    summary = f"Rule-based schedule generated with {len(assignments)} assignments. Watsonx API unavailable."
    return {'assignments': assignments, 'summary': summary, 'quality': 'Acceptable', 'recommendations': ['Enable watsonx API for AI-powered scheduling', 'Review understaffed shifts manually'], 'conflict_resolutions': {0: 'Used rule-based assignment - watsonx unavailable'}, 'used_fallback': True}

def run_agent() -> str:
    print("Step 1: Getting worker availability...")
    workers = get_worker_availability()
    print("Step 2: Getting coverage requirements...")
    requirements = get_coverage_requirements()
    print("Step 3: Detecting conflicts...")
    conflicts = detect_conflicts(workers, requirements)
    print(f"Step 4: Generating schedule with Granite (found {len(conflicts)} conflicts)...")
    schedule_result = generate_schedule_with_granite(workers, requirements, conflicts)
    conn = get_db_connection()
    cursor = conn.cursor()
    schedule_id = str(uuid.uuid4())
    week_start = datetime.now().strftime('%Y-%m-%d')
    generated_at = datetime.now().isoformat()
    cursor.execute('INSERT INTO schedules (schedule_id, week_start_date, generated_at, agent_summary, status) VALUES (?, ?, ?, ?, ?)', (schedule_id, week_start, generated_at, schedule_result['summary'], 'DRAFT'))
    worker_name_to_id = {w['name']: wid for wid, w in workers.items()}
    for assignment in schedule_result['assignments']:
        assignment_id = str(uuid.uuid4())
        worker_name = assignment['worker_name']
        worker_id = worker_name_to_id.get(worker_name)
        if worker_id:
            cursor.execute('INSERT INTO schedule_assignments (assignment_id, schedule_id, worker_id, day_of_week, shift, role) VALUES (?, ?, ?, ?, ?, ?)', (assignment_id, schedule_id, worker_id, assignment['day_of_week'], assignment['shift'], assignment['role']))
    for conflict in conflicts:
        conflict_id = str(uuid.uuid4())
        resolution = schedule_result['conflict_resolutions'].get(0, 'Addressed in schedule generation')
        description = f"{conflict['description']}. Resolution: {resolution}"
        cursor.execute('INSERT INTO conflicts (conflict_id, schedule_id, conflict_type, day_of_week, shift, description) VALUES (?, ?, ?, ?, ?, ?)', (conflict_id, schedule_id, conflict['type'], conflict['day_of_week'], conflict['shift'], description))
    conn.commit()
    conn.close()
    print(f"Schedule generated successfully: {schedule_id}")
    return schedule_id

if __name__ == '__main__':
    run_agent()
