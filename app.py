# app.py
import os
import uuid
from typing import List, Optional
from fastapi import HTTPException, Response
from sqlalchemy import select
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, Header, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, conlist, condecimal
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from db import get_db, create_tables
from models import Line, LineShape, Location, Assignment, Driver

# ======================================================
# FastAPI
# ======================================================
app = FastAPI(title="Chombi Backend MVP", version="0.1.0")

# CORS abierto para el MVP (ajusta en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("CHOMBI_API_KEY")  # opcional

@app.head("/v1/drivers/{driver_id}")
def head_driver(driver_id: UUID, db: Session = Depends(get_db)):
    exists = db.execute(select(Driver.id).where(Driver.id == driver_id)).first()
    if not exists:
        raise HTTPException(status_code=404)
    return Response(status_code=204)

def auth_dep(authorization: Optional[str] = Header(None)):
    """
    Autenticación mínima por API-Key (opcional).
    Pasa la key por header Authorization: Bearer <KEY>.
    """
    if API_KEY is None:
        return  # sin auth en MVP
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.on_event("startup")
def on_startup():
    # Crea tablas mínimas si no existen (útil en local)
    create_tables()


# ======================================================
# Schemas
# ======================================================
class LineOut(BaseModel):
    id: str
    name: str
    color_hex: Optional[str] = None

    class Config:
        from_attributes = True


class LatLngDto(BaseModel):
    lat: float
    lng: float


class LocationIn(BaseModel):
    driver_id: uuid.UUID
    vehicle_id: Optional[uuid.UUID] = None
    line_id: Optional[str] = None
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = None
    speed_mps: Optional[float] = None
    heading_deg: Optional[float] = Field(None, ge=0, le=360)
    timestamp_ms: int = Field(..., description="Epoch millis from device")
    source: Optional[str] = "driver-app"


class LocationReadDto(BaseModel):
    id: int
    driver_id: uuid.UUID
    vehicle_id: Optional[uuid.UUID]
    line_id: Optional[str]
    lat: float
    lng: float
    accuracy_m: Optional[float]
    speed_mps: Optional[float]
    heading_deg: Optional[float]
    timestamp_ms: int
    # received_at excluded para payload más chico
    source: Optional[str]


# ======================================================
# Endpoints
# ======================================================

@app.get("/health")
def health():
    return {"ok": True}




@app.get("/v1/lines", response_model=List[LineOut], dependencies=[Depends(auth_dep)])
def list_lines(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Line).where(Line.is_active == True).order_by(Line.id)
    ).scalars().all()
    return rows


@app.get("/v1/lines/{line_id}/shape", response_model=List[LatLngDto], dependencies=[Depends(auth_dep)])
def get_line_shape(
    line_id: str = Path(..., description="ID legible de línea, ej. L45"),
    db: Session = Depends(get_db)
):
    # Devuelve polyline ordenado por seq
    sql = text("""
        SELECT lat, lng
        FROM chombi.line_shapes
        WHERE line_id = :line_id
        ORDER BY seq
    """)
    res = db.execute(sql, {"line_id": line_id}).mappings().all()
    return [{"lat": r["lat"], "lng": r["lng"]} for r in res]


@app.get("/v1/lines/{line_id}/latest", response_model=List[LocationReadDto], dependencies=[Depends(auth_dep)])
def latest_by_line(
    line_id: str,
    db: Session = Depends(get_db)
):
    """
    Última ubicación por vehículo en una línea.
    Usamos DISTINCT ON (vehicle_id) de Postgres para performance y simplicidad.
    """
    sql = text("""
        SELECT DISTINCT ON (vehicle_id)
            id, driver_id, vehicle_id, line_id, lat, lng,
            accuracy_m, speed_mps, heading_deg, timestamp_ms, source
        FROM chombi.locations
        WHERE line_id = :line_id
        ORDER BY vehicle_id, timestamp_ms DESC
    """)
    res = db.execute(sql, {"line_id": line_id}).mappings().all()
    return [
        {
            "id": r["id"],
            "driver_id": r["driver_id"],
            "vehicle_id": r["vehicle_id"],
            "line_id": r["line_id"],
            "lat": r["lat"],
            "lng": r["lng"],
            "accuracy_m": r["accuracy_m"],
            "speed_mps": r["speed_mps"],
            "heading_deg": r["heading_deg"],
            "timestamp_ms": r["timestamp_ms"],
            "source": r["source"],
        } for r in res
    ]



@app.post("/v1/locations", status_code=204, dependencies=[Depends(auth_dep)])
def post_location(payload: LocationIn, db: Session = Depends(get_db)):
    """
    Inserta una ubicación. Si no llega vehicle_id o line_id,
    intenta resolverlos con la asignación activa del driver.
    """
    driver_id = payload.driver_id
    vehicle_id = payload.vehicle_id
    line_id = payload.line_id

    # Autocompletar desde assignments si falta info
    if vehicle_id is None or line_id is None:
        assign = db.execute(text("""
            SELECT vehicle_id, line_id
            FROM chombi.assignments
            WHERE driver_id = :driver_id AND is_active = TRUE
            ORDER BY started_at DESC
            LIMIT 1
        """), {"driver_id": str(driver_id)}).mappings().first()
        if assign:
            vehicle_id = vehicle_id or assign["vehicle_id"]
            line_id = line_id or assign["line_id"]

    # Validaciones básicas
    if line_id is None:
        # Permitimos line_id nulo si usas sólo /latest por vehicle,
        # pero para el caso de Passenger te conviene tenerlo.
        pass

    sql = text("""
        INSERT INTO chombi.locations
        (driver_id, vehicle_id, line_id, lat, lng, accuracy_m, speed_mps, heading_deg, timestamp_ms, source)
        VALUES (:driver_id, :vehicle_id, :line_id, :lat, :lng, :accuracy_m, :speed_mps, :heading_deg, :timestamp_ms, :source)
    """)
    db.execute(sql, {
        "driver_id": str(driver_id),
        "vehicle_id": str(vehicle_id) if vehicle_id else None,
        "line_id": line_id,
        "lat": payload.lat,
        "lng": payload.lng,
        "accuracy_m": payload.accuracy_m,
        "speed_mps": payload.speed_mps,
        "heading_deg": payload.heading_deg,
        "timestamp_ms": payload.timestamp_ms,
        "source": payload.source or "driver-app",
    })
    db.commit()
    return None
