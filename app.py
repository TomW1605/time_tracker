import os

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

# get env variables
port = int(os.getenv('PORT', 5000))

app = Flask(__name__)

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

    def __repr__(self):
        return f'<WorkSession({self.id}, {self.session_type}, {self.date}, {self.hours_worked}, {self.clock_in_time}, {self.clock_out_time})>'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/log_hours', methods=['GET'])
def log_hours():
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('log_hours.html', current_date=current_date)

@app.route('/clock_in', methods=['GET'])
def clock_in():
    current_time = datetime.now().strftime('%H:%M:%S')
    return render_template('clock_in.html', current_time=current_time)

@app.route('/clock_out', methods=['GET'])
def clock_out():
    current_time = datetime.now().strftime('%H:%M:%S')
    return render_template('clock_out.html', current_time=current_time)

@app.route('/summary')
def summary():
    return render_template('summary.html')

@app.route('/edit/<int:id>', methods=['GET'])
def edit(id):
    return render_template('edit.html', session_id=id)

@app.route('/api/hours_this_week')
def api_hours_this_week():
    now = datetime.now()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    sessions = WorkSession.query.filter(WorkSession.date >= start_of_week.date(), WorkSession.date <= end_of_week.date(), WorkSession.hours_worked > 0).all()
    total_hours = sum(session.hours_worked for session in sessions)
    return jsonify({'hours_this_week': round(total_hours, 1)})

@app.route('/api/log_hours', methods=['POST'])
def api_log_hours():
    data = request.get_json()
    date = data['date']
    hours_worked = float(data['hours_worked'])
    new_session = WorkSession(session_type='hours', date=datetime.strptime(date, '%Y-%m-%d').date(), hours_worked=round(hours_worked, 1))
    db.session.add(new_session)
    db.session.commit()
    return jsonify({'message': 'Logged hours successfully'}), 201

@app.route('/api/clock_in', methods=['POST'])
def api_clock_in():
    data = request.get_json()
    now = datetime.now()
    date = now.date()
    time_str = data['clock_in_time']
    time = datetime.strptime(time_str, '%H:%M:%S').time()
    clock_in_time = datetime.combine(date, time).replace(second=0, microsecond=0)
    new_session = WorkSession(session_type='in/out', date=clock_in_time.date(), clock_in_time=clock_in_time)
    db.session.add(new_session)
    db.session.commit()
    return jsonify({'message': 'Clocked in successfully'}), 201

@app.route('/api/clock_out', methods=['POST'])
def api_clock_out():
    data = request.get_json()
    session = WorkSession.query.filter_by(session_type='in/out', clock_out_time=None).order_by(WorkSession.clock_in_time.desc()).first()
    if not session:
        return jsonify({'error': 'No active clock-in session found'}), 404

    now = datetime.now()
    date = now.date()
    time_str = data['clock_out_time']
    time = datetime.strptime(time_str, '%H:%M:%S').time()
    clock_out_time = datetime.combine(date, time).replace(second=0, microsecond=0)
    session.clock_out_time = clock_out_time
    session.hours_worked = round((clock_out_time - session.clock_in_time).total_seconds() / 3600, 1)
    db.session.commit()
    return jsonify({'message': 'Clocked out successfully'}), 200

@app.route('/api/edit_session/<int:id>', methods=['POST'])
def api_edit_session(id):
    data = request.get_json()
    session = WorkSession.query.get_or_404(id)
    session.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    if session.session_type == 'hours':
        session.hours_worked = round(float(data['hours_worked']), 1)
    else:
        clock_in_time = datetime.combine(session.date, datetime.strptime(data['clock_in_time'], '%H:%M:%S').time()).replace(second=0, microsecond=0)
        clock_out_time = datetime.combine(session.date, datetime.strptime(data['clock_out_time'], '%H:%M:%S').time()).replace(second=0, microsecond=0)
        session.clock_in_time = clock_in_time
        session.clock_out_time = clock_out_time
        session.hours_worked = round((clock_out_time - clock_in_time).total_seconds() / 3600, 1)
    db.session.commit()
    return jsonify({'message': 'Session updated successfully'}), 200

@app.route('/api/get_sessions', methods=['GET'])
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

@app.route('/api/get_session/<int:id>', methods=['GET'])
def api_get_session(id):
    session = WorkSession.query.get_or_404(id)
    session_data = {
        'id': session.id,
        'session_type': session.session_type,
        'date': session.date.strftime('%Y-%m-%d'),
        'hours_worked': session.hours_worked,
        'clock_in_time': session.clock_in_time.strftime('%H:%M:%S') if session.clock_in_time else None,
        'clock_out_time': session.clock_out_time.strftime('%H:%M:%S') if session.clock_out_time else None
    }
    return jsonify(session_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=port, debug=True)
