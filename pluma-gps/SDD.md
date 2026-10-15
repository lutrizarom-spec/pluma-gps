# SDD — PLUMA GPS v3.0 (Nivel 1: MVP Educativo)

> Software Design Document — Nivel 1 MVP
> Base: Informe Técnico PLUMA GPS v3.0 + patrón arquitectónico Taller-Mecanico (MVC + DAO)

---

## 1. Arquitectura

```
pluma-gps/
├── model/          # Clases de dominio (UML)
├── dao/            # Data Access Objects (CRUD SQL)
├── tests/          # Pruebas unitarias e integración (TDD)
├── conectar.py     # Factory de conexión SQLite
├── main.py         # Entry point: init BD + smoke test
├── SDD.md          # Este documento
├── README.md
├── .gitignore
└── requirements.txt
```

**Patrones:**
- MVC simplificado: Model (model/) + Data Access (dao/) + Controller (main.py).
- DAO genérico: clase base `Dao` con conexión+cursor, herencia por entidad.
- Table-per-type: `gps_devices` hereda de `vehicles` vía FK.

**Stack Nivel 1:**
- Python 3.11+, SQLite3 (stdlib), `uuid` + `enum` (stdlib).
- Sin dependencias externas (SQLite viene con Python).
- Geometrías como texto WKT (sin PostGIS/Shapely en Nivel 1).

---

## 2. Modelo de Dominio (6 clases UML)

| Clase | Archivo | Responsabilidad |
|---|---|---|
| `User` | `model/user.py` | Usuario con plan de suscripción, valida RUT |
| `Vehicle` | `model/vehicle.py` | Vehículo asociado a usuario, asigna GPS |
| `GpsDevice` | `model/gps_device.py` | Hardware GPS con IMEI, nivel, estado online |
| `Geofence` | `model/geofence.py` | Polígono de contención (WKT) |
| `TelemetryLog` | `model/telemetry_log.py` | Registro telemétrico: posición, velocidad, sensores |
| `CutEngineCommand` | `model/cut_engine_command.py` | Comando de inmovilización con validación de seguridad |

### Enums (`model/enums.py`)
- `PlanSubscription`: `FREE_ADS`, `PRO_MONTHLY`, `ENTERPRISE_FLEET`
- `HardwareLevel`: `LEVEL_1_BASIC`, `LEVEL_2_ADVANCED`, `LEVEL_3_CANBUS`
- `CommandStatus`: `PENDING_SPEED_CHECK`, `EXECUTED`, `CANCELLED_SAFETY`

---

## 3. Esquema de Base de Datos (SQLite)

### Tabla: users
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,        -- UUID
    rut TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    subscription_plan TEXT NOT NULL,  -- ENUM
    is_active INTEGER DEFAULT 1      -- BOOLEAN
);
```

### Tabla: vehicles
```sql
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id TEXT PRIMARY KEY,     -- UUID
    user_id TEXT NOT NULL,
    license_plate TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    manufacture_year INTEGER,
    engine_type TEXT,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);
