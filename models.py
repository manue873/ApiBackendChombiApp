# models.py
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from db import Base

# ======================================================
# Modelos mínimos para el MVP
# (alineados con el script SQL que ya te di)
# ======================================================

class Line(Base):
    __tablename__ = "lines"
    __table_args__ = {"schema": "chombi"}

    # id legible: L45, L12, etc.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    color_hex: Mapped[Optional[str]] = mapped_column(String, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    shapes: Mapped[list["LineShape"]] = relationship("LineShape", back_populates="line", cascade="all, delete-orphan")


class LineShape(Base):
    __tablename__ = "line_shapes"
    __table_args__ = (
        Index("idx_line_shapes_line_seq", "line_id", "seq"),
        {"schema": "chombi"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_id: Mapped[str] = mapped_column(ForeignKey("chombi.lines.id", ondelete="CASCADE"), index=True)
    lat: Mapped[float] = mapped_column(Float)  # DOUBLE PRECISION
    lng: Mapped[float] = mapped_column(Float)
    seq: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    line: Mapped["Line"] = relationship("Line", back_populates="shapes")


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = {"schema": "chombi"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String, default=None)
    status: Mapped[str] = mapped_column(String, default="active")  # simplificado
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = {"schema": "chombi"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placa: Mapped[Optional[str]] = mapped_column(String, unique=True, default=None)
    code: Mapped[Optional[str]] = mapped_column(String, default=None)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("driver_id", "is_active", name="uq_active_driver"),
        Index("idx_assignments_line_active", "line_id", "is_active"),
        Index("idx_assignments_vehicle_active", "vehicle_id", "is_active"),
        {"schema": "chombi"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chombi.drivers.id", ondelete="CASCADE"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chombi.vehicles.id", ondelete="CASCADE"))
    line_id: Mapped[str] = mapped_column(ForeignKey("chombi.lines.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        Index("idx_locations_line_time", "line_id", "timestamp_ms"),
        Index("idx_locations_vehicle_time", "vehicle_id", "timestamp_ms"),
        Index("idx_locations_driver_time", "driver_id", "timestamp_ms"),
        Index("idx_locations_time", "timestamp_ms"),
        {"schema": "chombi"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chombi.drivers.id", ondelete="CASCADE"))
    vehicle_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("chombi.vehicles.id", ondelete="SET NULL"))
    line_id: Mapped[Optional[str]] = mapped_column(ForeignKey("chombi.lines.id", ondelete="SET NULL"))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[Optional[float]] = mapped_column(Float, default=None)
    speed_mps: Mapped[Optional[float]] = mapped_column(Float, default=None)
    heading_deg: Mapped[Optional[float]] = mapped_column(Float, default=None)
    timestamp_ms: Mapped[int] = mapped_column(BigInteger)  # epoch millis del dispositivo
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    source: Mapped[Optional[str]] = mapped_column(String, default="driver-app")

    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="chk_lat"),
        CheckConstraint("lng BETWEEN -180 AND 180", name="chk_lng"),
        Index("idx_locations_line_time", "line_id", "timestamp_ms"),
        Index("idx_locations_vehicle_time", "vehicle_id", "timestamp_ms"),
        Index("idx_locations_driver_time", "driver_id", "timestamp_ms"),
        Index("idx_locations_time", "timestamp_ms"),
        {"schema": "chombi"},
    )
