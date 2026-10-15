import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from datetime import datetime, timezone

from conectar import crear_conexion
from dao.dao import Dao
from dao.user_dao import UserDao
from dao.vehicle_dao import VehicleDao
from dao.gps_device_dao import GpsDeviceDao
from dao.telemetry_dao import TelemetryDao
from dao.command_dao import CutEngineCommandDao
from dao.alert_dao import AlertDao

from model.enums import PlanSubscription, HardwareLevel, CommandStatus
from model.user import User
from model.vehicle import Vehicle
from model.gps_device import GpsDevice
from model.telemetry_log import TelemetryLog
from model.cut_engine_command import CutEngineCommand

from model.alert import Alert, AlertType, AlertStatus

from api.auth import generate_token, require_auth, decode_token
from api.ws import socketio, broadcast_telemetry
import jwt as jwt_lib

app = Flask(__name__)
socketio.init_app(app, cors_allowed_origins="*")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pluma_gps.db")


def get_conn():
    conn = crear_conexion(DB_PATH)
    Dao(conn).crear_todas_las_tablas()
    return conn


def get_daos(conn):
    return {
        "user": UserDao(conn),
        "vehicle": VehicleDao(conn),
        "gps": GpsDeviceDao(conn),
        "telemetry": TelemetryDao(conn),
        "command": CutEngineCommandDao(conn),
        "alert": AlertDao(conn),
    }