```

### Tabla: gps_devices
```sql
CREATE TABLE IF NOT EXISTS gps_devices (
    device_id TEXT PRIMARY KEY,      -- UUID
    vehicle_id TEXT NOT NULL UNIQUE, -- 1:1 con vehículo
    imei TEXT NOT NULL UNIQUE,
    hardware_model TEXT,
    hardware_level TEXT NOT NULL,    -- ENUM
    is_online INTEGER DEFAULT 0      -- BOOLEAN
    FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id)
);
```

### Tabla: geofences
```sql
CREATE TABLE IF NOT EXISTS geofences (
    geofence_id TEXT PRIMARY KEY,    -- UUID
    vehicle_id TEXT NOT NULL,
    name TEXT NOT NULL,
    area_wkt TEXT NOT NULL,          -- POLYGON WKT (Nivel 1: texto)
    created_at TEXT NOT NULL,        -- ISO timestamp
    FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id)
);
```

### Tabla: telemetry_logs
```sql
CREATE TABLE IF NOT EXISTS telemetry_logs (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,       -- ISO timestamp
    point_wkt TEXT NOT NULL,         -- POINT WKT
    speed_kmh REAL DEFAULT 0,
    heading REAL DEFAULT 0,
    acc_ignition INTEGER DEFAULT 0,  -- BOOLEAN
    main_battery REAL,
    backup_battery REAL,
    fuel_level REAL,
    odometer_km REAL DEFAULT 0,
    dashcam_recording INTEGER DEFAULT 0, -- BOOLEAN
    FOREIGN KEY (device_id) REFERENCES gps_devices (device_id)
);
```

### Tabla: cut_engine_commands
```sql
CREATE TABLE IF NOT EXISTS cut_engine_commands (
    command_id TEXT PRIMARY KEY,     -- UUID
    device_id TEXT NOT NULL,
    requested_at TEXT NOT NULL,      -- ISO timestamp
    status TEXT NOT NULL,            -- ENUM
    doors_locked INTEGER DEFAULT 0,  -- BOOLEAN (Protocolo Anti-Robo)
    windows_closed INTEGER DEFAULT 0,-- BOOLEAN (Protocolo Anti-Robo)
    executed_at TEXT,
    speed_at_execution REAL,
    FOREIGN KEY (device_id) REFERENCES gps_devices (device_id)
);
```

---

## 4. Reglas de Negocio (Nivel 1)

1. **RUT chileno**: formato `XX.XXX.XXX-Y`, valida dígito verificador (módulo 11).
2. **Inmovilización segura**: `validate_safety_speed(speed)` retorna `True` si `speed <= 20 km/h` (conforme a la legislación chilena).
3. **Plan FREE_ADS**: máximo 1 vehículo.
4. **Geofence**: almacena WKT `POLYGON((...))`, `check_containment` evalúa point-in-polygon básico (bounding box).
5. **Telemetría y Anti-Robo**: registro de `odometer_km`, estado de `dashcam_recording` y bloqueo perimetral de cabina (`doors_locked`, `windows_closed`).

---

## 5. Estrategia TDD

- **Unit tests** (`tests/test_models.py`): cada clase del modelo, validaciones, enums.
- **Integration tests** (`tests/test_dao.py`): crear tablas, insertar, leer, validar FKs.
- **Smoke test** (`tests/test_integration.py`): flujo completo User→Vehicle→GPS→Telemetry→Command.
- Framework: `unittest` (stdlib, sin dependencias).
- Ejecución: `python -m pytest tests/` o `python -m unittest discover tests/`.

---

## 6. Dependencias

```
# requirements.txt
# Nivel 1: sin dependencias externas (SQLite + stdlib)
# Nivel 2: flask
flask
# Futuro Nivel 3: psycopg2, postgis
```

---

## 7. API REST (Nivel 2)

**Framework:** Flask 3.1+ · **Base URL:** `/api` · **Content-Type:** `application/json`

Arquitectura: cada endpoint abre conexión a SQLite, ejecuta DAO, cierra conexión. Las validaciones de dominio (model/) se interceptan en la capa API y se traducen a códigos HTTP.

### 7.1 Health

#### GET /api/health
| Atributo | Valor |
|---|---|
| Descripción | Verifica que el servicio esté activo |
| Request body | — |
| Response 200 | `{"status": "ok", "service": "PLUMA GPS v3.0 - Nivel 2"}` |

---

### 7.2 Usuarios

#### POST /api/users
| Atributo | Valor |
|---|---|
| Descripción | Crea un usuario con validación de RUT chileno |
| Request body | `{"rut": "12.345.678-5", "full_name": "Juan Pérez", "email": "jp@test.cl", "plan": "PRO_MONTHLY"}` |
| Response 201 | `{"user_id": "uuid", "rut": "12.345.678-5"}` |
| Response 400 | `{"error": "RUT inválido: ..."}` — RUT no pasa módulo 11 |
| Response 400 | `{"error": "Falta campo: 'full_name'"}` — campo obligatorio ausente |
| Response 400 | `{"error": "UNIQUE constraint failed: users.rut"}` — RUT duplicado |

**Mapeo de excepciones:**
- `ValueError` (RUT inválido) → 400
- `KeyError` (falta campo) → 400
- `sqlite3.IntegrityError` (UNIQUE) → 400

#### GET /api/users
| Atributo | Valor |
|---|---|
| Descripción | Lista todos los usuarios |
| Response 200 | `[{"user_id", "rut", "full_name", "email", "subscription_plan", "is_active"}]` |

#### GET /api/users/{user_id}
| Atributo | Valor |
|---|---|
| Descripción | Obtiene un usuario por UUID |
| Response 200 | `{"user_id", "rut", "full_name", "email", "subscription_plan", "is_active"}` |
| Response 404 | `{"error": "Usuario no encontrado"}` |

---

### 7.3 Vehículos

#### POST /api/users/{user_id}/vehicles
| Atributo | Valor |
|---|---|
| Descripción | Crea un vehículo asociado a un usuario (valida límite del plan) |
| Request body | `{"license_plate": "ABCD12", "brand": "Toyota", "model": "Hilux", "manufacture_year": 2024, "engine_type": "diesel"}` |
| Response 201 | `{"vehicle_id": "uuid", "license_plate": "ABCD12"}` |
| Response 400 | `{"error": "Patente debe tener entre 6 y 10 caracteres."}` — validación dominio |
| Response 400 | `{"error": "Plan FREE_ADS permite máximo 1 vehículo(s). Actualmente tiene 1."}` — límite de plan |
| Response 404 | `{"error": "Usuario no encontrado"}` |

**Mapeo de excepciones:**
- `ValueError` (patente) → 400
- Límite plan (`PlanSubscription.max_vehicles`) → 400
- Usuario no existe (DAO `buscar_por_id` → None) → 404

#### GET /api/vehicles
| Atributo | Valor |
|---|---|
| Descripción | Lista vehículos (opcional: filtrar por usuario) |
| Query params | `?user_id={uuid}` |
| Response 200 | `[{"vehicle_id", "user_id", "license_plate", "brand", "model", "manufacture_year", "engine_type"}]` |

#### GET /api/vehicles/{vehicle_id}
| Atributo | Valor |
|---|---|
| Descripción | Obtiene un vehículo por UUID |
| Response 200 | `{"vehicle_id", "user_id", "license_plate", "brand", "model", "manufacture_year", "engine_type"}` |
| Response 404 | `{"error": "Vehículo no encontrado"}` |

---

### 7.4 Dispositivos GPS

#### POST /api/vehicles/{vehicle_id}/gps
| Atributo | Valor |
|---|---|
| Descripción | Asigna un GPS a un vehículo (1:1) |
| Request body | `{"imei": "123456789012345", "hardware_model": "Suntech ST4315", "level": "LEVEL_1_BASIC", "is_online": true}` |
| Response 201 | `{"device_id": "uuid", "imei": "123456789012345"}` |
| Response 400 | `{"error": "IMEI debe ser numérico de 14-16 dígitos."}` — validación dominio |
| Response 404 | `{"error": "Vehículo no encontrado"}` |

**Mapeo de excepciones:**
- `ValueError` (IMEI) → 400
- `HardwareLevel` inválido → 400
- Vehículo no existe → 404
- `sqlite3.IntegrityError` (UNIQUE imei o vehicle_id) → 400

#### GET /api/gps-devices/{device_id}
| Atributo | Valor |
|---|---|
| Descripción | Obtiene un GPS por UUID |
| Response 200 | `{"device_id", "vehicle_id", "imei", "hardware_model", "hardware_level", "is_online"}` |
| Response 404 | `{"error": "Dispositivo no encontrado"}` |

---

### 7.5 Telemetría

#### POST /api/telemetry
| Atributo | Valor |
|---|---|
| Descripción | Registra un log de telemetría para un dispositivo GPS |
| Request body | `{"device_id": "uuid", "point_wkt": "POINT(-70.55 -33.45)", "speed_kmh": 15.0, "heading": 90.0, "acc_ignition": true, "main_battery": 12.5, "backup_battery": 95.0, "fuel_level": 60.0, "odometer_km": 12500.0, "dashcam_recording": true}` |
| Response 201 | `{"telemetry_id": 1, "device_id": "uuid"}` |
| Response 400 | `{"error": "point_wkt debe ser un POINT WKT."}` — validación dominio |
| Response 404 | `{"error": "Dispositivo GPS no encontrado"}` |

**Mapeo de excepciones:**
- `ValueError` (WKT inválido) → 400
- Dispositivo no existe → 404

#### GET /api/telemetry
| Atributo | Valor |
|---|---|
| Descripción | Lista registros de telemetría (opcional: filtrar por dispositivo) |
| Query params | `?device_id={uuid}` |
| Response 200 | `[{"telemetry_id", "device_id", "recorded_at", "point_wkt", "speed_kmh", "heading", "acc_ignition", "main_battery", "backup_battery", "fuel_level", "odometer_km", "dashcam_recording"}]` |

---

### 7.6 Comandos de Corte de Motor

#### POST /api/commands
| Atributo | Valor |
|---|---|
| Descripción | Crea un comando de inmovilización en estado PENDING_SPEED_CHECK |
| Request body | `{"device_id": "uuid"}` |
| Response 201 | `{"command_id": "uuid", "device_id": "uuid", "status": "PENDING_SPEED_CHECK", "requested_at": "ISO-8601"}` |
| Response 404 | `{"error": "Dispositivo GPS no encontrado"}` |

#### GET /api/commands/{command_id}
| Atributo | Valor |
|---|---|
| Descripción | Obtiene un comando por UUID |
| Response 200 | `{"command_id", "device_id", "requested_at", "status", "executed_at", "speed_at_execution"}` |
| Response 404 | `{"error": "Comando no encontrado"}` |

#### PATCH /api/commands/{command_id}/execute
| Atributo | Valor |
|---|---|
| Descripción | Evalúa velocidad actual y ejecuta el corte si es seguro (≤ 20 km/h) |
| Request body | — (no requiere body; lee última telemetría del dispositivo) |
| Response 200 | `{"command_id": "uuid", "status": "EXECUTED", "speed_at_execution": 15.0}` |
| Response 400 | `{"error": "Velocidad actual 80.0 km/h excede límite seguro de 20 km/h. Comando permanece PENDING_SPEED_CHECK.", "speed_kmh": 80.0, "status": "PENDING_SPEED_CHECK"}` |
| Response 400 | `{"error": "No hay telemetría para validar velocidad"}` |
| Response 400 | `{"error": "Comando ya ejecutado"}` |
| Response 400 | `{"error": "Comando cancelado"}` |
| Response 404 | `{"error": "Comando no encontrado"}` |

**Mapeo de excepciones:**
- `CutEngineCommand.validate_safety_speed()` retorna `False` → 400
- No hay telemetría registrada → 400
- Status actual = `EXECUTED` → 400
- Status actual = `CANCELLED_SAFETY` → 400

#### PATCH /api/commands/{command_id}/cancel
| Atributo | Valor |
|---|---|
| Descripción | Cancela un comando pendiente por timeout de seguridad |
| Request body | — |
| Response 200 | `{"command_id": "uuid", "status": "CANCELLED_SAFETY"}` |
| Response 400 | `{"error": "Comando ya ejecutado, no se puede cancelar"}` |
| Response 404 | `{"error": "Comando no encontrado"}` |

#### GET /api/commands
| Atributo | Valor |
|---|---|
| Descripción | Lista comandos (opcional: filtrar por dispositivo y/o estado) |
| Query params | `?device_id={uuid}` · `?status=PENDING_SPEED_CHECK` |
| Response 200 | `[{"command_id", "device_id", "requested_at", "status", "executed_at", "speed_at_execution"}]` |

---

### 7.7 Resumen de Mapeo Dominio → HTTP

| Excepción / Regla de dominio | Origen (model/) | HTTP Status | Mensaje |
|---|---|---|---|
| RUT inválido (módulo 11) | `User.rut` setter → `ValueError` | 400 | `"RUT inválido: {valor}"` |
| RUT duplicado | SQLite UNIQUE constraint | 400 | `"UNIQUE constraint failed..."` |
| Límite de plan excedido | `PlanSubscription.max_vehicles` | 400 | `"Plan {plan} permite máximo {n} vehículo(s)..."` |
| Patente inválida | `Vehicle.license_plate` setter → `ValueError` | 400 | `"Patente debe tener entre 6 y 10 caracteres."` |
| IMEI inválido | `GpsDevice.imei` setter → `ValueError` | 400 | `"IMEI debe ser numérico de 14-16 dígitos."` |
| WKT inválido (Telemetry) | `TelemetryLog.point_wkt` setter → `ValueError` | 400 | `"point_wkt debe ser un POINT WKT."` |
| Velocidad > 20 km/h | `CutEngineCommand.validate_safety_speed()` | 400 | `"...excede límite seguro de 20 km/h..."` |
| Sin telemetría para validar | DAO `ultima_velocidad` → `None` | 400 | `"No hay telemetría para validar velocidad"` |
| Comando ya ejecutado | Status check en API | 400 | `"Comando ya ejecutado"` |
| Comando ya cancelado | Status check en API | 400 | `"Comando cancelado"` |
| Recurso no encontrado | DAO `buscar_por_id` → `None` | 404 | `"{Recurso} no encontrado"` |

### 7.8 Dependencia Nivel 2

```
flask>=3.1
```

