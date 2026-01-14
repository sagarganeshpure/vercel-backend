from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # user, production_manager, admin
    profile_image = Column(Text, nullable=True)  # Base64 encoded image or URL
    is_active = Column(Boolean, default=True)
    # Serial number fields for Measurement Captain users
    serial_number_prefix = Column(String, nullable=True, index=True)  # Letter prefix (A, B, C, etc.) - unique per Measurement Captain
    serial_number_counter = Column(Integer, default=0, nullable=False)  # Current counter for serial numbers
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    measurements = relationship("Measurement", foreign_keys="Measurement.created_by", back_populates="created_by_user")
    parties = relationship("Party", back_populates="created_by_user")
    production_papers = relationship("ProductionPaper", back_populates="created_by_user")
    production_schedules = relationship("ProductionSchedule", back_populates="scheduled_by_user")
    supervisor_profile = relationship("ProductionSupervisor", back_populates="user", uselist=False)
    reported_issues = relationship("ProductionIssue", back_populates="reporter")
    task_progress_updates = relationship("TaskProgress", back_populates="updater")
    production_tracking_created = relationship("ProductionTracking", foreign_keys="ProductionTracking.created_by", back_populates="created_by_user")
    production_tracking_supervised = relationship("ProductionTracking", foreign_keys="ProductionTracking.supervisor_id", back_populates="supervisor")
    assigned_measurement_tasks = relationship("MeasurementTask", foreign_keys="MeasurementTask.assigned_to", back_populates="assigned_to_user")
    created_measurement_tasks = relationship("MeasurementTask", foreign_keys="MeasurementTask.assigned_by", back_populates="assigned_by_user")
    measurement_entries = relationship("MeasurementEntry", back_populates="created_by_user")


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    measurement_type = Column(String, nullable=False)  # frame_sample, shutter_sample, regular_frame, regular_shutter
    measurement_number = Column(String, nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    party_name = Column(String, nullable=True)  # Store party name for reference
    thickness = Column(String, nullable=True)  # Thickness value
    measurement_date = Column(DateTime(timezone=True), nullable=True)
    site_location = Column(String, nullable=True)  # Site location from party's site addresses
    items = Column(Text, nullable=False)  # JSON string - Array of measurement items/rows
    notes = Column(Text, nullable=True)  # Additional notes
    approval_status = Column(String, nullable=False, default="approved", index=True)  # approved, pending_approval, rejected
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)  # Soft delete flag
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # When it was deleted
    deletion_reason = Column(Text, nullable=True)  # Reason for deletion
    
    # Fields from MeasurementEntry for unification
    external_foam_patti = Column(String, nullable=True)  # e.g., "18 MM EXTERNAL FOAM PATTI @ BOTTAM SIDE"
    measurement_time = Column(String, nullable=True)  # e.g., "05:15 PM"
    task_id = Column(Integer, ForeignKey("measurement_tasks.id"), nullable=True, index=True)  # Link to measurement task
    status = Column(String, default="draft", nullable=False)  # draft, completed, sent_to_production (internal workflow)
    metadata_json = Column(Text, nullable=True)  # JSON field for additional MeasurementEntry-specific data (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    rejection_reason = Column(Text, nullable=True)  # Reason when approval_status='rejected'
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who approved/rejected
    approved_at = Column(DateTime(timezone=True), nullable=True)  # When approved/rejected
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Edit tracking fields
    last_edit_remark = Column(Text, nullable=True)  # Reason for the last edit
    last_edited_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who made the last edit
    last_edited_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp of last edit
    
    created_by_user = relationship("User", foreign_keys=[created_by], back_populates="measurements")
    last_edited_by_user = relationship("User", foreign_keys=[last_edited_by])
    party = relationship("Party")
    measurement_task = relationship("MeasurementTask", foreign_keys=[task_id])
    approver_user = relationship("User", foreign_keys=[approved_by])


