from flask import Flask, request, jsonify
import hashlib
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# File lưu trữ key
KEYS_FILE = "keys.json"
USED_KEYS_FILE = "used_keys.json"

# Danh sách key VIP (có thể lưu trong file)
VIP_KEYS = {
    "TBTOOL_VIP_7D_ABC123": {"duration": 168},
    "TBTOOL_VIP_7D_XYZ789": {"duration": 168},
    "TBTOOL_VIP_30D_DEF456": {"duration": 720},
    "TBTOOL_VIP_90D_GHI789": {"duration": 2160},
    "TBTOOL_VIP_365D_JKL012": {"duration": 8760},
}

def load_used_keys():
    if os.path.exists(USED_KEYS_FILE):
        try:
            with open(USED_KEYS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_used_keys(used_keys):
    with open(USED_KEYS_FILE, 'w') as f:
        json.dump(used_keys, f)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "TBTOOL Key Server is running",
        "version": "1.0",
        "endpoints": {
            "/api/verify_key": "POST - Verify VIP key",
            "/api/list_keys": "GET - List all keys",
            "/api/check_activation": "POST - Check activation status"
        }
    })

@app.route('/api/verify_key', methods=['POST'])
def verify_key():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        key = data.get('key')
        action = data.get('action', 'verify')
        
        if not device_id or not key:
            return jsonify({
                "success": False,
                "message": "Missing device_id or key"
            }), 400
        
        # Kiểm tra key có tồn tại không
        if key not in VIP_KEYS:
            return jsonify({
                "success": False,
                "message": "Key không hợp lệ"
            }), 404
        
        # Kiểm tra key đã được sử dụng chưa
        used_keys = load_used_keys()
        key_hash = hashlib.sha256(f"{device_id}:{key}".encode()).hexdigest()
        
        if key_hash in used_keys:
            return jsonify({
                "success": False,
                "message": "Key đã được sử dụng"
            }), 409
        
        # Lấy duration
        duration = VIP_KEYS[key].get("duration", 168)
        
        # Đánh dấu key đã sử dụng
        used_keys[key_hash] = {
            "device_id": device_id,
            "key": key,
            "used_at": datetime.now().isoformat(),
            "duration": duration
        }
        save_used_keys(used_keys)
        
        return jsonify({
            "success": True,
            "duration": duration,
            "message": f"Key hợp lệ, hoạt động {duration} giờ"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi server: {str(e)}"
        }), 500

@app.route('/api/check_activation', methods=['POST'])
def check_activation():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        key = data.get('key')
        
        if not device_id or not key:
            return jsonify({
                "active": False,
                "message": "Missing device_id or key"
            }), 400
        
        used_keys = load_used_keys()
        key_hash = hashlib.sha256(f"{device_id}:{key}".encode()).hexdigest()
        
        if key_hash in used_keys:
            record = used_keys[key_hash]
            return jsonify({
                "active": True,
                "duration": record.get("duration", 168),
                "used_at": record.get("used_at"),
                "message": "Key đã được kích hoạt"
            })
        else:
            return jsonify({
                "active": False,
                "message": "Key chưa được kích hoạt"
            })
            
    except Exception as e:
        return jsonify({
            "active": False,
            "message": f"Lỗi: {str(e)}"
        }), 500

@app.route('/api/list_keys', methods=['GET'])
def list_keys():
    # Chỉ hiện key đã được sử dụng (không hiện key gốc)
    used_keys = load_used_keys()
    return jsonify({
        "total_used": len(used_keys),
        "used_keys": list(used_keys.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
