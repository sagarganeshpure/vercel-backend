from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class CarpenterCaptain(Base):
    """Carpenter Captain Assignment to Sites"""
    __tablename__ = "carpenter_captains"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    wing = Column(String, nullable=True)  # Assigned wing(s) - can be JSON array
    assigned_date = Column(Date, nullable=False, default=func.current_date())
    status = Column(String, default="Active", nullable=False)  # Active, Inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    site = relationship("Site", foreign_keys=[site_id])


class WorkAllocation(Base):
    """Daily Work Allocation to Carpenters"""
    __tablename__ = "work_allocations"

    id = Column(Integer, primary_key=True, index=True)
    captain_id = Column(Integer, ForeignKey("carpenter_captains.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    allocation_date = Column(Date, nullable=False, index=True)
    flat_numbers = Column(Text, nullable=False)  # JSON array of flat numbers
    work_type = Column(String, nullable=False)  # Frame Fixing, Door Fixing, Both
    assigned_carpenters = Column(Text, nullable=True)  # JSON array of carpenter names/IDs
    target_quantity = Column(Integer, nullable=True)  # Target number of flats/doors/frames
    status = Column(String, default="Pending", nullable=False)  # Pending, In Progress, Completed
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    captain = relationship("CarpenterCaptain", foreign_keys=[captain_id])
    site = relationship("Site", foreign_keys=[site_id])


class CarpenterFrameFixing(Base):
    """Frame Fixing Record"""
    __tablename__ = "carpenter_frame_fixings"

    id = Column(Integer, primary_key=True, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    captain_id = Column(Integer, ForeignKey("carpenter_captains.id"), nullable=False, index=True)
    frame_type = Column(String, nullable=False)  # Bedroom, Bathroom, Kitchen, Main Door
    fixing_status = Column(String, default="Pending", nullable=False)  # Pending, Completed, On Hold
    fixing_date = Column(Date, nullable=True)
    carpenter_name = Column(String, nullable=True)
    issue = Column(Text, nullable=True)  # Issue description if any
    photo_url = Column(Text, nullable=True)  # URL or path to photo
    supervisor_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    flat = relationship("Flat", foreign_keys=[flat_id])
    site = relationship("Site", foreign_keys=[site_id])
    captain = relationship("CarpenterCaptain", foreign_keys=[captain_id])
    approver = relationship("User", foreign_keys=[approved_by])


class CarpenterDoorFixing(Base):
    """Door Fixing Record"""
    __tablename__ = "carpenter_door_fixings"

    id = Column(Integer, primary_key=True, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    captain_id = Column(Integer, ForeignKey("carpenter_captains.id"), nullable=False, index=True)
    door_type = Column(String, nullable=False)  # Main Door, Bedroom Door, Bathroom Door, Kitchen Door
    fixing_status = Column(String, default="Pending", nullable=False)  # Pending, Completed, On Hold
    fixing_date = Column(Date, nullable=True)
    carpenter_name = Column(String, nullable=True)
    reason = Column(Text, nullable=True)  # Reason if on hold
    customer_instruction = Column(Text, nullable=True)  # Special customer instructions
    photo_url = Column(Text, nullable=True)  # URL or path to photo
    supervisor_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    flat = relationship("Flat", foreign_keys=[flat_id])
    site = relationship("Site", foreign_keys=[site_id])
    captain = relationship("CarpenterCaptain", foreign_keys=[captain_id])
    approver = relationship("User", foreign_keys=[approved_by])


class CarpenterAttendance(Base):
    """Carpenter Attendance & Manpower Tracking"""
    __tablename__ = "carpenter_attendances"

    id = Column(Integer, primary_key=True, index=True)
    captain_id = Column(Integer, ForeignKey("carpenter_captains.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    carpenter_name = Column(String, nullable=False)
    present = Column(Boolean, default=True)
    work_hours = Column(Float, nullable=True)  # Hours worked
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    captain = relationship("CarpenterCaptain", foreign_keys=[captain_id])
    site = relationship("Site", foreign_keys=[site_id])


class CarpenterIssue(Base):
    """Issues & Constraints Reporting"""
    __tablename__ = "carpenter_issues"

    id = Column(Integer, primary_key=True, index=True)
    captain_id = Column(Integer, ForeignKey("carpenter_captains.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=True, index=True)
    issue_type = Column(String, nullable=False)  # Window not fixed, Civil work pending, Material missing, Access blocked, Builder instruction change
    description = Column(Text, nullable=False)
    status = Column(String, default="Open", nullable=False)  # Open, Resolved, Closed
    reported_date = Column(Date, nullable=False, default=func.current_date())
    resolved_date = Column(Date, nullable=True)
    photo_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    captain = relationship("CarpenterCaptain", foreign_keys=[captain_id])
    site = relationship("Site", foreign_keys=[site_id])
    flat = relationship("Flat", foreign_keys=[flat_id])


class WorkCompletion(Base):
    """Work Completion Summary for Accounts"""
    __tablename__ = "work_completions"

    id = Column(Integer, primary_key=True, index=True)
    captain_id = Column(Integer, ForeignKey("carpenter_captains.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    summary_date = Column(Date, nullable=False, index=True)  # Daily or weekly summary
    carpenter_name = Column(String, nullable=False)
    doors_fixed = Column(Integer, default=0)
    frames_fixed = Column(Integer, default=0)
    supervisor_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    captain = relationship("CarpenterCaptain", foreign_keys=[captain_id])
    site = relationship("Site", foreign_keys=[site_id])
    approver = relationship("User", foreign_keys=[approved_by])