class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    # Basic Party Information (Mandatory)
    party_type = Column(String, nullable=False)  # Builder, Developer, Contractor, Architect, Individual Customer
    name = Column(String, nullable=False, unique=True, index=True)  # Legal/Registered Name
    display_name = Column(String, nullable=True)  # Short name used internally
    customer_code = Column(String, nullable=True, unique=True, index=True)  # Auto-generated
    business_type = Column(String, nullable=True)  # Proprietorship, Partnership, Pvt Ltd, LLP, Individual
    
    # Contact Person Details (JSON for multiple contacts)
    contact_persons = Column(Text, nullable=True)  # JSON array of contacts
    
    # Address Details
    # Office/Registered Address
    office_address_line1 = Column(String, nullable=True)
    office_address_line2 = Column(String, nullable=True)
    office_area = Column(String, nullable=True)
    office_city = Column(String, nullable=True)
    office_state = Column(String, nullable=True)
    office_pin_code = Column(String, nullable=True)
    office_country = Column(String, nullable=True, default="India")
    
    # Site Address (Optional)
    site_addresses = Column(Text, nullable=True)  # JSON array of site addresses
    
    # Tax & Compliance Details
    gst_registration_type = Column(String, nullable=True)  # Registered, Unregistered, Composition
    gstin_number = Column(String, nullable=True, index=True)
    pan_number = Column(String, nullable=True, index=True)
    state_code = Column(String, nullable=True)  # Auto from GST
    msme_udyam_number = Column(String, nullable=True)
    
    # Business & Sales Information
    customer_category = Column(String, nullable=True)  # Premium Builder, Regular Builder, Architect, Walk-in
    industry_type = Column(String, nullable=True)  # Residential, Commercial, Mixed Projects
    estimated_monthly_volume = Column(String, nullable=True)
    estimated_yearly_volume = Column(String, nullable=True)
    price_category = Column(String, nullable=True)  # Retail, Builder Price, Special Contract Price
    assigned_sales_executive = Column(String, nullable=True)
    marketing_source = Column(String, nullable=True)  # Cold Visit, Reference, Architect, Existing Client
    
    # Credit & Payment Terms
    payment_terms = Column(String, nullable=True)  # Advance, 50% Advance – 50% Delivery, Credit
    credit_limit = Column(String, nullable=True)
    credit_days = Column(Integer, nullable=True)
    security_cheque_pdc = Column(Boolean, nullable=True, default=False)
    
    # Logistic & Dispatch Preferences
    preferred_delivery_location = Column(String, nullable=True)  # Factory Pickup, Site Delivery
    unloading_responsibility = Column(String, nullable=True)  # Company, Customer
    working_hours_at_site = Column(String, nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Product & Design Preferences (JSON)
    product_preferences = Column(Text, nullable=True)  # JSON: preferred_door_type, laminate_brands, standard_sizes, hardware_preferences
    
    # Documents (JSON array of document references)
    documents = Column(Text, nullable=True)  # JSON array of document metadata
    
    # Client Requirements (JSON)
    frame_requirements = Column(Text, nullable=True)  # JSON array of frame requirements
    door_requirements = Column(Text, nullable=True)  # JSON array of door/shutter requirements
    
    # Approval & Status Control
    customer_status = Column(String, nullable=True, default="Prospect")  # Prospect, Active, On Hold, Blacklisted
    approval_status = Column(String, nullable=True, default="Draft")  # Draft, Submitted, Approved
    
    # Legacy fields (keeping for backward compatibility)
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    created_by_user = relationship("User", back_populates="parties")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String, unique=True, index=True, nullable=False)
    product_category = Column(String, nullable=False)  # Door, Frame
    product_type = Column(String, nullable=False)  # Main Door Shutter, Bedroom Door Shutter, etc.
    sub_type = Column(String, nullable=True)  # Veneer Post Form, Laminated Post Form, etc.
    variant = Column(String, nullable=True)  # One Side Round Edge, Both Side Round Edge, etc.
    
    # Product Specifications
    description = Column(Text, nullable=True)
    specifications = Column(Text, nullable=True)  # JSON: {thickness, dimensions, etc.}
    manufacturing_process = Column(Text, nullable=True)  # JSON: array of stages
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User")
    production_tracking = relationship("ProductionTracking", back_populates="product")


class ManufacturingStage(Base):
    """Manufacturing Stage Master - Reusable stages for manufacturing processes"""
    __tablename__ = "manufacturing_stages"

    id = Column(Integer, primary_key=True, index=True)
    stage_name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User")


class Design(Base):
    """Design Master - Product designs for doors/shutters"""
    __tablename__ = "designs"

    id = Column(Integer, primary_key=True, index=True)
    design_name = Column(String, unique=True, index=True, nullable=False)
    design_code = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image = Column(Text, nullable=True)  # Base64 encoded image
    product_category = Column(String, default="Shutter", nullable=False)  # Shutter, Frame
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User")


