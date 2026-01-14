from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Vehicle(Base):
    """Vehicle Master - For logistics assignment"""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_no = Column(String, unique=True, index=True, nullable=False)
    vehicle_type = Column(String, nullable=False)  # Truck, Tempo, Container, etc.
    capacity_tonnes = Column(Float, nullable=True)
    capacity_cubic_meters = Column(Float, nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    current_location = Column(String, nullable=True)
    gps_enabled = Column(Boolean, default=False, nullable=False)
    insurance_expiry = Column(Date, nullable=True)
    registration_expiry = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    assignments = relationship("LogisticsAssignment", back_populates="vehicle")


class Driver(Base):
    """Driver Master - For logistics assignment"""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    mobile = Column(String, nullable=False, unique=True, index=True)
    license_number = Column(String, nullable=False, unique=True, index=True)
    license_expiry = Column(Date, nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    assignments = relationship("LogisticsAssignment", back_populates="driver")


class LogisticsAssignment(Base):
    """Vehicle & Driver Assignment to Dispatch Orders"""
    __tablename__ = "logistics_assignments"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=False, unique=True, index=True)
    dispatch_number = Column(String, nullable=False, index=True)
    
    # Vehicle Assignment
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    vehicle_no = Column(String, nullable=False)
    
    # Driver Assignment
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False, index=True)
    driver_name = Column(String, nullable=False)
    driver_mobile = Column(String, nullable=False)
    
    # Assignment Details
    planned_delivery_date = Column(Date, nullable=False)
    route_area = Column(String, nullable=True)
    assignment_notes = Column(Text, nullable=True)
    
    # Status
    status = Column(String, default="assigned", nullable=False)  # assigned, in_transit, delivered, delayed
    
    # Audit
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Logistics Manager
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    dispatch = relationship("Dispatch", foreign_keys=[dispatch_id], back_populates="logistics_assignment", overlaps="logistics_assignment")
    vehicle = relationship("Vehicle", back_populates="assignments")
    driver = relationship("Driver", back_populates="assignments")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class DeliveryIssue(Base):
    """Delivery Issues - Reported by Driver/Logistics"""
    __tablename__ = "delivery_issues"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=False, index=True)
    dispatch_number = Column(String, nullable=False, index=True)
    
    # Issue Details
    issue_type = Column(String, nullable=False)  # delivery_delay, damage, shortage, wrong_address, vehicle_breakdown
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="medium", nullable=False)  # low, medium, high, critical
    
    # Resolution
    status = Column(String, default="reported", nullable=False)  # reported, under_review, resolved, closed
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Images/Evidence
    issue_photo_url = Column(Text, nullable=True)  # URL or base64
    
    # Audit
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Driver or Logistics Executive
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Logistics Manager
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    dispatch = relationship("Dispatch", foreign_keys=[dispatch_id])
    reported_by_user = relationship("User", foreign_keys=[reported_by])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by])

