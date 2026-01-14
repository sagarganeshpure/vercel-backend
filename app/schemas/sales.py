from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


# Lead Schemas
class LeadBase(BaseModel):
    lead_type: str  # Builder, Developer, Individual
    customer_name: str
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    requirement_summary: Optional[str] = None
    lead_source: Optional[str] = None  # Cold visit, Reference, Architect, Existing Client
    lead_status: str = "New"  # New, Contacted, Qualified, Quotation Sent, Won, Lost
    assigned_sales_executive: Optional[str] = None
    first_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    lead_status: Optional[str] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    requirement_summary: Optional[str] = None
    lead_source: Optional[str] = None
    assigned_sales_executive: Optional[str] = None
    first_contact_date: Optional[datetime] = None
    last_follow_up_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    notes: Optional[str] = None
    converted_to_party_id: Optional[int] = None


class Lead(LeadBase):
    id: int
    lead_number: str
    converted_to_party_id: Optional[int] = None
    converted_at: Optional[datetime] = None
    assigned_to: Optional[int] = None
    first_contact_date: Optional[datetime] = None
    last_follow_up_date: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Site/Project Schemas
class SiteProjectBase(BaseModel):
    party_id: int
    party_name: str
    project_name: str
    location: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    no_of_units: Optional[int] = None
    tentative_door_count: Optional[int] = None
    expected_timeline: Optional[str] = None
    project_status: str = "Planning"  # Planning, Under Construction, Completed
    site_contact_person: Optional[str] = None
    site_contact_mobile: Optional[str] = None
    notes: Optional[str] = None


class SiteProjectCreate(SiteProjectBase):
    pass


class SiteProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    no_of_units: Optional[int] = None
    tentative_door_count: Optional[int] = None
    expected_timeline: Optional[str] = None
    project_status: Optional[str] = None
    site_contact_person: Optional[str] = None
    site_contact_mobile: Optional[str] = None
    notes: Optional[str] = None


class SiteProject(SiteProjectBase):
    id: int
    project_code: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Quotation Line Item Schema
class QuotationLineItem(BaseModel):
    door_type: str  # Main Door, Bedroom Door, Bathroom Door, Safety Door
    finish_type: str  # Veneer, Laminated, etc.
    quantity: int
    rate: Decimal
    discount: Optional[Decimal] = Decimal("0.00")
    amount: Decimal


# Quotation Schemas
class QuotationBase(BaseModel):
    party_id: int
    party_name: str
    site_project_id: Optional[int] = None
    lead_id: Optional[int] = None
    validity_date: Optional[date] = None
    payment_terms: Optional[str] = None
    delivery_timeline: Optional[str] = None
    line_items: List[Dict[str, Any]]  # List of quotation line items
    discount_amount: Optional[Decimal] = Decimal("0.00")
    discount_percentage: Optional[Decimal] = None
    notes: Optional[str] = None


class QuotationCreate(QuotationBase):
    pass


class QuotationUpdate(BaseModel):
    validity_date: Optional[date] = None
    payment_terms: Optional[str] = None
    delivery_timeline: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    discount_amount: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class Quotation(QuotationBase):
    id: int
    quotation_number: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    discount_approved_by: Optional[int] = None
    discount_approved_at: Optional[datetime] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Sales Order Schemas
class SalesOrderBase(BaseModel):
    quotation_id: Optional[int] = None
    party_id: int
    party_name: str
    site_project_id: Optional[int] = None
    po_number: Optional[str] = None
    order_date: date
    expected_delivery_date: Optional[date] = None
    payment_terms: Optional[str] = None
    payment_terms_accepted: bool = False
    total_amount: Decimal
    notes: Optional[str] = None


class SalesOrderCreate(SalesOrderBase):
    pass


class SalesOrderUpdate(BaseModel):
    po_number: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    payment_terms: Optional[str] = None
    payment_terms_accepted: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class SalesOrder(SalesOrderBase):
    id: int
    order_number: str
    status: str
    measurement_requested: bool
    measurement_id: Optional[int] = None
    production_paper_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Measurement Request Schemas
class MeasurementRequestBase(BaseModel):
    sales_order_id: int
    sales_order_number: str
    party_id: int
    party_name: str
    site_project_id: Optional[int] = None
    preferred_measurement_date: Optional[date] = None
    preferred_measurement_time: Optional[str] = None
    site_address: Optional[str] = None
    site_contact_person: Optional[str] = None
    site_contact_mobile: Optional[str] = None
    assigned_engineer_id: Optional[int] = None
    assigned_engineer_name: Optional[str] = None
    notes: Optional[str] = None


class MeasurementRequestCreate(MeasurementRequestBase):
    pass


class MeasurementRequestUpdate(BaseModel):
    preferred_measurement_date: Optional[date] = None
    preferred_measurement_time: Optional[str] = None
    site_address: Optional[str] = None
    site_contact_person: Optional[str] = None
    site_contact_mobile: Optional[str] = None
    assigned_engineer_id: Optional[int] = None
    assigned_engineer_name: Optional[str] = None
    status: Optional[str] = None
    measurement_id: Optional[int] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class MeasurementRequest(MeasurementRequestBase):
    id: int
    request_number: str
    status: str
    measurement_id: Optional[int] = None
    completed_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Follow-up Schemas
class FollowUpBase(BaseModel):
    lead_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    party_id: Optional[int] = None
    follow_up_type: str  # Call, Visit, Email, WhatsApp, Meeting
    follow_up_date: datetime
    subject: Optional[str] = None
    description: str
    call_duration: Optional[str] = None
    email_sent: bool = False
    whatsapp_sent: bool = False
    outcome: Optional[str] = None  # Positive, Negative, Neutral, Follow-up Required
    next_follow_up_date: Optional[datetime] = None
    notes: Optional[str] = None


class FollowUpCreate(FollowUpBase):
    pass


class FollowUpUpdate(BaseModel):
    follow_up_type: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    call_duration: Optional[str] = None
    email_sent: Optional[bool] = None
    whatsapp_sent: Optional[bool] = None
    outcome: Optional[str] = None
    next_follow_up_date: Optional[datetime] = None
    notes: Optional[str] = None


class FollowUp(FollowUpBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Dashboard Stats Schema
class SalesDashboardStats(BaseModel):
    new_leads: int = 0
    active_opportunities: int = 0
    orders_confirmed: int = 0
    measurement_pending: int = 0
    sales_value_mtd: Decimal = Decimal("0.00")
    lead_conversion_rate: Decimal = Decimal("0.00")

