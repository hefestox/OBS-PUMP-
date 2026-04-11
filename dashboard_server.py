from flask import Flask, send_from_directory, jsonify
import os
import json

app = Flask(__name__)

# Caminho para o status.json gerado pelo bot
STATUS_PATH = os.path.join(os.path.dirname(__file__), 'status.json')

@app.route('/')
def index():
    # Servir o dashboard HTML criado
    return send_from_directory('.', 'dashboard.html')

@app.route('/status')
def status():
    # Servir o status.json para o dashboard consumir via AJAX
    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    else:
        return jsonify({'error': 'status.json não encontrado'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
