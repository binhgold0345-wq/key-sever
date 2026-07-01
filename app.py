from flask import Flask, request, jsonify
import hashlib
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# File lưu trữ key
KEYS_FILE = "keys.json"
USED_KEYS_FILE = "used_keys.json"

def load_keys():
    """Tải danh sách key từ file keys.json"""
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # Nếu không có file, tạo mới với key mẫu
    default_keys = {
        "TBTOOL_VIP_7D_ABC123": {"duration": 168, "type": "VIP", "description": "Key VIP 7 ngày"},
        "TBTOOL_VIP_30D_DEF456": {"duration": 720, "type": "VIP", "description": "Key VIP 30 ngày"},
        "TBTOOL_VIP_90D_GHI789": {"duration": 2160, "type": "VIP", "description": "Key VIP 90 ngày"},
        "TBTOOL_VIP_365D_JKL012": {"duration": 8760, "type": "VIP", "description": "Key VIP 365 ngày"},
    }
    save_keys(default_keys)
    return default_keys

def save_keys(keys):
    """Lưu danh sách key vào file"""
    with open(KEYS_FILE, 'w', encoding='utf-8') as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

def load_used_keys():
    """Tải danh sách key đã sử dụng"""
    if os.path.exists(USED_KEYS_FILE):
        try:
            with open(USED_KEYS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_used_keys(used_keys):
    """Lưu danh sách key đã sử dụng"""
    with open(USED_KEYS_FILE, 'w', encoding='utf-8') as f:
        json.dump(used_keys, f, indent=2, ensure_ascii=False)

@app.route('/', methods=['GET'])
def home():
    keys = load_keys()
    return jsonify({
        "status": "online",
        "message": "TBTOOL Key Server is running",
        "version": "1.0",
        "total_keys": len(keys),
        "endpoints": {
            "/api/verify_key": "POST - Verify VIP key",
            "/api/list_keys": "GET - List all keys (hidden)",
            "/api/check_activation": "POST - Check activation status",
            "/api/add_key": "POST - Add new key (admin)"
        }
    })

@app.route('/api/verify_key', methods=['POST'])
def verify_key():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        key = data.get('key')
        
        if not device_id or not key:
            return jsonify({
                "success": False,
                "message": "Missing device_id or key"
            }), 400
        
        # Load danh sách key
        keys = load_keys()
        
        # Kiểm tra key có tồn tại không
        if key not in keys:
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
        duration = keys[key].get("duration", 168)
        
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
                "message": "Key chưa được kích hoạt hoặc không tồn tại"
            })
            
    except Exception as e:
        return jsonify({
            "active": False,
            "message": f"Lỗi: {str(e)}"
        }), 500

@app.route('/api/add_key', methods=['POST'])
def add_key():
    """Thêm key mới (chỉ admin)"""
    try:
        data = request.get_json()
        admin_key = data.get('admin_key')
        
        # Kiểm tra admin key (có thể đặt mật khẩu cố định)
        if admin_key != "TBTOOL_ADMIN_2026":
            return jsonify({
                "success": False,
                "message": "Unauthorized"
            }), 401
        
        new_key = data.get('new_key')
        duration = data.get('duration', 168)
        description = data.get('description', '')
        
        if not new_key:
            return jsonify({
                "success": False,
                "message": "Missing new_key"
            }), 400
        
        keys = load_keys()
        
        if new_key in keys:
            return jsonify({
                "success": False,
                "message": "Key đã tồn tại"
            }), 409
        
        keys[new_key] = {
            "duration": duration,
            "type": "VIP",
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        save_keys(keys)
        
        return jsonify({
            "success": True,
            "message": f"Đã thêm key: {new_key}",
            "key": new_key
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi: {str(e)}"
        }), 500

@app.route('/api/list_keys', methods=['GET'])
def list_keys():
    """Liệt kê key đã sử dụng (không hiện key gốc)"""
    used_keys = load_used_keys()
    return jsonify({
        "total_used": len(used_keys),
        "used_keys": list(used_keys.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
