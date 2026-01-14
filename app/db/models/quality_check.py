from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class QualityCheck(Base):
    __tablename__ = "quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    qc_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated like "QC001"
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    party_name = Column(String, nullable=True)
    
    # Product Information
    product_type = Column(String, nullable=False)  # Door, Frame
    product_category = Column(String, nullable=True)  # Main Door Shutter, etc.
    product_variant = Column(String, nullable=True)  # From Product Master
    order_type = Column(String, nullable=False)  # Urgent, Regular, Sample
    
    # Quantity Information
    total_quantity = Column(Float, nullable=False)  # Original quantity from production
    accepted_quantity = Column(Float, nullable=True, default=0)
    rework_quantity = Column(Float, nullable=True, default=0)
    rejected_quantity = Column(Float, nullable=True, default=0)
    
    # QC Checklist (JSON - Dynamic based on product attributes)
    checklist_results = Column(JSON, nullable=True)  # Array of checklist items with pass/fail
    
    # QC Decision
    qc_status = Column(String, default="pending", nullable=False)  # pending, approved, rework_required, rejected
    defect_category = Column(String, nullable=True)  # Surface, Dimension, Hardware, Packaging, etc.
    severity = Column(String, nullable=True)  # Critical, Major, Minor
    remarks = Column(Text, nullable=True)
    
    # Photos (JSON array of photo URLs/paths)
    photos = Column(JSON, nullable=True)
    
    # Production Completion Info
    production_completed_date = Column(DateTime(timezone=True), nullable=True)
    supervisor_name = Column(String, nullable=True)
    completed_stages_summary = Column(Text, nullable=True)  # Summary of completed production stages
    
    # QC Inspector
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    inspector_name = Column(String, nullable=True)
    inspection_date = Column(DateTime(timezone=True), nullable=True)
    
    # Rework Information
    rework_job_id = Column(Integer, ForeignKey("rework_jobs.id"), nullable=True)
    rework_department = Column(String, nullable=True)
    rework_target_date = Column(DateTime(timezone=True), nullable=True)
    
    # Cost Impact (for rejected items)
    cost_impact = Column(Float, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper")
    party = relationship("Party")
    inspector = relationship("User", foreign_keys=[inspector_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    rework_jobs = relationship("ReworkJob", foreign_keys="ReworkJob.quality_check_id", back_populates="quality_check", overlaps="quality_check")


class ReworkJob(Base):
    __tablename__ = "rework_jobs"

    id = Column(Integer, primary_key=True, index=True)
    rework_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated like "RW001"
    quality_check_id = Column(Integer, ForeignKey("quality_checks.id"), nullable=False, index=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False, index=True)
    
    # Rework Details
    rework_reason = Column(Text, nullable=False)
    defect_description = Column(Text, nullable=True)
    assigned_department = Column(String, nullable=False)  # Repair, Production, etc.
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)  # Supervisor/Manager
    target_completion_date = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String, default="pending", nullable=False)  # pending, in_progress, completed, cancelled
    
    # Completion Info
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)
    
    # Re-QC Info
    re_qc_required = Column(Boolean, default=True, nullable=False)
    re_qc_id = Column(Integer, ForeignKey("quality_checks.id"), nullable=True)  # Link to re-inspection QC
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    quality_check = relationship("QualityCheck", foreign_keys=[quality_check_id], back_populates="rework_jobs", overlaps="rework_jobs")
    production_paper = relationship("ProductionPaper")
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    completed_by_user = relationship("User", foreign_keys=[completed_by])
    created_by_user = relationship("User", foreign_keys=[created_by])


class QCCertificate(Base):
    __tablename__ = "qc_certificates"

    id = Column(Integer, primary_key=True, index=True)
    certificate_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated like "QCCERT001"
    quality_check_id = Column(Integer, ForeignKey("quality_checks.id"), nullable=False, index=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False)
    
    # Certificate Details
    product_details = Column(JSON, nullable=True)  # Product information
    inspection_date = Column(DateTime(timezone=True), nullable=False)
    inspector_name = Column(String, nullable=False)
    inspector_signature = Column(Text, nullable=True)  # Base64 or path to signature image
    
    # Certificate Status
    is_approved = Column(Boolean, default=True, nullable=False)
    certificate_pdf_path = Column(String, nullable=True)  # Path to generated PDF
    
    # Mandatory for specific products
    is_mandatory = Column(Boolean, default=False, nullable=False)  # For safety doors, fire-rated doors, etc.
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    quality_check = relationship("QualityCheck")

