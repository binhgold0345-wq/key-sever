# app.py - TBTOOL Key Server
# Hỗ trợ Key FREE, Key VIP và Key Vĩnh Viễn (FOREVER)

from flask import Flask, request, jsonify
import hashlib
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# File lưu trữ key
KEYS_FILE = "keys.json"
USED_KEYS_FILE = "used_keys.json"

# Định nghĩa thời gian theo loại key
VIP_DURATIONS = {
    "1D": 24,
    "3D": 72,
    "7D": 168,
    "15D": 360,
    "30D": 720,
    "6M": 4320,
    "1Y": 8760,
    "FOREVER": 87600  # 10 năm (coi như vĩnh viễn)
}

def load_keys():
    """Tải danh sách key VIP từ file keys.json"""
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # Key VIP mặc định
    default_keys = {
        "TBTOOL_VIP_1D_001": {"type": "1D", "description": "Key VIP 1 ngày"},
        "TBTOOL_VIP_7D_001": {"type": "7D", "description": "Key VIP 7 ngày"},
        "TBTOOL_VIP_30D_001": {"type": "30D", "description": "Key VIP 30 ngày"},
        "TBTOOL_VIP_6M_001": {"type": "6M", "description": "Key VIP 6 tháng"},
        "TBTOOL_VIP_1Y_001": {"type": "1Y", "description": "Key VIP 1 năm"},
        "TBTOOL_VIP_FOREVER_001": {"type": "FOREVER", "description": "Key VIP Vĩnh Viễn"},
    }
    save_keys(default_keys)
    return default_keys

def save_keys(keys):
    """Lưu danh sách key VIP vào file"""
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
    used_keys = load_used_keys()
    return jsonify({
        "status": "online",
        "message": "TBTOOL Key Server is running",
        "version": "2.0",
        "total_vip_keys": len(keys),
        "total_used": len(used_keys),
        "endpoints": {
            "/api/verify_vip_key": "POST - Verify VIP key",
            "/api/list_keys": "GET - List used keys",
            "/api/check_activation": "POST - Check activation status",
            "/api/add_vip_key": "POST - Add VIP key (admin)"
        }
    })

@app.route('/api/verify_vip_key', methods=['POST'])
def verify_vip_key():
    """Xác thực KEY VIP - chỉ lưu trong keys.json"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        key = data.get('key')
        
        if not device_id or not key:
            return jsonify({
                "success": False,
                "message": "Missing device_id or key"
            }), 400
        
        # Load danh sách key VIP
        vip_keys = load_keys()
        
        # Kiểm tra key VIP có tồn tại không
        if key not in vip_keys:
            return jsonify({
                "success": False,
                "message": "Key VIP không hợp lệ"
            }), 404
        
        # Kiểm tra key đã được sử dụng chưa
        used_keys = load_used_keys()
        key_hash = hashlib.sha256(f"{device_id}:{key}".encode()).hexdigest()
        
        if key_hash in used_keys:
            # Kiểm tra device_id có khớp không
            record = used_keys[key_hash]
            if record.get("device_id") != device_id:
                return jsonify({
                    "success": False,
                    "message": "Key VIP đã được sử dụng trên thiết bị khác"
                }), 403
            return jsonify({
                "success": False,
                "message": "Key VIP đã được sử dụng"
            }), 409
        
        # Lấy thông tin key VIP
        key_info = vip_keys[key]
        key_type = key_info.get("type", "1D")
        duration = VIP_DURATIONS.get(key_type, 24)
        
        # Đánh dấu key đã sử dụng
        used_keys[key_hash] = {
            "device_id": device_id,
            "key": key,
            "key_type": key_type,
            "used_at": datetime.now().isoformat(),
            "duration": duration
        }
        save_used_keys(used_keys)
        
        # Hiển thị thông báo phù hợp
        if key_type == "FOREVER":
            time_text = "VĨNH VIỄN (10 năm)"
        elif duration >= 720:
            time_text = f"{duration/24:.0f} ngày"
        elif duration >= 168:
            time_text = f"{duration/24:.0f} ngày"
        elif duration >= 72:
            time_text = f"{duration/24:.0f} ngày"
        else:
            time_text = f"{duration} giờ"
        
        return jsonify({
            "success": True,
            "duration": duration,
            "key_type": key_type,
            "is_vip": True,
            "is_forever": key_type == "FOREVER",
            "server_time": datetime.now().isoformat(),
            "message": f"Key VIP hợp lệ, hoạt động {time_text}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi server: {str(e)}"
        }), 500

@app.route('/api/check_activation', methods=['POST'])
def check_activation():
    """Kiểm tra trạng thái activation của key"""
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
                "duration": record.get("duration", 24),
                "used_at": record.get("used_at"),
                "key_type": record.get("key_type", "VIP"),
                "is_vip": True,
                "is_forever": record.get("key_type") == "FOREVER",
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

@app.route('/api/list_keys', methods=['GET'])
def list_keys():
    """Liệt kê key đã sử dụng (đồng bộ cho tool)"""
    used_keys = load_used_keys()
    return jsonify({
        "success": True,
        "total_used": len(used_keys),
        "used_keys": list(used_keys.keys())
    })

@app.route('/api/add_vip_key', methods=['POST'])
def add_vip_key():
    """Thêm key VIP mới (chỉ admin)"""
    try:
        data = request.get_json()
        admin_key = data.get('admin_key')
        
        if admin_key != "TBTOOL_ADMIN_2026":
            return jsonify({
                "success": False,
                "message": "Unauthorized"
            }), 401
        
        new_key = data.get('key')
        key_type = data.get('type', '1D')
        description = data.get('description', '')
        
        if not new_key:
            return jsonify({
                "success": False,
                "message": "Missing key"
            }), 400
        
        # Kiểm tra loại key VIP hợp lệ
        if key_type not in VIP_DURATIONS:
            return jsonify({
                "success": False,
                "message": f"Loại key VIP không hợp lệ. Hỗ trợ: {', '.join(VIP_DURATIONS.keys())}"
            }), 400
        
        vip_keys = load_keys()
        
        if new_key in vip_keys:
            return jsonify({
                "success": False,
                "message": "Key VIP đã tồn tại"
            }), 409
        
        vip_keys[new_key] = {
            "type": key_type,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        save_keys(vip_keys)
        
        return jsonify({
            "success": True,
            "message": f"Đã thêm key VIP: {new_key}",
            "key": new_key,
            "type": key_type,
            "duration": VIP_DURATIONS.get(key_type, 24)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi: {str(e)}"
        }), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """Thống kê server"""
    vip_keys = load_keys()
    used_keys = load_used_keys()
    
    # Đếm số key VIP theo loại
    type_counts = {}
    forever_count = 0
    for key, info in vip_keys.items():
        key_type = info.get("type", "UNKNOWN")
        type_counts[key_type] = type_counts.get(key_type, 0) + 1
        if key_type == "FOREVER":
            forever_count += 1
    
    return jsonify({
        "total_vip_keys": len(vip_keys),
        "total_used": len(used_keys),
        "vip_key_types": type_counts,
        "forever_keys": forever_count,
        "vip_keys": list(vip_keys.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
