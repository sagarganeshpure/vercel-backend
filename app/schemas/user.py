from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, List, Dict, Union
from datetime import datetime, date

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    role: str = Field(default="user", pattern='^(user|production_manager|raw_material_checker|production_scheduler|production_supervisor|quality_checker|crm_manager|marketing_executive|sales_executive|sales_manager|billing_executive|accounts_manager|accounts_executive|finance_head|auditor|dispatch_executive|dispatch_supervisor|logistics_manager|logistics_executive|driver|site_supervisor|carpenter_captain|purchase_executive|purchase_manager|store_incharge|measurement_captain|admin)$')

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserInDBBase(UserBase):
    id: int
    is_active: bool
    profile_image: Optional[str] = None
    serial_number_prefix: Optional[str] = None  # Letter prefix for Measurement Captain users (A, B, C, etc.)
    serial_number_counter: Optional[int] = 0  # Current counter for serial numbers
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic V2 syntax (replaces orm_mode)

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str

class UserProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = None


# Production Docs Schemas
class MeasurementItem(BaseModel):
    """Single row/item in a measurement document"""
    sr_no: Optional[str] = None
    location: Optional[str] = None
    location_of_fitting: Optional[str] = None
    hinges: Optional[str] = None
    bldg: Optional[str] = None
    flat_no: Optional[str] = None
    area: Optional[str] = None
    act_width: Optional[str] = None
    act_height: Optional[str] = None
    ro_width: Optional[str] = None
    ro_height: Optional[str] = None
    wall: Optional[str] = None
    subframe_side: Optional[str] = None
    sub_frame: Optional[str] = None
    h: Optional[str] = None
    w: Optional[str] = None
    qty: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    column3: Optional[str] = None
    column4: Optional[str] = None
    weidth: Optional[str] = None
    colum: Optional[str] = None
    heigh: Optional[str] = None
    # Allow additional fields
    class Config:
        extra = "allow"

class MeasurementBase(BaseModel):
    measurement_type: str = Field(..., pattern='^(frame_sample|shutter_sample|regular_frame|regular_shutter)$')
    measurement_number: Optional[str] = None  # Auto-generated if not provided
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    thickness: Optional[str] = None
    measurement_date: Optional[datetime] = None
    site_location: Optional[str] = None
    items: List[Dict[str, Any]] = Field(..., min_items=1)  # List of measurement items
    notes: Optional[str] = None
    # Fields from MeasurementEntry for unification
    external_foam_patti: Optional[str] = None
    measurement_time: Optional[str] = None
    task_id: Optional[int] = None
    status: Optional[str] = "draft"  # draft, completed, sent_to_production
    metadata: Optional[Dict[str, Any]] = None  # JSON field for additional data (maps to metadata_json in database)
    # Support category field from MeasurementEntry (maps to measurement_type)
    category: Optional[str] = None  # Will be mapped to measurement_type if provided

class MeasurementCreate(MeasurementBase):
    approval_status: Optional[str] = "approved"  # Default to approved, can be set to pending_approval by measurement_captain

class MeasurementUpdate(BaseModel):
    items: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    edit_remark: Optional[str] = None

class Measurement(MeasurementBase):
    id: int
    approval_status: Optional[str] = "approved"  # approved, pending_approval, rejected
    is_deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_username: Optional[str] = None  # Username of the user who created the measurement
    last_edit_remark: Optional[str] = None  # Reason for the last edit
    last_edited_by: Optional[int] = None  # User who made the last edit
    last_edited_at: Optional[datetime] = None  # Timestamp of last edit

    class Config:
        from_attributes = True

class MeasurementDeleteRequest(BaseModel):
    deletion_reason: str = Field(..., min_length=1, max_length=1000)


# Measurement Captain Schemas
class MeasurementTaskBase(BaseModel):
    assigned_to: int  # Measurement Captain user ID
    party_id: Optional[int] = None
    party_name: str
    project_site_name: Optional[str] = None
    site_address: Optional[str] = None
    task_description: Optional[str] = None
    priority: str = "Normal"  # High, Normal, Low
    due_date: Optional[date] = None

class MeasurementTaskCreate(MeasurementTaskBase):
    pass

class MeasurementTaskUpdate(BaseModel):
    status: Optional[str] = None
    task_description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None