# ==================== AUTH ====================

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json()
    try:
        user = User(
            rut=data["rut"],
            full_name=data["full_name"],
            email=data["email"],
            plan=PlanSubscription(data.get("plan", "FREE_ADS")),
        )
        user.set_password(data["password"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        return jsonify({"error": f"Falta campo: {e}"}), 400

    conn = get_conn()
    daos = get_daos(conn)
    try:
        daos["user"].insertar(user)
        token = generate_token(user.user_id, user.rut, user.plan.value)
        conn.close()
        return jsonify({
            "user_id": user.user_id,
            "rut": user.rut,
            "token": token,
        }), 201
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json()
    rut = data.get("rut")
    password = data.get("password")
    if not rut or not password:
        return jsonify({"error": "rut y password son obligatorios"}), 400

    conn = get_conn()
    daos = get_daos(conn)
    row = daos["user"].buscar_por_rut(rut)
    conn.close()

    if not row:
        return jsonify({"error": "Credenciales inválidas"}), 401

    user = User(
        rut=row[1], full_name=row[2], email=row[3],
        plan=PlanSubscription(row[4]), user_id=row[0],
        is_active=bool(row[5]), password_hash=row[6],
    )
    if not user.verify_password(password):
        return jsonify({"error": "Credenciales inválidas"}), 401

    token = generate_token(user.user_id, user.rut, user.plan.value)
    return jsonify({
        "user_id": user.user_id,
        "rut": user.rut,
        "plan": user.plan.value,
        "token": token,
    })


# ==================== USERS ====================

@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json()
    try:
        user = User(
            rut=data["rut"],
            full_name=data["full_name"],
            email=data["email"],
            plan=PlanSubscription(data.get("plan", "FREE_ADS")),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        return jsonify({"error": f"Falta campo: {e}"}), 400

    conn = get_conn()
    daos = get_daos(conn)
    try:
        daos["user"].insertar(user)
        conn.close()
        return jsonify({"user_id": user.user_id, "rut": user.rut}), 201
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/users", methods=["GET"])
def list_users():
    conn = get_conn()
    daos = get_daos(conn)
    rows = daos["user"].listar()
    conn.close()
    return jsonify([
        {"user_id": r[0], "rut": r[1], "full_name": r[2],
         "email": r[3], "subscription_plan": r[4], "is_active": bool(r[5])}
        for r in rows
    ])


@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_conn()
    daos = get_daos(conn)
    row = daos["user"].buscar_por_id(user_id)
    conn.close()
    if not row:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify({
        "user_id": row[0], "rut": row[1], "full_name": row[2],
        "email": row[3], "subscription_plan": row[4], "is_active": bool(row[5])
    })


# ==================== VEHICLES ====================

@app.route("/api/users/<user_id>/vehicles", methods=["POST"])
@require_auth
def create_vehicle(user_id):
    data = request.get_json()
    conn = get_conn()
    daos = get_daos(conn)

    user_row = daos["user"].buscar_por_id(user_id)
    if not user_row:
        conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    plan = PlanSubscription(user_row[4])
    count = daos["vehicle"].contar_por_usuario(user_id)

    try:
        plan_val = PlanSubscription(user_row[4])
        if plan_val.max_vehicles != -1 and count >= plan_val.max_vehicles:
            conn.close()
            return jsonify({
                "error": f"Plan {plan_val.value} permite máximo {plan_val.max_vehicles} vehículo(s). "
                         f"Actualmente tiene {count}."
            }), 400
    except Exception:
        pass

    try:
        veh = Vehicle(
            user_id=user_id,
            license_plate=data["license_plate"],
            brand=data.get("brand", ""),
            model=data.get("model", ""),
            manufacture_year=data.get("manufacture_year", 0),
            engine_type=data.get("engine_type", ""),
        )
    except ValueError as e:
        conn.close()
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        conn.close()
        return jsonify({"error": f"Falta campo: {e}"}), 400

    try:
        daos["vehicle"].insertar(veh)
        conn.close()
        return jsonify({"vehicle_id": veh.vehicle_id, "license_plate": veh.license_plate}), 201
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/vehicles", methods=["GET"])
@require_auth
def list_vehicles():
    user_id = request.args.get("user_id")
    conn = get_conn()
    daos = get_daos(conn)
    if user_id:
        rows = [r for r in daos["vehicle"].listar() if r[1] == user_id]
    else:
        rows = daos["vehicle"].listar()
    conn.close()
    return jsonify([
        {"vehicle_id": r[0], "user_id": r[1], "license_plate": r[2],
         "brand": r[3], "model": r[4], "manufacture_year": r[5], "engine_type": r[6]}
        for r in rows
    ])


@app.route("/api/vehicles/<vehicle_id>", methods=["GET"])
@require_auth
def get_vehicle(vehicle_id):
    conn = get_conn()
    daos = get_daos(conn)
    row = daos["vehicle"].buscar_por_id(vehicle_id)
    conn.close()
    if not row:
        return jsonify({"error": "Vehículo no encontrado"}), 404
    return jsonify({
        "vehicle_id": row[0], "user_id": row[1], "license_plate": row[2],
        "brand": row[3], "model": row[4], "manufacture_year": row[5], "engine_type": row[6]
    })


# ==================== GPS DEVICES ====================

@app.route("/api/vehicles/<vehicle_id>/gps", methods=["POST"])
@require_auth
def assign_gps(vehicle_id):
    data = request.get_json()
    conn = get_conn()
    daos = get_daos(conn)

    veh_row = daos["vehicle"].buscar_por_id(vehicle_id)
    if not veh_row:
        conn.close()
        return jsonify({"error": "Vehículo no encontrado"}), 404

    try:
        dev = GpsDevice(
            vehicle_id=vehicle_id,
            imei=data["imei"],
            hardware_model=data.get("hardware_model", ""),
            level=HardwareLevel(data.get("level", "LEVEL_1_BASIC")),
            is_online=data.get("is_online", False),
        )
    except ValueError as e:
        conn.close()
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        conn.close()
        return jsonify({"error": f"Falta campo: {e}"}), 400

    try:
        daos["gps"].insertar(dev)
        conn.close()
        return jsonify({"device_id": dev.device_id, "imei": dev.imei}), 201
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/gps-devices/<device_id>", methods=["GET"])
@require_auth
def get_gps(device_id):
    conn = get_conn()
    daos = get_daos(conn)
    row = daos["gps"].buscar_por_id(device_id)
    conn.close()
    if not row:
        return jsonify({"error": "Dispositivo no encontrado"}), 404
    return jsonify({
        "device_id": row[0], "vehicle_id": row[1], "imei": row[2],
        "hardware_model": row[3], "hardware_level": row[4], "is_online": bool(row[5])
    })


# ==================== TELEMETRY ====================

@app.route("/api/telemetry", methods=["POST"])
@require_auth
def create_telemetry():
    data = request.get_json()
    conn = get_conn()
    daos = get_daos(conn)

    device_row = daos["gps"].buscar_por_id(data.get("device_id", ""))
    if not device_row:
        conn.close()
        return jsonify({"error": "Dispositivo GPS no encontrado"}), 404

    try:
        tele = TelemetryLog(
            device_id=data["device_id"],
            point_wkt=data["point_wkt"],
            speed_kmh=data.get("speed_kmh", 0.0),
            heading=data.get("heading", 0.0),
            acc_ignition=data.get("acc_ignition", False),
            main_battery=data.get("main_battery"),
            backup_battery=data.get("backup_battery"),
            fuel_level=data.get("fuel_level"),
            odometer_km=data.get("odometer_km", 0.0),
            dashcam_recording=data.get("dashcam_recording", False),
        )
    except ValueError as e:
        conn.close()
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        conn.close()
        return jsonify({"error": f"Falta campo: {e}"}), 400

    try:
        tid = daos["telemetry"].insertar(tele)
        # Broadcast via WebSocket
        broadcast_telemetry({
            "telemetry_id": tid,
            "device_id": tele.device_id,
            "point_wkt": tele.point_wkt,
            "speed_kmh": tele.speed_kmh,
            "heading": tele.heading,
            "acc_ignition": tele.acc_ignition,
            "odometer_km": tele.odometer_km,
            "dashcam_recording": tele.dashcam_recording,
        })

        # --- Alert evaluation ---
        alerts_created = []
        # Overspeed
        overspeed_alert = Alert.evaluate_overspeed(tele.device_id, tele.speed_kmh)
        if overspeed_alert:
            daos["alert"].insertar(overspeed_alert)
            alerts_created.append(overspeed_alert)
        # Geofence
        try:
            from dao.geofence_dao import GeofenceDao
            gf_dao = GeofenceDao(conn)
            # Find vehicle_id from device_id
            dev_row = daos["gps"].buscar_por_id(tele.device_id)
            if dev_row:
                vid = dev_row[1]
                gf_rows = gf_dao.listar_por_vehiculo(vid)
                if gf_rows:
                    from model.geofence import Geofence
                    gf_objects = []
                    for gfr in gf_rows:
                        gf_obj = Geofence(
                            vehicle_id=gfr[1], name=gfr[2], area_wkt=gfr[3],
                            geofence_id=gfr[0], created_at=gfr[4])
                        gf_objects.append({"geofence": gf_obj, "was_inside": None})
                    geo_alerts = Alert.evaluate_geofence(
                        tele.device_id, vid, tele.point_wkt, gf_objects)
                    for a in geo_alerts:
                        daos["alert"].insertar(a)
                        alerts_created.append(a)
        except Exception:
            pass

        # Broadcast alerts via WebSocket
        for a in alerts_created:
            socketio.emit("alert_update", {
                "alert_id": a.alert_id,
                "device_id": a.device_id,
                "type": a.type.value,
                "message": a.message,
                "status": a.status.value,
                "created_at": a.created_at,
            }, room="telemetry")

        conn.close()
        return jsonify({"telemetry_id": tid, "device_id": tele.device_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/telemetry", methods=["GET"])
@require_auth
def list_telemetry():
    device_id = request.args.get("device_id", "")
    conn = get_conn()
    daos = get_daos(conn)
    if device_id:
        rows = daos["telemetry"].listar_por_device(device_id)
    else:
        rows = daos["telemetry"].listar()
    conn.close()
    return jsonify([
        {
            "telemetry_id": r[0], "device_id": r[1], "recorded_at": r[2],
            "point_wkt": r[3], "speed_kmh": r[4], "heading": r[5],
            "acc_ignition": bool(r[6]),
            "main_battery": r[7], "backup_battery": r[8],
            "fuel_level": r[9],
            "odometer_km": r[10],
            "dashcam_recording": bool(r[11]),
        }
        for r in rows
    ])


# ==================== CUT ENGINE COMMANDS ====================

@app.route("/api/commands", methods=["POST"])
@require_auth
def create_command():
    data = request.get_json()
    conn = get_conn()
    daos = get_daos(conn)

    device_row = daos["gps"].buscar_por_id(data.get("device_id", ""))
    if not device_row:
        conn.close()
        return jsonify({"error": "Dispositivo GPS no encontrado"}), 404

    cmd = CutEngineCommand(
        device_id=data["device_id"],
        doors_locked=bool(data.get("doors_locked", False)),
        windows_closed=bool(data.get("windows_closed", False)),
    )
    if data.get("activate_anti_theft"):
        cmd.activate_anti_theft_lock()

    try:
        daos["command"].insertar(cmd)
        conn.close()
        return jsonify({
            "command_id": cmd.command_id,
            "device_id": cmd.device_id,
            "status": cmd.status.value,
            "doors_locked": cmd.doors_locked,
            "windows_closed": cmd.windows_closed,
            "requested_at": cmd.requested_at,
        }), 201
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/commands/<command_id>", methods=["GET"])
@require_auth
def get_command(command_id):
    conn = get_conn()
    daos = get_daos(conn)
    row = daos["command"].buscar_por_id(command_id)
    conn.close()
    if not row:
        return jsonify({"error": "Comando no encontrado"}), 404
    return jsonify({
        "command_id": row[0], "device_id": row[1], "requested_at": row[2],
        "status": row[3], "executed_at": row[4], "speed_at_execution": row[5],
    })


@app.route("/api/commands/<command_id>/execute", methods=["PATCH"])
@require_auth
def execute_command(command_id):
    conn = get_conn()
    daos = get_daos(conn)
    row = daos["command"].buscar_por_id(command_id)
    if not row:
        conn.close()
        return jsonify({"error": "Comando no encontrado"}), 404

    status = row[3]
    if status == "EXECUTED":
        conn.close()
        return jsonify({"error": "Comando ya ejecutado"}), 400
    if status == "CANCELLED_SAFETY":
        conn.close()
        return jsonify({"error": "Comando cancelado"}), 400

    device_id = row[1]
    speed = daos["telemetry"].ultima_velocidad(device_id)
    if speed is None:
        conn.close()
        return jsonify({"error": "No hay telemetría para validar velocidad"}), 400

    if not CutEngineCommand.validate_safety_speed(speed):
        conn.close()
        return jsonify({
            "error": f"Velocidad actual {speed} km/h excede límite seguro de 20 km/h. "
                     "Comando permanece PENDING_SPEED_CHECK.",
            "speed_kmh": speed,
            "status": "PENDING_SPEED_CHECK"
        }), 400

    daos["command"].actualizar_estado(
        command_id, "EXECUTED",
        executed_at=datetime.now(timezone.utc).isoformat(),
        speed_at_execution=speed,
    )
    conn.close()
    return jsonify({
        "command_id": command_id,
        "status": "EXECUTED",
        "speed_at_execution": speed,
    })


@app.route("/api/commands/<command_id>/cancel", methods=["PATCH"])
@require_auth
def cancel_command(command_id):
    conn = get_conn()
    daos = get_daos(conn)
    row = daos["command"].buscar_por_id(command_id)
    if not row:
        conn.close()
        return jsonify({"error": "Comando no encontrado"}), 404

    if row[3] == "EXECUTED":
        conn.close()
        return jsonify({"error": "Comando ya ejecutado, no se puede cancelar"}), 400

    daos["command"].actualizar_estado(command_id, "CANCELLED_SAFETY")
    conn.close()
    return jsonify({
        "command_id": command_id,
        "status": "CANCELLED_SAFETY",
    })


@app.route("/api/commands", methods=["GET"])
@require_auth
def list_commands():
    device_id = request.args.get("device_id")
    status = request.args.get("status")
    conn = get_conn()
    daos = get_daos(conn)
    rows = daos["command"].listar()
    conn.close()
    if device_id:
        rows = [r for r in rows if r[1] == device_id]
    if status:
        rows = [r for r in rows if r[3] == status]
    return jsonify([
        {"command_id": r[0], "device_id": r[1], "requested_at": r[2],
         "status": r[3], "executed_at": r[4], "speed_at_execution": r[5]}
        for r in rows
    ])


# ==================== ALERTS ====================

@app.route("/api/alerts", methods=["GET"])
@require_auth
def list_alerts():
    device_id = request.args.get("device_id")
    status = request.args.get("status")
    alert_type = request.args.get("type")
    conn = get_conn()
    daos = get_daos(conn)
    rows = daos["alert"].listar(device_id=device_id, status=status, alert_type=alert_type)
    conn.close()
    return jsonify([
        {"alert_id": r[0], "device_id": r[1], "type": r[2],
         "message": r[3], "status": r[4], "created_at": r[5]}
        for r in rows
    ])


@app.route("/api/alerts/<alert_id>/ack", methods=["PATCH"])
@require_auth
def ack_alert(alert_id):
    conn = get_conn()
    daos = get_daos(conn)
    row = daos["alert"].buscar_por_id(alert_id)
    if not row:
        conn.close()
        return jsonify({"error": "Alerta no encontrada"}), 404
    if row[4] == "ACKNOWLEDGED":
        conn.close()
        return jsonify({"error": "Alerta ya está ACKNOWLEDGED"}), 400
    daos["alert"].acknowledge(alert_id)
    conn.close()
    return jsonify({"alert_id": alert_id, "status": "ACKNOWLEDGED"})


# ==================== HEALTH ====================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "PLUMA GPS v3.0 - Nivel 3"})


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
