import os

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

from sqlalchemy import ForeignKey

# get env variables
port = int(os.getenv('PORT', 5000))
base_url = os.getenv('BASE_URL', '/time_tracker')
hours_per_day = os.getenv('HOURS_PER_DAY', 7.6)
days_per_week = os.getenv('DAYS_PER_WEEK', 5)
# hours_per_week = (hours_per_day*days_per_week)

# Ensure base_url has leading and trailing slashes
if not base_url.startswith('/'):
    base_url = '/' + base_url
if not base_url.endswith('/'):
    base_url = base_url + '/'

app = Flask(__name__, static_url_path=base_url + 'static')

# Ensure the config directory exists
os.makedirs('/config', exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:////config/work_hours.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class WorkSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_type = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours_worked = db.Column(db.Float, nullable=True)
    clock_in_time = db.Column(db.DateTime, nullable=True)
    clock_out_time = db.Column(db.DateTime, nullable=True)
    comment = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<WorkSession({self.id}, {self.session_type}, {self.date}, {self.hours_worked}, {self.clock_in_time}, {self.clock_out_time})>'

class Edit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, ForeignKey(WorkSession.id), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    changes = db.Column(db.Text, nullable=True)
    comment = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Edit({self.id}, {self.session_id}, {self.date}, {self.changes}, {self.comment})>'

@app.route(base_url)
def index():
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M:%S')
    return render_template('index.html', current_date=current_date, current_time=current_time)

@app.route(base_url + 'edit/<int:id>', methods=['GET'])
def edit(id):
    return render_template('edit.html', session_id=id)

@app.route(base_url + 'api/log_hours', methods=['POST'])
def api_log_hours():
    data = request.get_json()
    date = data['date']
    hours_worked = float(data['hours_worked'])
    new_session = WorkSession(session_type='hours', date=datetime.strptime(date, '%Y-%m-%d').date(), hours_worked=round(hours_worked, 1))
    db.session.add(new_session)
    db.session.commit()
    return jsonify({'message': 'Logged hours successfully'}), 201

@app.route(base_url + 'api/clock_in', methods=['POST'])
def api_clock_in():
    hours_this_week = get_hours_week()
    hours_today = get_hours_today()

    data = request.get_json()
    now = datetime.now()
    date = now.date()
    time_str = data['clock_in_time']
    time = datetime.strptime(time_str, '%H:%M:%S').time()
    clock_in_time = datetime.combine(date, time).replace(second=0, microsecond=0)
    new_session = WorkSession(session_type='clocked', date=clock_in_time.date(), clock_in_time=clock_in_time)
    db.session.add(new_session)
    db.session.commit()
    if date.weekday() == 4: #if friday
        # print(hours_this_week)
        hours_remaining = (hours_per_day*days_per_week)-hours_this_week
        # print(hours_remaining)
        leave_time = clock_in_time + timedelta(hours=hours_remaining)
        # print(leave_time.strftime('%H:%M:%S'))
    else:
        leave_time = clock_in_time + timedelta(hours=hours_per_day - hours_today)
    return jsonify({'message': 'Clocked in successfully',
                    'leave_time': leave_time.strftime('%H:%M:%S')}), 201

@app.route(base_url + 'api/clock_out', methods=['POST'])
def api_clock_out():
    data = request.get_json()
    session = WorkSession.query.filter_by(session_type='clocked', clock_out_time=None).order_by(WorkSession.clock_in_time.desc()).first()
    if not session:
        return jsonify({
            'error': 'No active clock-in session found',
            'message': 'No active clock-in session found'
        }), 404

    now = datetime.now()
    date = now.date()
    time_str = data['clock_out_time']
    time = datetime.strptime(time_str, '%H:%M:%S').time()
    clock_out_time = datetime.combine(date, time).replace(second=0, microsecond=0)
    session.clock_out_time = clock_out_time
    session.hours_worked = round((clock_out_time - session.clock_in_time).total_seconds() / 3600, 1)
    db.session.commit()
    return jsonify({'message': f'Clocked out successfully',
                    'hours': session.hours_worked,
                    'hours_today': get_hours_today()}), 200

@app.route(base_url + 'api/edit_session/<int:id>', methods=['POST'])
def api_edit_session(id):
    data = request.get_json()
    session = WorkSession.query.get_or_404(id)

    new_data = {"date": datetime.strptime(data['date'], '%Y-%m-%d').date()}
    if session.session_type == 'hours':
        new_data["hours_worked"] = round(float(data['hours_worked']), 1)
    else:
        new_data["clock_in_time"] = False
        new_data["clock_out_time"] = False
        if data['clock_in_time']:
            new_data["clock_in_time"] = datetime.combine(session.date,
                                             datetime.strptime(data['clock_in_time'], '%H:%M:%S').time()).replace(
                second=0, microsecond=0)

        if data['clock_out_time']:
            new_data["clock_out_time"] = datetime.combine(session.date,
                                              datetime.strptime(data['clock_out_time'], '%H:%M:%S').time()).replace(
                second=0, microsecond=0)

        if new_data["clock_in_time"] and new_data["clock_out_time"]:
            new_data["hours_worked"] = round((new_data["clock_out_time"] - new_data["clock_in_time"]).total_seconds() / 3600, 1)
    new_data['comment'] = data['comment']

    changes = {}

    for key, value in new_data.items():
        if value != getattr(session, key):
            changes[key] = (getattr(session, key), value)

    change_str = ""
    for key, value in changes.items():
        change_str += f"{key}: '{value[0]}'->'{value[1]}', "
    change_str = change_str[:-2]

    if change_str:
        session_edit = Edit(session_id=id, date_time=datetime.now(), changes=change_str, comment=data['edit_comment'])
        db.session.add(session_edit)

        session.date = new_data["date"]
        if session.session_type == 'hours':
            session.hours_worked = new_data["hours_worked"]
        else:
            if data['clock_in_time']:
                session.clock_in_time = new_data["clock_in_time"]

            if data['clock_out_time']:
                session.clock_out_time = new_data["clock_out_time"]

            if new_data["clock_in_time"] and new_data["clock_out_time"]:
                session.hours_worked = new_data["hours_worked"]
        session.comment = data['comment']

        db.session.commit()
        return jsonify({'message': 'Session updated successfully'}), 200
    return jsonify({'message': 'No changes made'}), 200

@app.route(base_url + 'api/get_sessions', methods=['GET'])
def api_get_sessions():
    sessions = WorkSession.query.all()
    sessions_list = [
        {
            'id': session.id,
            'session_type': session.session_type,
            'date': session.date.strftime('%Y-%m-%d'),
            'hours_worked': session.hours_worked,
            'clock_in_time': session.clock_in_time.strftime('%Y-%m-%d %H:%M:%S') if session.clock_in_time else None,
            'clock_out_time': session.clock_out_time.strftime('%Y-%m-%d %H:%M:%S') if session.clock_out_time else None
        }
        for session in sessions
    ]
    return jsonify(sessions_list)

@app.route(base_url + 'api/get_sessions_grouped', methods=['GET'])
def api_get_sessions_grouped():
    sessions = WorkSession.query.all()
    weeks = {}
    for session in sessions:
        start_of_week = session.date - timedelta(days=session.date.weekday())
        end_of_week = start_of_week + timedelta(days=4)
        week = start_of_week.strftime('%Y-%m-%d')
        if week not in weeks:
            weeks[week] = {
                "start_date": start_of_week,
                "start": start_of_week.strftime('%d-%m-%Y'),
                "end": end_of_week.strftime('%d-%m-%Y'),
                "sessions": []
            }
        weeks[week]["sessions"].append({
            'id': session.id,
            'session_type': session.session_type,
            'date': session.date.strftime('%Y-%m-%d'),
            'hours_worked': session.hours_worked,
            'clock_in_time': session.clock_in_time.strftime('%Y-%m-%d %H:%M:%S') if session.clock_in_time else None,
            'clock_out_time': session.clock_out_time.strftime('%Y-%m-%d %H:%M:%S') if session.clock_out_time else None
        })

    for week in weeks:
        weeks[week]["hours_worked"] = get_hours_week(weeks[week]["start_date"])
        weeks[week]["hours_short"] = get_week_hours_deficit(weeks[week]["start_date"])
    return jsonify(weeks)

@app.route(base_url + 'api/get_session/<int:id>', methods=['GET'])
def api_get_session(id):
    session = WorkSession.query.get_or_404(id)

    edits = []
    for edit in Edit.query.filter_by(session_id=id).all():
        edits.append({
            'id': edit.id,
            'date_time': edit.date_time.strftime('%Y-%m-%d %H:%M:%S'),
            'changes': edit.changes,
            'comment': edit.comment,
        })

    session_data = {
        'id': session.id,
        'session_type': session.session_type,
        'date': session.date.strftime('%Y-%m-%d'),
        'hours_worked': session.hours_worked,
        'clock_in_time': session.clock_in_time.strftime('%H:%M:%S') if session.clock_in_time else None,
        'clock_out_time': session.clock_out_time.strftime('%H:%M:%S') if session.clock_out_time else None,
        'comment': session.comment,
        'edit_history': edits
    }
    return jsonify(session_data)

@app.route(base_url + 'api/delete_session/<int:id>', methods=['DELETE'])
def api_delete_session(id):
    session = WorkSession.query.get_or_404(id)
    db.session.delete(session)
    db.session.commit()
    return jsonify({'message': 'Session deleted successfully'}), 200

@app.route(base_url + 'api/get_hours', methods=['GET'])
def api_get_hours():
    return jsonify({
        'hours_today': get_hours_today(),
        'hours_this_week': get_hours_week(),
        'today_deficit': get_today_hours_deficit(),
        'week_deficit': get_week_hours_deficit(),
        'all_time_deficit': get_all_time_deficit()
    })

def get_hours_today():
    today = datetime.now().date()
    complete_sessions = WorkSession.query.filter(WorkSession.date == today, WorkSession.hours_worked > 0).all()
    running_sessions = WorkSession.query.filter(WorkSession.date == today, WorkSession.hours_worked == None).all()
    # print(running_sessions)
    total_hours = (sum(session.hours_worked for session in complete_sessions) +
                   sum(round((datetime.now() - session.clock_in_time).total_seconds() / 3600, 1) for session in running_sessions))
    return round(total_hours, 1)

def get_hours_week(now = datetime.now()):
    if isinstance(now, datetime):
        now = now.date()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    complete_sessions = WorkSession.query.filter(WorkSession.date >= start_of_week, WorkSession.date <= end_of_week, WorkSession.hours_worked > 0).all()
    running_sessions = WorkSession.query.filter(WorkSession.date >= start_of_week, WorkSession.date <= end_of_week, WorkSession.hours_worked == None).all()
    total_hours = (sum(session.hours_worked for session in complete_sessions) +
                   sum(round((datetime.now() - session.clock_in_time).total_seconds() / 3600, 1) for session in running_sessions))
    return round(total_hours, 1)

def get_hours_all_time():
    complete_sessions = WorkSession.query.filter(WorkSession.hours_worked > 0).all()
    running_sessions = WorkSession.query.filter(WorkSession.hours_worked == None).all()
    total_hours = (sum(session.hours_worked for session in complete_sessions) +
                   sum(round((datetime.now() - session.clock_in_time).total_seconds() / 3600, 1) for session in running_sessions))
    return round(total_hours, 1)

def get_today_hours_deficit():
    if datetime.now().weekday() in [5, 6]:
        return 0
    today_deficit = hours_per_day - get_hours_today()
    return today_deficit

def get_week_hours_deficit(now:datetime = datetime.now()):
    if now.isocalendar()[1] == datetime.now().isocalendar()[1] and datetime.now().weekday() < 5:
        week_target = hours_per_day * (datetime.now().weekday()+1)
    else:
        week_target = hours_per_day * days_per_week
    week_deficit = week_target - get_hours_week(now)
    return week_deficit

def get_all_time_deficit():
    sessions = WorkSession.query.all()
    weeks = []
    for session in sessions:
        week = session.date - timedelta(days=session.date.weekday())
        weeks.append(week)

    all_time_target = 0
    num_weeks = len(set(weeks))
    if datetime.now().weekday() < 5:
        num_weeks -= 1
        all_time_target += hours_per_day * (datetime.now().weekday()+1)

    all_time_target += (hours_per_day*days_per_week) * num_weeks
    all_time_deficit = all_time_target - get_hours_all_time()

    return all_time_deficit

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=port, debug=True)
