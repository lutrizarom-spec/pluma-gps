import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import conectar
from dao.dao import Dao


def main():
    print("=== PLUMA GPS v3.0 — Nivel 1: Inicialización BD ===")

    conn = conectar.crear_conexion()
    dao_base = Dao(conn)

    print("\n[1] Creando 6 tablas en orden de dependencia FK...")
    dao_base.crear_todas_las_tablas()

    print("\n[2] Verificando tablas creadas...")
    conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tablas = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]

    esperadas = ["users", "vehicles", "gps_devices", "geofences", "telemetry_logs", "cut_engine_commands"]
    for t in esperadas:
        status = "✅" if t in tablas else "❌"
        print(f"   {status} {t}")

    # Smoke test: insertar datos de prueba
    print("\n[3] Smoke test: inserción de datos de prueba...")
    from model.enums import PlanSubscription, HardwareLevel, CommandStatus
    from model.user import User
    from model.vehicle import Vehicle
    from model.gps_device import GpsDevice
    from model.geofence import Geofence
    from model.telemetry_log import TelemetryLog
    from model.cut_engine_command import CutEngineCommand

    from dao.user_dao import UserDao
    from dao.vehicle_dao import VehicleDao
    from dao.gps_device_dao import GpsDeviceDao
    from dao.geofence_dao import GeofenceDao
    from dao.telemetry_dao import TelemetryDao
    from dao.command_dao import CutEngineCommandDao

    u_dao, v_dao, g_dao, gf_dao, t_dao, c_dao = (
        UserDao(conn), VehicleDao(conn), GpsDeviceDao(conn),
        GeofenceDao(conn), TelemetryDao(conn), CutEngineCommandDao(conn)
    )

    user = User(rut="12.345.678-5", full_name="Juan Pérez", email="jperez@test.cl",
                plan=PlanSubscription.PRO_MONTHLY)
    u_dao.insertar(user)
    print(f"   User: {user.rut} ({user.user_id[:8]}...) ✅")

    veh = Vehicle(user_id=user.user_id, license_plate="ABC123",
                  brand="Toyota", model="Hilux", manufacture_year=2024, engine_type="diesel")
    v_dao.insertar(veh)
    print(f"   Vehicle: {veh.license_plate} ({veh.vehicle_id[:8]}...) ✅")

    dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345",
                    hardware_model="Coban TK103", level=HardwareLevel.LEVEL_1_BASIC, is_online=True)
    g_dao.insertar(dev)
    print(f"   GpsDevice: {dev.imei} ({dev.device_id[:8]}...) ✅")

    gf = Geofence(vehicle_id=veh.vehicle_id, name="Casa",
                  area_wkt="POLYGON((-70.6 -33.4, -70.5 -33.4, -70.5 -33.5, -70.6 -33.5, -70.6 -33.4))")
    gf_dao.insertar(gf)
    print(f"   Geofence: {gf.name} ({gf.geofence_id[:8]}...) ✅")

    tele = TelemetryLog(device_id=dev.device_id, point_wkt="POINT(-70.55 -33.45)",
                        speed_kmh=15.0, heading=90.0, acc_ignition=True, brake_fluid_alert=False)
    t_dao.insertar(tele)
    print(f"   TelemetryLog: speed={tele.speed_kmh}km/h (id={tele.telemetry_id}) ✅")

    cmd = CutEngineCommand(device_id=dev.device_id)
    c_dao.insertar(cmd)
    print(f"   CutEngineCommand: {cmd.status.value} ({cmd.command_id[:8]}...) ✅")

    # Validar corte seguro
    print("\n[4] Validación de corte-corriente seguro...")
    speed = t_dao.ultima_velocidad(dev.device_id)
    if CutEngineCommand.validate_safety_speed(speed):
        cmd.mark_as_executed(speed)
        c_dao.actualizar_estado(cmd.command_id, cmd.status.value,
                               cmd.executed_at, cmd.speed_at_execution)
        print(f"   Velocidad {speed}km/h ≤ 20km/h → EJECUTADO ✅")
    else:
        print(f"   Velocidad {speed}km/h > 20km/h → PENDIENTE ⚠️")

    # Validar geofence
    print("\n[5] Validación de geocerca...")
    dentro = gf.check_containment("POINT(-70.55 -33.45)")
    print(f"   Punto dentro de geocerca '{gf.name}': {'Sí ✅' if dentro else 'No ❌'}")

    # Resumen BD
    print("\n[6] Resumen de BD:")
    for nombre, dao in [("users", u_dao), ("vehicles", v_dao),
                         ("gps_devices", g_dao), ("geofences", gf_dao),
                         ("telemetry_logs", t_dao), ("cut_engine_commands", c_dao)]:
        rows = dao.listar() if hasattr(dao, 'listar') else []
        print(f"   {nombre}: {len(rows)} registro(s)")

    print("\n=== Inicialización completada exitosamente ===")
    conn.close()


if __name__ == "__main__":
    main()
