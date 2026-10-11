from flask import Flask, render_template, request, jsonify, session
import random, string, os

app = Flask(__name__)
app.secret_key = 'secret-santa-2025'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

rooms = {}

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    session['name'] = data['name']
    return jsonify({"ok": True})

@app.route('/api/create_room', methods=['POST'])
def create_room():
    name = session.get('name')
    code = gen_code()
    rooms[code] = {
        "creator": name,
        "members": [{"name": name}],
        "shuffled": False,
        "assignments": {}
    }
    return jsonify({"code": code})

@app.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.json
    code = data['code'].upper()
    name = session.get('name')
    if code not in rooms:
        return jsonify({"error": "Room code thappu da!"}), 400
    room = rooms[code]
    if room['shuffled']:
        return jsonify({"error": "Already shuffle pannitanga!"}), 400
    if not any(m['name']==name for m in room['members']):
        room['members'].append({"name": name})
    return jsonify({"code": code})

@app.route('/api/room/<code>')
def get_room(code):
    code = code.upper()
    if code not in rooms:
        return jsonify({"error": "Room illa"}), 404
    room = rooms[code]
    name = session.get('name')
    my_assignment = room['assignments'].get(name) if room['shuffled'] else None
    return jsonify({
        "code": code,
        "creator": room['creator'],
        "members": room['members'],
        "is_creator": room['creator'] == name,
        "shuffled": room['shuffled'],
        "my_assignment": my_assignment,
        "my_name": name
    })

@app.route('/api/shuffle/<code>', methods=['POST'])
def shuffle_room(code):
    code = code.upper()
    room = rooms[code]
    name = session.get('name')
    if room['creator']!= name:
        return jsonify({"error": "Creator mattum!"}), 403
    members = [m['name'] for m in room['members']]
    if len(members) < 2:
        return jsonify({"error": "2 perachum venum!"}), 400
    receivers = members[:]
    while True:
        random.shuffle(receivers)
        if all(g!= r for g, r in zip(members, receivers)):
            break
    assignments = {g: r for g, r in zip(members, receivers)}
    room['assignments'] = assignments
    room['shuffled'] = True
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
