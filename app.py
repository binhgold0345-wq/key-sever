# app.py - TBTOOL Key Server (FULL - Thêm FREE key)
# Hỗ trợ: VIP + FREE (tạo link, kích hoạt, check hạn, cancel)

from flask import Flask, request, jsonify
import hashlib
import json
import secrets
from datetime import datetime, timedelta
import os

app = Flask(__name__)

KEYS_FILE = "keys.json"
DEVICES_FILE = "devices.json"
FREE_KEYS_FILE = "free_keys.json"   # Lưu key FREE đang chờ/đã kích hoạt

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

# ==================== HÀM LOAD/SAVE ====================
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_keys():
    return load_json(KEYS_FILE, {})

def save_keys(keys):
    save_json(KEYS_FILE, keys)

def load_devices():
    return load_json(DEVICES_FILE, {})

def save_devices(devices):
    save_json(DEVICES_FILE, devices)

def load_free_keys():
    return load_json(FREE_KEYS_FILE, {})

def save_free_keys(free_keys):
    save_json(FREE_KEYS_FILE, free_keys)

# ==================== HỖ TRỢ ====================
def gen_free_key(length=8):
    return secrets.token_hex(length // 2).upper()

# ==================== HOME ====================
@app.route('/', methods=['GET'])
def home():
    keys = load_keys()
    devices = load_devices()
    free_keys = load_free_keys()
    return jsonify({
        "status": "online",
        "message": "TBTOOL Key Server is running",
        "version": "3.1",
        "total_vip_keys": len(keys),
        "total_devices": len(devices),
        "total_free_pending": len([k for k in free_keys.values() if not k.get('activated')]),
        "total_free_active": len([k for k in free_keys.values() if k.get('activated')]),
        "endpoints": {
            "VIP": {
                "/api/verify_key": "POST - Verify key & bind device",
                "/api/add_key": "POST - Add VIP key (admin)",
                "/api/delete_key": "POST - Delete VIP key (admin)"
            },
            "FREE": {
                "/api/free/create": "POST - Tạo link FREE, trả về key",
                "/api/free/activate": "POST - Kích hoạt key FREE",
                "/api/free/check": "GET - Kiểm tra hạn FREE theo device_id",
                "/api/free/cancel": "POST - Hủy key FREE chưa kích hoạt"
            },
            "Common": {
                "/api/check_device": "GET - Check device by device_id",
                "/api/list_devices": "GET - List all devices",
                "/api/used_keys": "GET - List used keys",
                "/api/reset_device": "POST - Reset device (admin)"
            }
        }
    })

# ==================== VIP ====================
@app.route('/api/verify_key', methods=['POST'])
def verify_key():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        key = data.get('key')

        if not device_id or not key:
            return jsonify({"success": False, "message": "Missing device_id or key"}), 400

        vip_keys = load_keys()
        devices = load_devices()

        if key not in vip_keys:
            return jsonify({"success": False, "message": "Key không hợp lệ"}), 404

        for dev_id, dev_info in devices.items():
            if dev_info.get("key") == key:
                if dev_id != device_id:
                    return jsonify({
                        "success": False,
                        "message": "Key đã được kích hoạt bởi thiết bị khác!",
                        "used_by": dev_id
                    }), 403

        if device_id in devices:
            existing_key = devices[device_id].get("key")
            if existing_key == key:
                key_info = vip_keys[key]
                key_type = key_info.get("type", "1D")
                duration = VIP_DURATIONS.get(key_type, 24)
                time_text = "VĨNH VIỄN" if key_type == "FOREVER" else (f"{duration/24:.0f} ngày" if duration >= 720 else f"{duration} giờ")
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
                return jsonify({
                    "success": False,
                    "message": "Thiết bị này đã kích hoạt key khác!",
                    "current_key": existing_key
                }), 409

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

        time_text = "VĨNH VIỄN" if key_type == "FOREVER" else (f"{duration/24:.0f} ngày" if duration >= 720 else f"{duration} giờ")
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
        return jsonify({"success": False, "message": f"Lỗi server: {str(e)}"}), 500

@app.route('/api/add_key', methods=['POST'])
def add_key():
    try:
        data = request.get_json()
        if data.get('admin_key') != "TBTOOL_ADMIN_2026":
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        new_key = data.get('key')
        key_type = data.get('type', '1D')
        description = data.get('description', '')

        if not new_key:
            return jsonify({"success": False, "message": "Missing key"}), 400
        if key_type not in VIP_DURATIONS:
            return jsonify({"success": False, "message": f"Loại key không hợp lệ. Hỗ trợ: {', '.join(VIP_DURATIONS.keys())}"}), 400

        vip_keys = load_keys()
        if new_key in vip_keys:
            return jsonify({"success": False, "message": "Key VIP đã tồn tại"}), 409

        vip_keys[new_key] = {"type": key_type, "description": description, "created_at": datetime.now().isoformat()}
        save_keys(vip_keys)
        return jsonify({"success": True, "message": f"Đã thêm key VIP: {new_key}", "key": new_key, "type": key_type, "duration": VIP_DURATIONS.get(key_type, 24)})

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

@app.route('/api/delete_key', methods=['POST'])
def delete_key():
    try:
        data = request.get_json()
        if data.get('admin_key') != "TBTOOL_ADMIN_2026":
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

# ==================== FREE KEY ====================
@app.route('/api/free/create', methods=['POST'])
def free_create():
    """Tạo link FREE, trả về key (pending)"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')

        if not device_id:
            return jsonify({"success": False, "message": "Missing device_id"}), 400

        free_keys = load_free_keys()

        # Nếu device đã có free key active → không tạo mới
        for k, v in free_keys.items():
            if v.get('device_id') == device_id and v.get('activated'):
                remaining = (datetime.fromisoformat(v['expiry']) - datetime.now()).total_seconds() / 3600
                if remaining > 0:
                    return jsonify({
                        "success": True,
                        "message": f"Device đã có key FREE active, còn {remaining:.1f} giờ",
                        "key": k,
                        "link": f"https://webkeytbtool.blogspot.com/?device={device_id}&key={k}"
                    })

        # Tạo key mới
        key = gen_free_key(8)
        while key in free_keys:
            key = gen_free_key(8)

        free_keys[key] = {
            "device_id": device_id,
            "activated": False,
            "created_at": datetime.now().isoformat(),
            "expiry": None
        }
        save_free_keys(free_keys)

        return jsonify({
            "success": True,
            "key": key,
            "link": f"https://webkeytbtool.blogspot.com/?device={device_id}&key={key}"
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

@app.route('/api/free/activate', methods=['POST'])
def free_activate():
    """Kích hoạt key FREE, bắt đầu đếm 24h"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        key = data.get('key')

        if not device_id or not key:
            return jsonify({"success": False, "message": "Missing device_id or key"}), 400

        free_keys = load_free_keys()

        if key not in free_keys:
            return jsonify({"success": False, "message": "Key FREE không tồn tại"}), 404

        entry = free_keys[key]
        if entry.get('device_id') != device_id:
            return jsonify({"success": False, "message": "Device ID không khớp với key"}), 403

        if entry.get('activated'):
            return jsonify({"success": False, "message": "Key FREE đã được kích hoạt trước đó"}), 409

        # Kích hoạt: 24h
        now = datetime.now()
        expiry = now + timedelta(hours=24)
        free_keys[key]['activated'] = True
        free_keys[key]['activated_at'] = now.isoformat()
        free_keys[key]['expiry'] = expiry.isoformat()
        save_free_keys(free_keys)

        return jsonify({
            "success": True,
            "message": "Kích hoạt FREE thành công, hết hạn sau 24h",
            "expiry": expiry.isoformat()
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

@app.route('/api/free/check', methods=['GET'])
def free_check():
    """Kiểm tra trạng thái FREE của device"""
    try:
        device_id = request.args.get('device_id')
        if not device_id:
            return jsonify({"success": False, "message": "Missing device_id"}), 400

        free_keys = load_free_keys()
        for key, entry in free_keys.items():
            if entry.get('device_id') == device_id:
                if not entry.get('activated'):
                    return jsonify({"success": False, "message": "Key chưa kích hoạt", "key": key})

                expiry = datetime.fromisoformat(entry['expiry'])
                now = datetime.now()
                if now > expiry:
                    # Hết hạn -> xóa entry
                    del free_keys[key]
                    save_free_keys(free_keys)
                    return jsonify({"success": False, "message": "Key FREE đã hết hạn"})

                remaining_hours = (expiry - now).total_seconds() / 3600
                return jsonify({
                    "success": True,
                    "key": key,
                    "expiry": entry['expiry'],
                    "remaining_hours": round(remaining_hours, 1),
                    "status": "active"
                })

        return jsonify({"success": False, "message": "Device chưa có key FREE"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

@app.route('/api/free/cancel', methods=['POST'])
def free_cancel():
    """Hủy key FREE chưa kích hoạt (khi user tắt tool)"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        if not device_id:
            return jsonify({"success": False, "message": "Missing device_id"}), 400

        free_keys = load_free_keys()
        to_delete = []
        for key, entry in free_keys.items():
            if entry.get('device_id') == device_id and not entry.get('activated'):
                to_delete.append(key)

        if not to_delete:
            return jsonify({"success": False, "message": "Không có key FREE pending nào để hủy"})

        for k in to_delete:
            del free_keys[k]
        save_free_keys(free_keys)

        return jsonify({"success": True, "message": f"Đã hủy {len(to_delete)} key FREE pending"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500

# ==================== COMMON ====================
@app.route('/api/check_device', methods=['GET'])
def check_device():
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({"success": False, "message": "Missing device_id"}), 400

    devices = load_devices()
    if device_id in devices:
        dev_info = devices[device_id]
        return jsonify({
            "success": True,
            "device_id": device_id,
            "key": dev_info.get("key"),
            "key_type": dev_info.get("key_type", "VIP"),
            "duration": dev_info.get("duration", 24),
            "is_forever": dev_info.get("key_type") == "FOREVER",
            "activated_at": dev_info.get("activated_at")
        })
    else:
        return jsonify({"success": False, "message": "Device chưa kích hoạt"}), 404

@app.route('/api/list_devices', methods=['GET'])
def list_devices():
    devices = load_devices()
    return jsonify({"success": True, "total": len(devices), "devices": devices})

@app.route('/api/used_keys', methods=['GET'])
def used_keys():
    devices = load_devices()
    used = list(set([info.get("key") for info in devices.values()]))
    return jsonify({"success": True, "total": len(used), "used_keys": used})

@app.route('/api/reset_device', methods=['POST'])
def reset_device():
    try:
        data = request.get_json()
        if data.get('admin_key') != "TBTOOL_ADMIN_2026":
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

# ==================== RUN ====================
if __name__ == '__main__':
    if not os.path.exists(DEVICES_FILE):
        save_devices({})
    if not os.path.exists(KEYS_FILE):
        save_keys({})
    if not os.path.exists(FREE_KEYS_FILE):
        save_free_keys({})
    app.run(host='0.0.0.0', port=10000)
