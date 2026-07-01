from flask import Flask, request, jsonify
import sqlite3
import hashlib

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS keys (key TEXT PRIMARY KEY, fingerprint TEXT)')
    conn.commit()
    conn.close()

@app.route('/activate', methods=['POST'])
def activate():
    data = request.json
    key = data.get('key')
    fingerprint = data.get('fingerprint')
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute('SELECT fingerprint FROM keys WHERE key = ?', (key,))
    row = c.fetchone()
    if row:
        if row[0] == fingerprint:
            return jsonify({'status': 'ok', 'message': 'Active'})
        else:
            return jsonify({'status': 'error', 'message': 'Key already used on another device'})
    else:
        c.execute('INSERT INTO keys VALUES (?, ?)', (key, fingerprint))
        conn.commit()
        return jsonify({'status': 'ok', 'message': 'Activated for first time'})
    conn.close()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
