# app.py - TBTOOL Key Server
# Hỗ trợ Key VIP, check key và lưu device, chặn device khác dùng lại key

from flask import Flask, request, jsonify
import hashlib
import json
from datetime import datetime
import os

app = Flask(__name__)

KEYS_FILE = "keys.json"
DEVICES_FILE = "devices.json"

VIP_DURATIONS = {
    "1D": 24,
    "3D": 72,
    "7D": 168,
    "15D": 360,
    "30D": 720,
    "6M": 4320,
    "1Y": 8760,
    "FOREVER": 87600
}

def load_keys():
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
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
    with open(KEYS_FILE, 'w', encoding='utf-8') as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

def load_devices():
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_devices(devices):
    with open(DEVICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(devices, f, indent=2, ensure_ascii=False)

@app.route('/', methods=['GET'])
def home():
    keys = load_keys()
    devices = load_devices()
    return jsonify({
        "status": "online",
        "message": "TBTOOL Key Server is running",
        "version": "3.0",
        "total_vip_keys": len(keys),
        "total_devices": len(devices),
        "endpoints": {
            "/api/verify_key": "POST - Verify key & bind device",
            "/api/check_device": "GET - Check device by device_id",
            "/api/list_devices": "GET - List all devices",
            "/api/used_keys": "GET - List used keys",
            "/api/add_key": "POST - Add VIP key (admin)",
            "/api/delete_key": "POST - Delete VIP key (admin)"
        }
    })

@app.route('/api/verify_key', methods=['POST'])
def verify_key():
    """
    Xác thực key, lưu device_id, chặn device khác dùng key đã kích hoạt
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        key = data.get('key')

        if not device_id or not key:
            return jsonify({
                "success": False,
                "message": "Missing device_id or key"
            }), 400

        vip_keys = load_keys()
        devices = load_devices()

        # 1. Check key có tồn tại trong VIP keys không
        if key not in vip_keys:
            return jsonify({
                "success": False,
                "message": "Key không hợp lệ"
            }), 404

        # 2. Check key đã bị device KHÁC dùng chưa
        for dev_id, dev_info in devices.items():
            if dev_info.get("key") == key:
                if dev_id != device_id:
                    return jsonify({
                        "success": False,
                        "message": "Key đã được kích hoạt bởi thiết bị khác!",
                        "used_by": dev_id
                    }), 403

        # 3. Check device này đã kích hoạt key NÀO chưa
        if device_id in devices:
            existing_key = devices[device_id].get("key")
            # Nếu device đã kích hoạt key này rồi thì trả về thành công luôn
            if existing_key == key:
                key_info = vip_keys[key]
                key_type = key_info.get("type", "1D")
                duration = VIP_DURATIONS.get(key_type, 24)
                if key_type == "FOREVER":
                    time_text = "VĨNH VIỄN"
                elif duration >= 720:
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
                    "message": f"Key VIP đã kích hoạt trước đó, hoạt động {time_text}"
                })
            else:
                # Device này đã dùng key khác, nhưng muốn dùng key mới -> không cho
                return jsonify({
                    "success": False,
                    "message": "Thiết bị này đã kích hoạt key khác!",
                    "current_key": existing_key
                }), 409

        # 4. Kích hoạt mới: Lưu device + key
        key_info = vip_keys[key]
        key_type = key_info.get("type", "1D")
        duration = VIP_DURATIONS.get(key_type, 24)

        devices[device_id] = {
            "key": key,
            "key_type": key_type,
            "activated_at": datetime.now().isoformat(),
            "duration": duration
        }
        save_devices(devices)

        if key_type == "FOREVER":
            time_text = "VĨNH VIỄN"
        elif duration >= 720:
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
            "message": f"Kích hoạt thành công! Key VIP hoạt động {time_text}"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi server: {str(e)}"
        }), 500

@app.route('/api/check_device', methods=['GET'])
def check_device():
    """Kiểm tra trạng thái device"""
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({"success": False, "message": "Missing device_id"}), 400

    devices = load_devices()
    if device_id in devices:
        dev_info = devices[device_id]
        key_type = dev_info.get("key_type", "VIP")
        duration = dev_info.get("duration", 24)
        return jsonify({
            "success": True,
            "device_id": device_id,
            "key": dev_info.get("key"),
            "key_type": key_type,
            "duration": duration,
            "is_forever": key_type == "FOREVER",
            "activated_at": dev_info.get("activated_at")
        })
    else:
        return jsonify({
            "success": False,
            "message": "Device chưa kích hoạt"
        }), 404

@app.route('/api/list_devices', methods=['GET'])
def list_devices():
    """Liệt kê tất cả device đã kích hoạt"""
    devices = load_devices()
    return jsonify({
        "success": True,
        "total": len(devices),
        "devices": devices
    })

@app.route('/api/used_keys', methods=['GET'])
def used_keys():
    """Liệt kê key đã được sử dụng"""
    devices = load_devices()
    used = list(set([info.get("key") for info in devices.values()]))
    return jsonify({
        "success": True,
        "total": len(used),
        "used_keys": used
    })

@app.route('/api/add_key', methods=['POST'])
def add_key():
    """Thêm key VIP mới (admin)"""
    try:
        data = request.get_json()
        admin_key = data.get('admin_key')

        if admin_key != "TBTOOL_ADMIN_2026":
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        new_key = data.get('key')
        key_type = data.get('type', '1D')
        description = data.get('description', '')

        if not new_key:
            return jsonify({"success": False, "message": "Missing key"}), 400

        if key_type not in VIP_DURATIONS:
            return jsonify({
                "success": False,
                "message": f"Loại key không hợp lệ. Hỗ trợ: {', '.join(VIP_DURATIONS.keys())}"
            }), 400

        vip_keys = load_keys()
        if new_key in vip_keys:
            return jsonify({"success": False, "message": "Key VIP đã tồn tại"}), 409

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
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

@app.route('/api/delete_key', methods=['POST'])
def delete_key():
    """Xóa key VIP (admin)"""
    try:
        data = request.get_json()
        admin_key = data.get('admin_key')

        if admin_key != "TBTOOL_ADMIN_2026":
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        key_to_delete = data.get('key')
        if not key_to_delete:
            return jsonify({"success": False, "message": "Missing key"}), 400

        vip_keys = load_keys()
        if key_to_delete not in vip_keys:
            return jsonify({"success": False, "message": "Key VIP không tồn tại"}), 404

        del vip_keys[key_to_delete]
        save_keys(vip_keys)

        return jsonify({"success": True, "message": f"Đã xóa key VIP: {key_to_delete}"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

@app.route('/api/reset_device', methods=['POST'])
def reset_device():
    """Reset device (gỡ key khỏi device) - admin"""
    try:
        data = request.get_json()
        admin_key = data.get('admin_key')

        if admin_key != "TBTOOL_ADMIN_2026":
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        device_id = data.get('device_id')
        if not device_id:
            return jsonify({"success": False, "message": "Missing device_id"}), 400

        devices = load_devices()
        if device_id in devices:
            del devices[device_id]
            save_devices(devices)
            return jsonify({"success": True, "message": f"Đã reset device: {device_id}"})
        else:
            return jsonify({"success": False, "message": "Device không tồn tại"}), 404

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

if __name__ == '__main__':
    if not os.path.exists(DEVICES_FILE):
        save_devices({})
    if not os.path.exists(KEYS_FILE):
        load_keys()
    app.run(host='0.0.0.0', port=10000)