class ProductionPaper(Base):
    __tablename__ = "production_papers"

    id = Column(Integer, primary_key=True, index=True)
    paper_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated
    # po_number = Column(String, nullable=True, index=True)  # Purchase Order Number - Temporarily commented out
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    party_name = Column(String, nullable=True)  # Store party name for reference
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=True)
    project_site_name = Column(String, nullable=True)
    
    # Order Details
    order_type = Column(String, nullable=False, default="Regular")  # Urgent, Regular, Sample
    product_category = Column(String, nullable=False)  # Door, Frame
    product_type = Column(String, nullable=True)  # Main Door Shutter, etc.
    product_sub_type = Column(String, nullable=True)  # Veneer Post Form, etc.
    
    # Dates
    expected_dispatch_date = Column(Date, nullable=True)
    production_start_date = Column(Date, nullable=True)
    
    # Status
    status = Column(String, default="draft", nullable=False)  # draft, active, in_production, ready_for_dispatch, dispatched, delivered, completed
    
    # Material Availability (Auto-checked)
    shutter_available = Column(Boolean, default=False)
    laminate_available = Column(Boolean, default=False)
    frame_material_available = Column(Boolean, default=False)
    raw_material_check_date = Column(DateTime(timezone=True), nullable=True)
    
    # Additional Fields
    title = Column(String, nullable=True)  # Keep for backward compatibility
    description = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    
    # Site and Product Details
    site_name = Column(String, nullable=True)
    site_location = Column(String, nullable=True)
    area = Column(String, nullable=True)  # MD/BED/BATH/DRB/FRD
    concept = Column(String, nullable=True)  # BSL PF/ONE EDGE PF/BSL/FRP/FRP+OSL(RP)/GEL+OSL (RP)/OSL PF+GEL
    thickness = Column(String, nullable=True)  # 55MM/45MM/40MM/35MM/32MM
    design = Column(String, nullable=True)
    frontside_design = Column(String, nullable=True)
    backside_design = Column(String, nullable=True)
    gel_colour = Column(String, nullable=True)
    laminate = Column(String, nullable=True)
    core = Column(String, nullable=True)
    remark = Column(Text, nullable=True)
    
    # Frame-specific fields
    total_quantity = Column(String, nullable=True)
    wall_type = Column(String, nullable=True)
    rebate = Column(String, nullable=True)
    sub_frame = Column(String, nullable=True)
    construction = Column(String, nullable=True)
    cover_moulding = Column(String, nullable=True)
    
    # Shutter-specific fields
    frontside_laminate = Column(String, nullable=True)
    backside_laminate = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    side_frame = Column(String, nullable=True)
    filler = Column(String, nullable=True)
    foam_bottom = Column(String, nullable=True)
    frp_coating = Column(String, nullable=True)
    
    selected_measurement_items = Column(Text, nullable=True)  # JSON array of selected item indices [0, 2, 5]
    
    # Client Requirement Reference (to track which requirement was used)
    client_requirement_party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    client_requirement_type = Column(String, nullable=True)  # "frame" or "door"
    client_requirement_index = Column(Integer, nullable=True)  # Index in the requirements array
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Soft Delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)  # Soft delete flag
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # When it was deleted
    deletion_reason = Column(Text, nullable=True)  # Reason for deletion
    
    # Relationships
    created_by_user = relationship("User", back_populates="production_papers")
    party = relationship("Party", foreign_keys=[party_id])
    measurement = relationship("Measurement")
    production_schedules = relationship("ProductionSchedule", back_populates="production_paper")
    production_tracking = relationship("ProductionTracking", back_populates="production_paper")