class MeasurementTask(MeasurementTaskBase):
    id: int
    task_number: str
    assigned_by: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MeasurementEntryBase(BaseModel):
    task_id: Optional[int] = None
    measurement_number: str  # PG-XXX/DD.MM.YYYY
    category: Optional[str] = None  # Sample Frame, Sample Shutter, Regular Frame, Regular Shutter
    party_name: str
    thickness: Optional[str] = None
    external_foam_patti: Optional[str] = None
    measurement_date: Optional[datetime] = None
    measurement_time: Optional[str] = None
    measurement_items: List[Dict[str, Any]] = Field(..., min_items=1)  # JSON array of table rows
    notes: Optional[str] = None

class MeasurementEntryCreate(MeasurementEntryBase):
    pass

class MeasurementEntryUpdate(BaseModel):
    category: Optional[str] = None
    measurement_items: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class MeasurementEntry(MeasurementEntryBase):
    id: int
    status: str
    sent_to_production_at: Optional[datetime] = None
    production_measurement_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Contact Person schema
class ContactPerson(BaseModel):
    name: str
    designation: Optional[str] = None  # Owner, Purchase Manager, Site Engineer, Project Manager
    mobile_number: Optional[str] = None
    email: Optional[str] = None

# Site Address schema
class SiteAddress(BaseModel):
    project_site_name: Optional[str] = None
    site_address: Optional[str] = None
    site_contact_person: Optional[str] = None
    site_mobile_no: Optional[str] = None

# Product Preferences schema
class ProductPreferences(BaseModel):
    preferred_door_type: Optional[str] = None  # Flush, Designer, Laminate
    preferred_laminate_brands: Optional[str] = None
    standard_sizes_used: Optional[str] = None
    hardware_preferences: Optional[str] = None

# Document schema
class Document(BaseModel):
    type: str  # GST Certificate, PAN Card, Visiting Card, Company Registration, Signed Agreement
    filename: Optional[str] = None
    url: Optional[str] = None

class PartyBase(BaseModel):
    # Basic Party Information (Mandatory)
    party_type: str  # Builder, Developer, Contractor, Architect, Individual Customer
    name: str  # Legal/Registered Name
    display_name: Optional[str] = None
    customer_code: Optional[str] = None  # Auto-generated
    business_type: Optional[str] = None  # Proprietorship, Partnership, Pvt Ltd, LLP, Individual
    
    # Contact Person Details
    contact_persons: Optional[List[ContactPerson]] = None
    
    # Address Details
    office_address_line1: Optional[str] = None
    office_address_line2: Optional[str] = None
    office_area: Optional[str] = None
    office_city: Optional[str] = None
    office_state: Optional[str] = None
    office_pin_code: Optional[str] = None
    office_country: Optional[str] = "India"
    site_addresses: Optional[List[SiteAddress]] = None
    
    # Tax & Compliance Details
    gst_registration_type: Optional[str] = None  # Registered, Unregistered, Composition
    gstin_number: Optional[str] = None
    pan_number: Optional[str] = None
    state_code: Optional[str] = None
    msme_udyam_number: Optional[str] = None
    
    # Business & Sales Information
    customer_category: Optional[str] = None  # Premium Builder, Regular Builder, Architect, Walk-in
    industry_type: Optional[str] = None  # Residential, Commercial, Mixed Projects
    estimated_monthly_volume: Optional[str] = None
    estimated_yearly_volume: Optional[str] = None
    price_category: Optional[str] = None  # Retail, Builder Price, Special Contract Price
    assigned_sales_executive: Optional[str] = None
    marketing_source: Optional[str] = None  # Cold Visit, Reference, Architect, Existing Client
    
    # Credit & Payment Terms
    payment_terms: Optional[str] = None  # Advance, 50% Advance – 50% Delivery, Credit
    credit_limit: Optional[str] = None
    credit_days: Optional[int] = None
    security_cheque_pdc: Optional[bool] = False
    
    # Logistic & Dispatch Preferences
    preferred_delivery_location: Optional[str] = None  # Factory Pickup, Site Delivery
    unloading_responsibility: Optional[str] = None  # Company, Customer
    working_hours_at_site: Optional[str] = None
    special_instructions: Optional[str] = None
    
    # Product & Design Preferences
    product_preferences: Optional[ProductPreferences] = None
    
    # Documents
    documents: Optional[List[Document]] = None
    
    # Client Requirements (JSON - array of requirement objects)
    frame_requirements: Optional[List[Dict[str, Any]]] = None
    door_requirements: Optional[List[Dict[str, Any]]] = None
    
    # Approval & Status Control
    customer_status: Optional[str] = "Prospect"  # Prospect, Active, On Hold, Blacklisted
    approval_status: Optional[str] = "Draft"  # Draft, Submitted, Approved
    
    # Legacy fields (for backward compatibility)
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class PartyCreate(PartyBase):
    pass

