from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Site(Base):
    """Site Master - Links to SiteProject from Sales Module"""
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    site_project_id = Column(Integer, ForeignKey("site_projects.id"), nullable=False, index=True)
    site_code = Column(String, unique=True, index=True, nullable=True)  # Auto-generated
    
    # Site Details (from SiteProject - read-only)
    builder_name = Column(String, nullable=False)  # From party
    project_name = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    # Site Structure
    wings = Column(Text, nullable=True)  # JSON array: ["A", "B", "C", "D", "E"]
    total_floors = Column(Integer, nullable=True)
    total_flats = Column(Integer, nullable=True)
    
    # Status
    site_status = Column(String, default="Active", nullable=False)  # Active, Completed, On Hold
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    site_project = relationship("SiteProject")
    flats = relationship("Flat", back_populates="site", cascade="all, delete-orphan")
    daily_progress_reports = relationship("DailySiteProgress", back_populates="site")
    issues = relationship("SiteIssue", back_populates="site")


class Flat(Base):
    """Flat-wise Door & Frame Register"""
    __tablename__ = "flats"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    flat_number = Column(String, nullable=False, index=True)  # e.g., "1803"
    wing = Column(String, nullable=False, index=True)  # e.g., "D"
    floor = Column(Integer, nullable=False, index=True)  # e.g., 18
    
    # Door Requirements (Boolean flags)
    main_door_required = Column(Boolean, default=False)
    bedroom_door_required = Column(Boolean, default=False)
    bathroom_door_required = Column(Boolean, default=False)
    kitchen_door_required = Column(Boolean, default=False)
    
    # Fixing Status
    frame_fixed = Column(Boolean, default=False)
    door_fixed = Column(Boolean, default=False)
    
    # Additional Info
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    site = relationship("Site", back_populates="flats")
    measurements = relationship("SiteMeasurement", back_populates="flat")
    frame_fixings = relationship("FrameFixing", back_populates="flat")
    door_fixings = relationship("DoorFixing", back_populates="flat")
    photos = relationship("SitePhoto", back_populates="flat")


class SiteMeasurement(Base):
    """Measurement & Requirement Entry"""
    __tablename__ = "site_measurements"

    id = Column(Integer, primary_key=True, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    
    # Measurement Details
    location = Column(String, nullable=False)  # Bedroom, Bathroom, Kitchen, Main Door
    width_mm = Column(Float, nullable=False)
    height_mm = Column(Float, nullable=False)
    wall_thickness = Column(Float, nullable=True)
    handing = Column(String, nullable=True)  # Left, Right
    door_type = Column(String, nullable=False)  # Main Door, Bedroom Door, Bathroom Door, Kitchen Door
    frame_type = Column(String, nullable=True)  # Single Rebated, Double Rebated, etc.
    special_note = Column(Text, nullable=True)  # Post form, etc.
    
    # Status
    status = Column(String, default="Pending", nullable=False)  # Pending, Approved, Rejected
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    flat = relationship("Flat", back_populates="measurements")
    site = relationship("Site")


class FrameFixing(Base):
    """Frame Fixing Status"""
    __tablename__ = "frame_fixings"

    id = Column(Integer, primary_key=True, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    
    # Frame Details
    frame_type = Column(String, nullable=False)  # Bedroom, Main Door, etc.
    fixing_status = Column(String, nullable=False)  # Completed, Pending, On Hold
    fixing_date = Column(Date, nullable=True)
    contractor = Column(String, nullable=True)
    floor_readiness = Column(Boolean, default=False)  # Yes/No
    issue = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    flat = relationship("Flat", back_populates="frame_fixings")
    site = relationship("Site")


class DoorFixing(Base):
    """Door Fixing Status"""
    __tablename__ = "door_fixings"

    id = Column(Integer, primary_key=True, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    
    # Door Details
    door_type = Column(String, nullable=False)  # Main Door, Bedroom Door, etc.
    fixing_status = Column(String, nullable=False)  # Completed, Pending, On Hold
    reason = Column(Text, nullable=True)  # Window not fixed, etc.
    expected_resume_date = Column(Date, nullable=True)
    customer_instruction = Column(Text, nullable=True)  # Only main door, etc.
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    flat = relationship("Flat", back_populates="door_fixings")
    site = relationship("Site")


class DailySiteProgress(Base):
    """Daily Site Progress Report (DSP)"""
    __tablename__ = "daily_site_progress"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    
    # Progress Details
    report_date = Column(Date, nullable=False, index=True)
    wing = Column(String, nullable=True)
    floors_covered = Column(String, nullable=True)  # "Up to 18th"
    frames_fixed_today = Column(Integer, default=0)
    doors_fixed_today = Column(Integer, default=0)
    work_front_available = Column(Boolean, default=True)
    constraints = Column(Text, nullable=True)  # Window pending, etc.
    tomorrow_plan = Column(Text, nullable=True)  # Frame fixing 19-20
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    site = relationship("Site", back_populates="daily_progress_reports")


class SiteIssue(Base):
    """Issues & Constraints"""
    __tablename__ = "site_issues"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=True, index=True)
    
    # Issue Details
    issue_type = Column(String, nullable=False)  # Window not fixed, Civil work pending, Material shortage, Access blocked, Customer change request
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    wing = Column(String, nullable=True)
    floor = Column(Integer, nullable=True)
    
    # Status
    status = Column(String, default="Open", nullable=False)  # Open, Closed, Resolved
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    site = relationship("Site", back_populates="issues")
    flat = relationship("Flat")


class SitePhoto(Base):
    """Photos & Attachments"""
    __tablename__ = "site_photos"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=True, index=True)
    
    # Photo Details
    photo_type = Column(String, nullable=False)  # Frame fixed, Door fixed, Damage, Constraint, General
    photo_url = Column(Text, nullable=False)  # URL or base64
    caption = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    site = relationship("Site")
    flat = relationship("Flat", back_populates="photos")

