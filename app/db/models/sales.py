from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Lead(Base):
    """Lead Management - Captures leads from various sources"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    lead_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: LD-0001
    
    # Lead Type & Basic Info
    lead_type = Column(String, nullable=False)  # Builder, Developer, Individual
    customer_name = Column(String, nullable=False, index=True)
    contact_person = Column(String, nullable=True)
    mobile = Column(String, nullable=True, index=True)
    whatsapp = Column(String, nullable=True)
    email = Column(String, nullable=True)
    city = Column(String, nullable=True)
    area = Column(String, nullable=True)
    
    # Lead Details
    requirement_summary = Column(Text, nullable=True)
    lead_source = Column(String, nullable=True)  # Cold visit, Reference, Architect, Existing Client
    lead_status = Column(String, default="New", nullable=False)  # New, Contacted, Qualified, Quotation Sent, Won, Lost
    
    # Conversion Info
    converted_to_party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Assignment
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)  # Sales Executive
    assigned_sales_executive = Column(String, nullable=True)
    
    # Dates
    first_contact_date = Column(DateTime(timezone=True), nullable=True)
    last_follow_up_date = Column(DateTime(timezone=True), nullable=True)
    next_follow_up_date = Column(DateTime(timezone=True), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    converted_party = relationship("Party", foreign_keys=[converted_to_party_id])
    follow_ups = relationship("FollowUp", back_populates="lead")
    quotations = relationship("Quotation", back_populates="lead")


class SiteProject(Base):
    """Site & Project Management - Multiple sites per builder/party"""
    __tablename__ = "site_projects"

    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String, unique=True, index=True, nullable=True)  # Auto-generated
    
    # Party Link
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_name = Column(String, nullable=False)
    
    # Project Details
    project_name = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pin_code = Column(String, nullable=True)
    
    # Project Specifications
    no_of_units = Column(Integer, nullable=True)  # Number of flats/units
    tentative_door_count = Column(Integer, nullable=True)
    expected_timeline = Column(String, nullable=True)  # e.g., "Q1 2024"
    project_status = Column(String, default="Planning", nullable=False)  # Planning, Under Construction, Completed
    
    # Contact at Site
    site_contact_person = Column(String, nullable=True)
    site_contact_mobile = Column(String, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    party = relationship("Party")
    quotations = relationship("Quotation", back_populates="site_project")
    sales_orders = relationship("SalesOrder", back_populates="site_project")


class Quotation(Base):
    """Quotation Management - Sales quotations with line items"""
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    quotation_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: QT-0001
    
    # Party & Project Link
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_name = Column(String, nullable=False)
    site_project_id = Column(Integer, ForeignKey("site_projects.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    
    # Quotation Header
    validity_date = Column(Date, nullable=True)
    payment_terms = Column(String, nullable=True)  # Advance, 50% Advance – 50% Delivery, Credit
    delivery_timeline = Column(String, nullable=True)  # Tentative delivery timeline
    
    # Line Items (JSON)
    line_items = Column(Text, nullable=False)  # JSON array of quotation items
    
    # Pricing
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=False, default=0)
    discount_percentage = Column(Numeric(5, 2), nullable=True)
    tax_amount = Column(Numeric(15, 2), nullable=False, default=0)  # GST
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Approval
    discount_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Sales Manager
    discount_approved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="Draft", nullable=False)  # Draft, Sent, Accepted, Rejected, Expired
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    party = relationship("Party")
    site_project = relationship("SiteProject", back_populates="quotations")
    lead = relationship("Lead", back_populates="quotations")
    sales_order = relationship("SalesOrder", back_populates="quotation", uselist=False)
    discount_approver = relationship("User", foreign_keys=[discount_approved_by])


class SalesOrder(Base):
    """Sales Order - Confirmed orders that trigger production flow"""
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: SO-0001
    
    # Links
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_name = Column(String, nullable=False)
    site_project_id = Column(Integer, ForeignKey("site_projects.id"), nullable=True, index=True)
    
    # Order Details
    po_number = Column(String, nullable=True, index=True)  # Customer PO Number
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=True)
    
    # Payment Terms (from quotation)
    payment_terms = Column(String, nullable=True)
    payment_terms_accepted = Column(Boolean, default=False)
    
    # Order Value
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Status
    status = Column(String, default="Confirmed", nullable=False)  # Confirmed, Measurement Pending, In Production, Ready for Dispatch, Dispatched, Delivered, Cancelled
    
    # Production Integration
    measurement_requested = Column(Boolean, default=False)
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    party = relationship("Party")
    site_project = relationship("SiteProject", back_populates="sales_orders")
    quotation = relationship("Quotation", back_populates="sales_order")
    measurement = relationship("Measurement")
    production_paper = relationship("ProductionPaper")
    follow_ups = relationship("FollowUp", back_populates="sales_order")


class MeasurementRequest(Base):
    """Measurement Request - Auto-triggered when order is confirmed"""
    __tablename__ = "measurement_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: MR-0001
    
    # Links
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, index=True)
    sales_order_number = Column(String, nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    party_name = Column(String, nullable=False)
    site_project_id = Column(Integer, ForeignKey("site_projects.id"), nullable=True)
    
    # Request Details
    preferred_measurement_date = Column(Date, nullable=True)
    preferred_measurement_time = Column(String, nullable=True)
    site_address = Column(Text, nullable=True)
    site_contact_person = Column(String, nullable=True)
    site_contact_mobile = Column(String, nullable=True)
    
    # Assignment
    assigned_engineer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_engineer_name = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="Pending", nullable=False)  # Pending, Assigned, Scheduled, Completed, Cancelled
    
    # Completion
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=True)  # Link to actual measurement
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    assigned_engineer = relationship("User", foreign_keys=[assigned_engineer_id])
    sales_order = relationship("SalesOrder")
    site_project = relationship("SiteProject")
    measurement = relationship("Measurement")


class FollowUp(Base):
    """Follow-ups & Communication - CRM features for leads and orders"""
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    
    # Links (can be linked to Lead or Sales Order)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    
    # Follow-up Details
    follow_up_type = Column(String, nullable=False)  # Call, Visit, Email, WhatsApp, Meeting
    follow_up_date = Column(DateTime(timezone=True), nullable=False)
    subject = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    
    # Communication Logs
    call_duration = Column(String, nullable=True)  # e.g., "15 minutes"
    email_sent = Column(Boolean, default=False)
    whatsapp_sent = Column(Boolean, default=False)
    
    # Outcome
    outcome = Column(String, nullable=True)  # Positive, Negative, Neutral, Follow-up Required
    next_follow_up_date = Column(DateTime(timezone=True), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    lead = relationship("Lead", back_populates="follow_ups")
    sales_order = relationship("SalesOrder", back_populates="follow_ups")