class Party(PartyBase):
    id: int
    created_by: int
    created_by_username: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PartyOrderDetailsUpdate(BaseModel):
    """Update order details for a party"""
    payment_terms: Optional[str] = None
    credit_limit: Optional[str] = None
    credit_days: Optional[int] = None
    security_cheque_pdc: Optional[bool] = None
    preferred_delivery_location: Optional[str] = None
    unloading_responsibility: Optional[str] = None
    working_hours_at_site: Optional[str] = None
    special_instructions: Optional[str] = None
    change_reason: Optional[str] = None


class PartyClientRequirementsUpdate(BaseModel):
    """Update client requirements (frame and door requirements) for a party"""
    frame_requirements: Optional[str] = None  # JSON string
    door_requirements: Optional[str] = None  # JSON string
    special_instructions: Optional[str] = None  # Text string
    customer_status: Optional[str] = None  # Purchase Order Status
    documents: Optional[str] = None  # JSON string array of documents


class PartyHistoryEntry(BaseModel):
    """Single history entry for party changes"""
    id: int
    party_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: int
    changed_by_username: Optional[str] = None
    changed_at: datetime
    change_reason: Optional[str] = None

    class Config:
        from_attributes = True


class ProductionPaperBase(BaseModel):
    paper_number: Optional[str] = None  # Auto-generated if not provided
    # po_number: Optional[str] = None  # Temporarily commented out
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    measurement_id: Optional[int] = None
    project_site_name: Optional[str] = None
    order_type: str = "Regular"  # Urgent, Regular, Sample
    product_category: str  # Door, Frame
    product_type: Optional[str] = None
    product_sub_type: Optional[str] = None
    expected_dispatch_date: Optional[datetime] = None
    production_start_date: Optional[datetime] = None
    status: str = "draft"  # draft, active, in_production, ready_for_dispatch, dispatched, delivered, completed
    title: Optional[str] = None  # Keep for backward compatibility
    description: Optional[str] = None
    remarks: Optional[str] = None
    # Site and Product Details
    site_name: Optional[str] = None
    site_location: Optional[str] = None
    area: Optional[str] = None  # MD/BED/BATH/DRB/FRD
    concept: Optional[str] = None  # BSL PF/ONE EDGE PF/BSL/FRP/FRP+OSL(RP)/GEL+OSL (RP)/OSL PF+GEL
    thickness: Optional[str] = None  # 55MM/45MM/40MM/35MM/32MM
    design: Optional[str] = None
    frontside_design: Optional[str] = None
    backside_design: Optional[str] = None
    gel_colour: Optional[str] = None
    laminate: Optional[str] = None
    core: Optional[str] = None
    remark: Optional[str] = None
    
    # Frame-specific fields
    total_quantity: Optional[str] = None
    wall_type: Optional[str] = None
    rebate: Optional[str] = None
    sub_frame: Optional[str] = None
    construction: Optional[str] = None
    cover_moulding: Optional[str] = None
    
    # Shutter-specific fields
    frontside_laminate: Optional[str] = None
    backside_laminate: Optional[str] = None
    grade: Optional[str] = None
    side_frame: Optional[str] = None
    filler: Optional[str] = None
    foam_bottom: Optional[str] = None
    frp_coating: Optional[str] = None
    
    selected_measurement_items: Optional[Any] = None  # Array of selected item indices [0, 2, 5] OR array of objects [{measurement_id, item_index, item_type}]. Validation handled in endpoint.
    # Client Requirement Reference
    client_requirement_type: Optional[str] = None  # "frame" or "door"
    client_requirement_index: Optional[int] = None  # Index in the requirements array

class ProductionPaperCreate(ProductionPaperBase):
    pass

class ProductionPaperParty(BaseModel):
    id: int
    name: str

class ProductionPaperMeasurement(BaseModel):
    id: int
    measurement_number: str
    party_name: Optional[str] = None

