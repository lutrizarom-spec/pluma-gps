# PLUMA GPS v3.0 — Niveles 1-3

Sistema de telemetría geoespacial y seguridad vehicular con API REST, WebSockets y JWT.

## Stack
- **Nivel 1:** Python 3.14 + SQLite (modelo, DAO, tests)
- **Nivel 2:** Flask (API REST con 17 endpoints)
- **Nivel 3:** JWT + bcrypt + WebSockets (SocketIO)
- **Nivel 3.3:** PostgreSQL + Alembic + Docker

## Estructura
```
pluma-gps/
├── model/          # 6 clases UML + enums
├── dao/            # 6 DAOs + clase base (SQLite/PostgreSQL dual)
├── api/            # Flask app + auth (JWT) + ws (SocketIO)
├── tests/          # 139 tests (unit + integration + API + auth + WS)
├── alembic/        # Migraciones PostgreSQL
├── conectar.py     # Factory conexión (SQLite/PostgreSQL)
├── main.py         # Entry point CLI
├── Dockerfile      # Imagen API
├── docker-compose.yml  # PostgreSQL + API
├── .env            # Variables de entorno
├── SDD.md          # Software Design Document
└── requirements.txt
```

## Ejecutar local (SQLite)
```bash
python main.py                         # Inicializar BD + smoke test
python -m unittest discover tests/ -v  # 139 tests
```

## Ejecutar con Docker (PostgreSQL)
```bash
docker-compose up --build
# Alembic ejecuta migración automáticamente al iniciar
# API disponible en http://localhost:5000
```

## Endpoints
- **Auth:** POST /api/auth/register, POST /api/auth/login
- **Users:** POST/GET /api/users, GET /api/users/:id
- **Vehicles:** POST /api/users/:id/vehicles, GET /api/vehicles
- **GPS:** POST /api/vehicles/:id/gps, GET /api/gps-devices/:id
- **Telemetry:** POST/GET /api/telemetry
- **Commands:** POST/GET/PATCH /api/commands
- **WebSocket:** /ws/telemetry (broadcast en tiempo real)
- **Health:** GET /api/health