class ProductionSchedule(Base):
    __tablename__ = "production_schedules"

    id = Column(Integer, primary_key=True, index=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    
    # Production Plan
    production_start_date = Column(Date, nullable=False)
    target_completion_date = Column(Date, nullable=False)
    priority = Column(String, default="Normal", nullable=False)  # High, Normal, Low
    
    # Department-wise Scheduling (JSON)
    department_schedule = Column(Text, nullable=True)  # JSON: [{department, supervisor, planned_start, planned_end}]
    
    # Supervisor Assignment
    primary_supervisor = Column(String, nullable=True)
    backup_supervisor = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="Scheduled", nullable=False)  # Scheduled, In Production, On Hold, Completed, Cancelled
    
    # Material Checks (read-only from system)
    measurement_received = Column(Boolean, default=False)
    production_paper_approved = Column(Boolean, default=False)
    shutter_available = Column(Boolean, default=False)
    laminate_available = Column(Boolean, default=False)
    frame_material_available = Column(Boolean, default=False)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    scheduled_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper", back_populates="production_schedules")
    scheduled_by_user = relationship("User", back_populates="production_schedules")
    production_tasks = relationship("ProductionTask", back_populates="schedule")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # Sanding, Cutting, Round Edge, etc.
    code = Column(String, unique=True, nullable=True, index=True)  # Optional code
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    supervisors = relationship("ProductionSupervisor", back_populates="department")
    tasks = relationship("ProductionTask", back_populates="department")


