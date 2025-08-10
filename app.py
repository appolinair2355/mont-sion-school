from flask import Flask, render_template, request, jsonify, session
import yaml
import os
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuration
PORT = int(os.environ.get('PORT', 10000))
DATA_FILE = 'data/students.yaml'
USERS_FILE = 'data/users.yaml'

# Initialisation des fichiers YAML
def init_data_files():
    os.makedirs('data', exist_ok=True)
    
    if not os.path.exists(USERS_FILE):
        users_data = {
            'users': {
                'Kouamé': {'password': '02910291', 'role': 'admin'},
                'directrice': {'password': 'directrice123', 'role': 'admin'}
            }
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(users_data, f, allow_unicode=True, default_flow_style=False)
    
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            yaml.dump({'students': []}, f, allow_unicode=True, default_flow_style=False)

init_data_files()

# Fonctions utilitaires YAML
def load_yaml(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

def save_yaml(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

# Routes principales
@app.route('/')
def index():
    return render_template('index.html', school_name="Mont Sion")

@app.route('/inscription')
def inscription():
    return render_template('inscription.html', school_name="Mont Sion")

@app.route('/scolarite')
def scolarite():
    return render_template('scolarite.html', school_name="Mont Sion")

@app.route('/administration')
def administration():
    return render_template('administration.html', school_name="Mont Sion")

@app.route('/profil')
def profil():
    return render_template('profil.html', school_name="Mont Sion")

# API Endpoints
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    users_data = load_yaml(USERS_FILE)
    user = users_data.get('users', {}).get(username)
    
    if user and user['password'] == password:
        session['user'] = {'username': username, 'role': user['role']}
        return jsonify({'success': True, 'user': session['user']})
    
    return jsonify({'success': False, 'message': 'Identifiants incorrects'})

@app.route('/api/create-profile', methods=['POST'])
def create_profile():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    users_data = load_yaml(USERS_FILE)
    
    if username in users_data.get('users', {}):
        return jsonify({'success': False, 'message': 'Utilisateur existe déjà'})
    
    if 'users' not in users_data:
        users_data['users'] = {}
    
    users_data['users'][username] = {'password': password, 'role': role}
    save_yaml(USERS_FILE, users_data)
    
    return jsonify({'success': True, 'message': 'Profil créé avec succès'})

@app.route('/api/students', methods=['GET'])
def get_students():
    if not session.get('user'):
        return jsonify({'error': 'Non autorisé'}), 401
    
    data = load_yaml(DATA_FILE)
    return jsonify(data.get('students', []))

@app.route('/api/students', methods=['POST'])
def add_student():
    if not session.get('user'):
        return jsonify({'error': 'Non autorisé'}), 401
    
    student_data = request.json
    student_data['id'] = int(datetime.now().timestamp() * 1000)
    student_data['date_inscription'] = datetime.now().isoformat()
    student_data['frais_scolarite'] = 70000
    student_data['montant_paye'] = 0
    student_data['reste_a_payer'] = 70000
    
    data = load_yaml(DATA_FILE)
    if 'students' not in data:
        data['students'] = []
    
    data['students'].append(student_data)
    save_yaml(DATA_FILE, data)
    
    return jsonify({'success': True, 'student': student_data})

@app.route('/api/students/<int:student_id>/payment', methods=['POST'])
def add_payment(student_id):
    if not session.get('user') or session['user']['username'] not in ['Kouamé', 'directrice']:
        return jsonify({'error': 'Non autorisé'}), 401
    
    amount = request.json.get('amount', 0)
    
    data = load_yaml(DATA_FILE)
    students = data.get('students', [])
    
    for student in students:
        if student['id'] == student_id:
            student['montant_paye'] = student.get('montant_paye', 0) + amount
            student['reste_a_payer'] = 70000 - student['montant_paye']
            save_yaml(DATA_FILE, data)
            return jsonify({'success': True, 'student': student})
    
    return jsonify({'error': 'Élève non trouvé'}), 404

@app.route('/api/search-students')
def search_students():
    if not session.get('user'):
        return jsonify({'error': 'Non autorisé'}), 401
    
    query = request.args.get('q', '').lower()
    data = load_yaml(DATA_FILE)
    students = data.get('students', [])
    
    if query:
        students = [s for s in students if query in s['nom'].lower() or query in s['prenoms'].lower()]
    
    return jsonify(students)

@app.route('/api/stats')
def get_stats():
    if not session.get('user') or session['user']['username'] != 'Kouamé':
        return jsonify({'error': 'Non autorisé'}), 401
    
    data = load_yaml(DATA_FILE)
    students = data.get('students', [])
    
    total_students = len(students)
    total_expected = total_students * 70000
    total_collected = sum(s.get('montant_paye', 0) for s in students)
    total_remaining = total_expected - total_collected
    
    return jsonify({
        'total_students': total_students,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'total_remaining': total_remaining
    })

@app.route('/api/download-yaml')
def download_yaml():
    if not session.get('user'] or session['user']['username'] != 'Kouamé':
        return jsonify({'error': 'Non autorisé'}), 401
    
    data = load_yaml(DATA_FILE)
    yaml_content = yaml.dump(data, allow_unicode=True, default_flow_style=False)
    
    return yaml_content, 200, {
        'Content-Type': 'text/yaml',
        'Content-Disposition': 'attachment; filename=mont-sion-students.yaml'
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
  