class ProductionPaper(ProductionPaperBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: Optional[bool] = False
    deleted_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None
    party: Optional[ProductionPaperParty] = None
    measurement: Optional[ProductionPaperMeasurement] = None

    class Config:
        from_attributes = True


class ProductionPaperDeleteRequest(BaseModel):
    deletion_reason: Optional[str] = None


# Manufacturing Stage Schemas
class ManufacturingStageBase(BaseModel):
    stage_name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True

class ManufacturingStageCreate(ManufacturingStageBase):
    pass

class ManufacturingStageUpdate(BaseModel):
    stage_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ManufacturingStage(ManufacturingStageBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Design Schemas
class DesignBase(BaseModel):
    design_name: str
    design_code: str
    description: Optional[str] = None
    image: Optional[str] = None  # Base64 encoded image
    product_category: Optional[str] = "Shutter"

class DesignCreate(DesignBase):
    pass

class DesignUpdate(BaseModel):
    design_name: Optional[str] = None
    design_code: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    product_category: Optional[str] = None
    is_active: Optional[bool] = None

class Design(DesignBase):
    id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Product Schemas
class ManufacturingProcessStep(BaseModel):
    step_name: str  # This will be the stage_name from ManufacturingStage
    time_hours: Optional[float] = None
    duration_unit: Optional[str] = 'hours'  # 'hours' or 'days'
    sequence: Optional[int] = None

class ProductBase(BaseModel):
    product_code: str
    product_category: str  # Door, Frame
    product_type: str  # Main Door Shutter, Bedroom Door Shutter, etc.
    sub_type: Optional[str] = None  # Veneer Post Form, Laminated Post Form, etc.
    variant: Optional[str] = None  # One Side Round Edge, Both Side Round Edge, etc.
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    manufacturing_process: Optional[List[ManufacturingProcessStep]] = None

class ProductCreate(BaseModel):
    product_code: Optional[str] = None  # Auto-generated if not provided
    product_category: str  # Door, Frame
    product_type: str  # Main Door Shutter, Bedroom Door Shutter, etc.
    sub_type: Optional[str] = None  # Veneer Post Form, Laminated Post Form, etc.
    variant: Optional[str] = None  # One Side Round Edge, Both Side Round Edge, etc.
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    manufacturing_process: Optional[List[ManufacturingProcessStep]] = None

class ProductUpdate(BaseModel):
    product_code: Optional[str] = None
    product_category: Optional[str] = None
    product_type: Optional[str] = None
    sub_type: Optional[str] = None
    variant: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    manufacturing_process: Optional[List[ManufacturingProcessStep]] = None

class Product(ProductBase):
    id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Production Tracking Schemas
class ProductionTrackingBase(BaseModel):
    production_paper_id: int
    production_paper_number: str
    product_id: Optional[int] = None
    product_type: str  # Door, Frame
    product_category: Optional[str] = None
    stage_name: str
    stage_sequence: int
    start_date_time: Optional[datetime] = None
    end_date_time: Optional[datetime] = None
    estimated_duration_hours: Optional[float] = None
    actual_duration_hours: Optional[float] = None
    supervisor_name: Optional[str] = None
    supervisor_id: Optional[int] = None
    status: str = "Pending"  # Pending, In Progress, Completed, On Hold
    rework_flag: bool = False
    rework_reason: Optional[str] = None
    quality_status: Optional[str] = None
    remarks: Optional[str] = None

class ProductionTrackingCreate(ProductionTrackingBase):
    pass

class ProductionTracking(ProductionTrackingBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Raw Material Checker Schemas
class RawMaterialCategoryBase(BaseModel):
    name: str
    code: Optional[str] = None  # Auto-generated if not provided
    description: Optional[str] = None
    is_active: bool = True

class RawMaterialCategoryCreate(RawMaterialCategoryBase):
    pass

class RawMaterialCategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class RawMaterialCategory(RawMaterialCategoryBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str
    code: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    gstin_number: Optional[str] = None
    pan_number: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_days: Optional[int] = None
    is_active: bool = True
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class Supplier(SupplierBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RawMaterialCheckBase(BaseModel):
    check_number: Optional[str] = None  # Auto-generated
    production_paper_id: Optional[int] = None
    party_id: Optional[int] = None
    supplier_id: Optional[int] = None
    category_id: Optional[int] = None
    product_name: str
    quantity: float
    unit: str = "pcs"
    status: str = "pending"  # pending, work_in_progress, approved
    checked_by: Optional[int] = None
    checked_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None

class RawMaterialCheckCreate(RawMaterialCheckBase):
    pass

class RawMaterialCheck(RawMaterialCheckBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional['RawMaterialCategory'] = None

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    order_number: Optional[str] = None  # Auto-generated
    raw_material_check_id: Optional[int] = None
    supplier_id: int
    category_id: Optional[int] = None
    product_name: str
    quantity: float
    unit: str = "pcs"
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    status: str = "pending"  # pending, ordered, in_transit, delivered, completed, cancelled
    order_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional['RawMaterialCategory'] = None

    class Config:
        from_attributes = True


class ProductSupplierMappingBase(BaseModel):
    product_name: str
    supplier_id: int
    priority: int = 1  # 1 = primary, 2 = secondary, etc.
    is_active: bool = True
    notes: Optional[str] = None

class ProductSupplierMappingCreate(ProductSupplierMappingBase):
    pass

class ProductSupplierMapping(ProductSupplierMappingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Production Scheduler Schemas
class DepartmentScheduleItem(BaseModel):
    department: str  # Sanding, Cutting, Pressing, Finishing
    supervisor: Optional[str] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None

class ProductionScheduleBase(BaseModel):
    production_paper_id: int
    production_start_date: datetime
    target_completion_date: datetime
    priority: str = "Normal"  # High, Normal, Low
    department_schedule: Optional[List[DepartmentScheduleItem]] = None
    primary_supervisor: Optional[str] = None
    backup_supervisor: Optional[str] = None
    remarks: Optional[str] = None

class ProductionScheduleCreate(ProductionScheduleBase):
    pass

class ProductionScheduleUpdate(BaseModel):
    production_start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    priority: Optional[str] = None
    department_schedule: Optional[List[DepartmentScheduleItem]] = None
    primary_supervisor: Optional[str] = None
    backup_supervisor: Optional[str] = None
    status: Optional[str] = None  # Scheduled, In Production, On Hold, Completed, Cancelled
    remarks: Optional[str] = None
    reason_for_change: Optional[str] = None  # Required when rescheduling

class ProductionSchedule(ProductionScheduleBase):
    id: int
    status: str
    measurement_received: bool
    production_paper_approved: bool
    shutter_available: bool
    laminate_available: bool
    frame_material_available: bool
    scheduled_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Production Supervisor Schemas
class DepartmentBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    pass

class Department(DepartmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductionSupervisorBase(BaseModel):
    user_id: int
    department_id: int
    supervisor_type: str = Field(..., pattern='^(Loading & Unloading|Sanding|Cutting|Laminate|Grooving|Frame)$')
    shift: Optional[str] = None
    is_active: bool = True
    backup_supervisor_id: Optional[int] = None

class ProductionSupervisorCreate(ProductionSupervisorBase):
    pass

class ProductionSupervisorUpdate(BaseModel):
    department_id: Optional[int] = None
    supervisor_type: Optional[str] = Field(None, pattern='^(Loading & Unloading|Sanding|Cutting|Laminate|Grooving|Frame)$')
    shift: Optional[str] = None
    is_active: Optional[bool] = None
    backup_supervisor_id: Optional[int] = None

class ProductionSupervisor(ProductionSupervisorBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductionTaskBase(BaseModel):
    schedule_id: int
    department_id: int
    supervisor_id: Optional[int] = None
    supervisor_type: Optional[str] = Field(None, pattern='^(Loading & Unloading|Sanding|Cutting|Laminate|Grooving|Frame)$')
    production_paper_no: str
    party_name: Optional[str] = None
    product_type: Optional[str] = None
    order_type: Optional[str] = None
    quantity: int
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None

class ProductionTaskCreate(ProductionTaskBase):
    pass

class ProductionTaskUpdate(BaseModel):
    status: Optional[str] = None
    quantity_completed: Optional[int] = None
    rework_qty: Optional[int] = None
    start_time: Optional[datetime] = None
    expected_end_time: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    on_hold_reason: Optional[str] = None
    quality_status: Optional[str] = None

class ProductionTask(ProductionTaskBase):
    id: int
    status: str
    start_time: Optional[datetime] = None
    expected_end_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    quantity_completed: int
    balance_quantity: int
    rework_qty: int
    rejection_reason: Optional[str] = None
    on_hold_reason: Optional[str] = None
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    quality_status: Optional[str] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductionIssueBase(BaseModel):
    task_id: int
    production_paper_no: str
    department_id: int
    issue_type: str
    description: str
    photo_url: Optional[str] = None
    severity: str
    affected_quantity: Optional[int] = None

class ProductionIssueCreate(ProductionIssueBase):
    pass

class ProductionIssueUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_remarks: Optional[str] = None
    downtime_hours: Optional[float] = None

class ProductionIssue(ProductionIssueBase):
    id: int
    status: str
    assigned_to: Optional[str] = None
    resolution_remarks: Optional[str] = None
    downtime_hours: Optional[float] = None
    reported_by: int
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskProgressCreate(BaseModel):
    task_id: int
    quantity_completed: int
    rework_qty: int = 0
    notes: Optional[str] = None

class TaskProgress(BaseModel):
    id: int
    task_id: int
    quantity_completed: int
    rework_qty: int
    notes: Optional[str] = None
    updated_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Quality Check Schemas
class ChecklistItem(BaseModel):
    """Single checklist item for QC"""
    category: str  # General, Veneer/Laminate, Post Form, Safety/Fire Door, etc.
    item_name: str  # e.g., "Dimensions as per measurement"
    pass_fail: Optional[str] = None  # "pass", "fail"
    defect_type: Optional[str] = None
    remarks: Optional[str] = None


class QualityCheckBase(BaseModel):
    qc_number: Optional[str] = None  # Auto-generated
    production_paper_id: int
    production_paper_number: str
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    product_type: str  # Door, Frame
    product_category: Optional[str] = None
    product_variant: Optional[str] = None
    order_type: str  # Urgent, Regular, Sample
    total_quantity: float
    accepted_quantity: Optional[float] = 0
    rework_quantity: Optional[float] = 0
    rejected_quantity: Optional[float] = 0
    checklist_results: Optional[List[Dict[str, Any]]] = None  # Array of checklist items
    qc_status: str = "pending"  # pending, approved, rework_required, rejected
    defect_category: Optional[str] = None
    severity: Optional[str] = None  # Critical, Major, Minor
    remarks: Optional[str] = None
    photos: Optional[List[str]] = None  # Array of photo URLs/paths
    production_completed_date: Optional[datetime] = None
    supervisor_name: Optional[str] = None
    completed_stages_summary: Optional[str] = None
    inspector_id: Optional[int] = None
    inspector_name: Optional[str] = None
    inspection_date: Optional[datetime] = None
    rework_job_id: Optional[int] = None
    rework_department: Optional[str] = None
    rework_target_date: Optional[datetime] = None
    cost_impact: Optional[float] = None


class QualityCheckCreate(QualityCheckBase):
    pass


class QualityCheckUpdate(BaseModel):
    accepted_quantity: Optional[float] = None
    rework_quantity: Optional[float] = None
    rejected_quantity: Optional[float] = None
    checklist_results: Optional[List[Dict[str, Any]]] = None
    qc_status: Optional[str] = None
    defect_category: Optional[str] = None
    severity: Optional[str] = None
    remarks: Optional[str] = None
    photos: Optional[List[str]] = None
    inspector_id: Optional[int] = None
    inspector_name: Optional[str] = None
    inspection_date: Optional[datetime] = None
    cost_impact: Optional[float] = None


class QualityCheck(QualityCheckBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReworkJobBase(BaseModel):
    rework_number: Optional[str] = None  # Auto-generated
    quality_check_id: int
    production_paper_id: int
    production_paper_number: str
    rework_reason: str
    defect_description: Optional[str] = None
    assigned_department: str
    assigned_to: Optional[int] = None
    target_completion_date: Optional[datetime] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    re_qc_required: bool = True
    re_qc_id: Optional[int] = None


class ReworkJobCreate(ReworkJobBase):
    pass


class ReworkJobUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    target_completion_date: Optional[datetime] = None
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    re_qc_id: Optional[int] = None


class ReworkJob(ReworkJobBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QCCertificateBase(BaseModel):
    certificate_number: Optional[str] = None  # Auto-generated
    quality_check_id: int
    production_paper_id: int
    production_paper_number: str
    product_details: Optional[Dict[str, Any]] = None
    inspection_date: datetime
    inspector_name: str
    inspector_signature: Optional[str] = None
    is_approved: bool = True
    certificate_pdf_path: Optional[str] = None
    is_mandatory: bool = False


class QCCertificateCreate(QCCertificateBase):
    pass


class QCCertificate(QCCertificateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True