class ProductionSupervisor(Base):
    __tablename__ = "production_supervisors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    supervisor_type = Column(String, nullable=False, index=True)  # Loading & Unloading, Sanding, Cutting, Laminate, Grooving, Frame
    shift = Column(String, nullable=True)  # Morning, Evening, Night
    is_active = Column(Boolean, default=True, nullable=False)
    backup_supervisor_id = Column(Integer, ForeignKey("production_supervisors.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    department = relationship("Department", back_populates="supervisors")
    backup_supervisor = relationship("ProductionSupervisor", remote_side=[id], foreign_keys=[backup_supervisor_id])
    tasks = relationship("ProductionTask", back_populates="supervisor")


class ProductionTask(Base):
    __tablename__ = "production_tasks"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("production_schedules.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    supervisor_id = Column(Integer, ForeignKey("production_supervisors.id"), nullable=True, index=True)
    supervisor_type = Column(String, nullable=True, index=True)  # Type of supervisor required for this task
    
    # Task Details
    production_paper_no = Column(String, nullable=False, index=True)
    party_name = Column(String, nullable=True)
    product_type = Column(String, nullable=True)  # Door, Frame
    order_type = Column(String, nullable=True)  # Urgent, Regular, Sample
    quantity = Column(Integer, nullable=False, default=0)
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    
    # Status & Progress
    status = Column(String, default="Pending", nullable=False)  # Pending, Accepted, In Progress, On Hold, Completed, Rejected
    start_time = Column(DateTime(timezone=True), nullable=True)
    expected_end_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    quantity_completed = Column(Integer, default=0, nullable=False)
    balance_quantity = Column(Integer, nullable=False)
    rework_qty = Column(Integer, default=0, nullable=False)
    
    # Rejection/On Hold
    rejection_reason = Column(Text, nullable=True)  # Material, Machine, Manpower
    on_hold_reason = Column(Text, nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    resumed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Quality
    quality_status = Column(String, nullable=True)  # Pass, Fail, Pending
    
    # Audit
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    schedule = relationship("ProductionSchedule", back_populates="production_tasks")
    department = relationship("Department", back_populates="tasks")
    supervisor = relationship("ProductionSupervisor", back_populates="tasks")
    issues = relationship("ProductionIssue", back_populates="task")
    progress_updates = relationship("TaskProgress", back_populates="task")


class ProductionIssue(Base):
    __tablename__ = "production_issues"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("production_tasks.id"), nullable=False, index=True)
    production_paper_no = Column(String, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    
    # Issue Details
    issue_type = Column(String, nullable=False)  # Material Shortage, Machine Breakdown, Quality Issue, Manpower Issue, Design/Measurement Issue
    description = Column(Text, nullable=False)
    photo_url = Column(Text, nullable=True)  # URL or base64
    severity = Column(String, nullable=False)  # Critical, High, Medium
    affected_quantity = Column(Integer, nullable=True)
    
    # Status & Resolution
    status = Column(String, default="Open", nullable=False)  # Open, Assigned, In Progress, Resolved, Closed
    assigned_to = Column(String, nullable=True)  # Purchase, Store, Maintenance Captain, QC, Engineering
    resolution_remarks = Column(Text, nullable=True)
    downtime_hours = Column(Float, nullable=True)
    
    # Audit
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    task = relationship("ProductionTask", back_populates="issues")
    department = relationship("Department")
    reporter = relationship("User")


class TaskProgress(Base):
    __tablename__ = "task_progress"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("production_tasks.id"), nullable=False, index=True)
    quantity_completed = Column(Integer, nullable=False)
    rework_qty = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("ProductionTask", back_populates="progress_updates")
    updater = relationship("User")


class ProductionTracking(Base):
    __tablename__ = "production_tracking"

    id = Column(Integer, primary_key=True, index=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_type = Column(String, nullable=False)  # Door, Frame
    product_category = Column(String, nullable=True)  # Main Door Shutter, etc.
    
    # Stage Information
    stage_name = Column(String, nullable=False)  # Material Unloading, Sanding, Cutting, etc.
    stage_sequence = Column(Integer, nullable=False)  # Order of stages (1, 2, 3, ...)
    
    # Timing
    start_date_time = Column(DateTime(timezone=True), nullable=True)
    end_date_time = Column(DateTime(timezone=True), nullable=True)
    estimated_duration_hours = Column(Float, nullable=True)
    actual_duration_hours = Column(Float, nullable=True)
    
    # Supervisor Information
    supervisor_name = Column(String, nullable=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status
    status = Column(String, default="Pending", nullable=False)  # Pending, In Progress, Completed, On Hold
    
    # Quality & Rework
    rework_flag = Column(Boolean, default=False, nullable=False)
    rework_reason = Column(Text, nullable=True)
    quality_status = Column(String, nullable=True)  # Pass, Fail, Pending
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper", back_populates="production_tracking")
    product = relationship("Product", back_populates="production_tracking")
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    created_by_user = relationship("User", foreign_keys=[created_by])


class MeasurementTask(Base):
    """Tasks assigned to Measurement Captain by Site Supervisor or Sales/Marketing"""
    __tablename__ = "measurement_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated
    
    # Task Assignment
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Measurement Captain
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Site Supervisor or Sales/Marketing
    
    # Project/Party Information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    party_name = Column(String, nullable=False)
    project_site_name = Column(String, nullable=True)
    site_address = Column(Text, nullable=True)
    
    # Task Details
    task_description = Column(Text, nullable=True)
    priority = Column(String, default="Normal", nullable=False)  # High, Normal, Low
    status = Column(String, default="assigned", nullable=False)  # assigned, in_progress, completed, cancelled
    due_date = Column(Date, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    assigned_to_user = relationship("User", foreign_keys=[assigned_to])
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    party = relationship("Party")
    measurement_entry = relationship("MeasurementEntry", back_populates="task", uselist=False)


class MeasurementEntry(Base):
    """Measurement entries created by Measurement Captain"""
    __tablename__ = "measurement_entries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Task Reference
    task_id = Column(Integer, ForeignKey("measurement_tasks.id"), nullable=True, index=True)
    
    # Measurement Header Information (matching image structure)
    measurement_number = Column(String, unique=True, index=True, nullable=False)  # PG-XXX/DD.MM.YYYY
    category = Column(String, nullable=True)  # Sample Frame, Sample Shutter, Regular Frame, Regular Shutter
    party_name = Column(String, nullable=False)
    thickness = Column(String, nullable=True)  # e.g., "35 MM"
    external_foam_patti = Column(String, nullable=True)  # e.g., "18 MM EXTERNAL FOAM PATTI @ BOTTAM SIDE"
    measurement_date = Column(DateTime(timezone=True), nullable=True)
    measurement_time = Column(String, nullable=True)  # e.g., "05:15 PM"
    
    # Measurement Table Data (JSON array of rows)
    measurement_items = Column(Text, nullable=False)  # JSON array matching the table structure
    
    # Status & Integration
    status = Column(String, default="draft", nullable=False)  # draft, completed, sent_to_production
    sent_to_production_at = Column(DateTime(timezone=True), nullable=True)
    production_measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=True)  # Link to production measurement
    
    # Additional Notes
    notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    task = relationship("MeasurementTask", foreign_keys=[task_id], back_populates="measurement_entry")
    created_by_user = relationship("User", foreign_keys=[created_by])
    production_measurement = relationship("Measurement")


class PartyHistory(Base):
    """Track changes to party order details"""
    __tablename__ = "party_history"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    
    # Changed field information
    field_name = Column(String, nullable=False)  # e.g., "payment_terms", "credit_limit"
    old_value = Column(Text, nullable=True)  # Previous value
    new_value = Column(Text, nullable=True)  # New value
    
    # Change metadata
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    change_reason = Column(Text, nullable=True)  # Optional reason for the change
    
    # Relationships
    party = relationship("Party")
    changed_by_user = relationship("User", foreign_keys=[changed_by])
