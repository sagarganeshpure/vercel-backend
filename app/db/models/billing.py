from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class BillingRequest(Base):
    """Dispatch requests that need billing - created by Dispatch department"""
    __tablename__ = "billing_requests"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_request_no = Column(String, unique=True, index=True, nullable=False)  # DR-1023
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False, index=True)
    
    # Party Information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_name = Column(String, nullable=False)
    party_gstin = Column(String, nullable=True)
    
    # Delivery Information
    site_name = Column(String, nullable=True)
    delivery_address = Column(Text, nullable=False)
    vehicle_no = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    dispatch_date = Column(Date, nullable=True)
    
    # Item Details (JSON - cannot be changed by billing)
    items = Column(Text, nullable=False)  # JSON: [{product_name, door_frame_type, quantity, uom}]
    
    # Status
    status = Column(String, default="pending", nullable=False)  # pending, dc_created, invoice_created, billing_approved, sent_to_dispatch
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Dispatch user
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper")
    party = relationship("Party")
    created_by_user = relationship("User")
    delivery_challans = relationship("DeliveryChallan", back_populates="billing_request")
    tax_invoices = relationship("TaxInvoice", back_populates="billing_request")


class DeliveryChallan(Base):
    """Delivery Challan (DC) - Material movement document"""
    __tablename__ = "delivery_challans"

    id = Column(Integer, primary_key=True, index=True)
    dc_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: DC-001
    billing_request_id = Column(Integer, ForeignKey("billing_requests.id"), nullable=False, index=True)
    dispatch_request_no = Column(String, nullable=False, index=True)
    
    # Party Information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    party_name = Column(String, nullable=False)
    
    # Delivery Information
    delivery_address = Column(Text, nullable=False)
    vehicle_no = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    dc_date = Column(Date, nullable=False)
    
    # Line Items (JSON)
    line_items = Column(Text, nullable=False)  # JSON: [{product_name, door_frame_type, quantity, uom, remarks}]
    
    # Status
    status = Column(String, default="draft", nullable=False)  # draft, approved, sent_to_dispatch
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Billing Executive
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Accounts Manager
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    billing_request = relationship("BillingRequest", back_populates="delivery_challans")
    party = relationship("Party")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    tax_invoices = relationship("TaxInvoice", back_populates="delivery_challan")


class TaxInvoice(Base):
    """GST Compliant Tax Invoice"""
    __tablename__ = "tax_invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: INV-001
    billing_request_id = Column(Integer, ForeignKey("billing_requests.id"), nullable=False, index=True)
    delivery_challan_id = Column(Integer, ForeignKey("delivery_challans.id"), nullable=True, index=True)
    dispatch_request_no = Column(String, nullable=False, index=True)
    
    # Party Information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    party_name = Column(String, nullable=False)
    party_gstin = Column(String, nullable=True)
    place_of_supply = Column(String, nullable=False)  # State name
    state_code = Column(String, nullable=True)
    
    # Invoice Details
    invoice_date = Column(Date, nullable=False)
    payment_terms = Column(String, nullable=True)  # Advance, Credit, etc.
    dc_reference = Column(String, nullable=True)  # DC Number reference
    
    # Line Items (JSON with tax details)
    line_items = Column(Text, nullable=False)  # JSON: [{product_description, hsn_code, quantity, rate, discount, taxable_value, cgst_rate, sgst_rate, igst_rate, cgst_amount, sgst_amount, igst_amount}]
    
    # Totals
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    cgst_total = Column(Numeric(15, 2), nullable=False, default=0)
    sgst_total = Column(Numeric(15, 2), nullable=False, default=0)
    igst_total = Column(Numeric(15, 2), nullable=False, default=0)
    freight = Column(Numeric(15, 2), nullable=True, default=0)
    round_off = Column(Numeric(15, 2), nullable=True, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Status
    status = Column(String, default="draft", nullable=False)  # draft, approved, sent_to_dispatch, tally_synced
    
    # Credit Control
    credit_limit_check = Column(Boolean, default=False, nullable=False)
    credit_limit_exceeded = Column(Boolean, default=False, nullable=False)
    outstanding_amount = Column(Numeric(15, 2), nullable=True)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Billing Executive
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Accounts Manager
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    billing_request = relationship("BillingRequest", back_populates="tax_invoices")
    delivery_challan = relationship("DeliveryChallan", back_populates="tax_invoices")
    party = relationship("Party")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    tally_syncs = relationship("TallySync", back_populates="tax_invoice")


class TallySync(Base):
    """Tally Integration Tracking"""
    __tablename__ = "tally_syncs"

    id = Column(Integer, primary_key=True, index=True)
    tax_invoice_id = Column(Integer, ForeignKey("tax_invoices.id"), nullable=False, index=True)
    
    # Sync Details
    sync_type = Column(String, nullable=False)  # export_invoice, import_payment, import_ledger
    sync_status = Column(String, nullable=False)  # pending, success, failed, retry
    sync_method = Column(String, nullable=False)  # xml_export, excel_import
    
    # Data
    export_data = Column(Text, nullable=True)  # JSON or XML data
    import_data = Column(Text, nullable=True)  # Imported data from Tally
    
    # Response
    tally_response = Column(Text, nullable=True)  # Response from Tally
    error_message = Column(Text, nullable=True)
    
    # Retry
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    synced_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tax_invoice = relationship("TaxInvoice", back_populates="tally_syncs")
    synced_by_user = relationship("User")

