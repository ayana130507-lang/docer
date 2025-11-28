from flask import Flask, jsonify, render_template, request, abort
import threading

app = Flask(__name__, static_folder='static', template_folder='templates')

# Simple in-memory store for demo purposes
_lock = threading.Lock()
_items = []
_next_id = 1


@app.route('/')
def index_json():
    return jsonify(status="ok", message="Приложение успешно работает!")


@app.route('/ui')
def ui():
    return render_template('index.html')


@app.route('/items', methods=['GET'])
def list_items():
    return jsonify(items=_items)


@app.route('/items', methods=['POST'])
def create_item():
    global _next_id
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    if not name:
        return jsonify(error='name is required'), 400
    with _lock:
        item = {'id': _next_id, 'name': name, 'description': description}
        _items.append(item)
        _next_id += 1
    return jsonify(item), 201


@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.get_json() or {}
    name = data.get('name')
    description = data.get('description')
    with _lock:
        for it in _items:
            if it['id'] == item_id:
                if name is not None:
                    it['name'] = name
                if description is not None:
                    it['description'] = description
                return jsonify(it)
    return jsonify(error='not found'), 404


@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    with _lock:
        for i, it in enumerate(_items):
            if it['id'] == item_id:
                _items.pop(i)
                return jsonify(status='deleted')
    return jsonify(error='not found'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
