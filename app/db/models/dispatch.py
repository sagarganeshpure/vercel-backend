from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Dispatch(Base):
    """Main Dispatch Record - Controls outward movement of doors & frames"""
    __tablename__ = "dispatches"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: DSP-001
    dispatch_request_no = Column(String, nullable=True, index=True)  # DR-1023 (if from request)
    
    # Production Paper Link
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False, index=True)
    
    # Billing Link (MUST have approved DC/Invoice)
    billing_request_id = Column(Integer, ForeignKey("billing_requests.id"), nullable=True, index=True)
    delivery_challan_id = Column(Integer, ForeignKey("delivery_challans.id"), nullable=True, index=True)
    tax_invoice_id = Column(Integer, ForeignKey("tax_invoices.id"), nullable=True, index=True)
    dc_number = Column(String, nullable=True, index=True)
    invoice_number = Column(String, nullable=True, index=True)
    
    # Party Information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_name = Column(String, nullable=False)
    delivery_address = Column(Text, nullable=False)
    
    # Dispatch Details
    dispatch_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=True)
    
    # Vehicle & Logistics
    vehicle_type = Column(String, nullable=False)  # Company, Transporter
    vehicle_no = Column(String, nullable=False)
    driver_name = Column(String, nullable=True)
    driver_mobile = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="draft", nullable=False)  # draft, approved, dispatched, in_transit, delivered, delayed
    
    # QC & Billing Approval Flags
    qc_approved = Column(Boolean, default=False, nullable=False)
    billing_approved = Column(Boolean, default=False, nullable=False)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Dispatch Executive
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Dispatch Supervisor
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    production_paper = relationship("ProductionPaper")
    billing_request = relationship("BillingRequest")
    delivery_challan = relationship("DeliveryChallan")
    tax_invoice = relationship("TaxInvoice")
    party = relationship("Party")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    dispatch_items = relationship("DispatchItem", back_populates="dispatch", cascade="all, delete-orphan")
    gate_pass = relationship("GatePass", back_populates="dispatch", uselist=False)
    delivery_tracking = relationship("DeliveryTracking", back_populates="dispatch", uselist=False)
    logistics_assignment = relationship("LogisticsAssignment", foreign_keys="LogisticsAssignment.dispatch_id", uselist=False)


class DispatchItem(Base):
    """Items in a Dispatch - Product details"""
    __tablename__ = "dispatch_items"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=False, index=True)
    
    # Product Information
    product_type = Column(String, nullable=False)  # Door, Frame
    product_description = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    packaging_type = Column(String, nullable=True)  # Packed, Loose, etc.
    weight = Column(Float, nullable=True)  # Optional
    volume = Column(Float, nullable=True)  # Optional
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    dispatch = relationship("Dispatch", back_populates="dispatch_items")


class GatePass(Base):
    """Gate Pass for Security - Generated when dispatch is approved"""
    __tablename__ = "gate_passes"

    id = Column(Integer, primary_key=True, index=True)
    gate_pass_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: GP-001
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=False, unique=True, index=True)
    dispatch_number = Column(String, nullable=False, index=True)
    
    # Vehicle Details
    vehicle_no = Column(String, nullable=False)
    driver_name = Column(String, nullable=True)
    driver_mobile = Column(String, nullable=True)
    
    # Item Summary (JSON)
    item_summary = Column(Text, nullable=False)  # JSON: [{product_type, description, quantity}]
    
    # Security Verification
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Security user
    time_out = Column(DateTime(timezone=True), nullable=True)  # Vehicle exit time
    verified = Column(Boolean, default=False, nullable=False)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    dispatch = relationship("Dispatch", back_populates="gate_pass")
    verified_by_user = relationship("User")


class DeliveryTracking(Base):
    """Delivery Status Tracking - Updated by Logistics"""
    __tablename__ = "delivery_tracking"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=False, unique=True, index=True)
    dispatch_number = Column(String, nullable=False, index=True)
    
    # Status
    status = Column(String, default="dispatched", nullable=False)  # dispatched, in_transit, delivered, delayed
    
    # Delivery Details
    delivered_date = Column(DateTime(timezone=True), nullable=True)
    receiver_name = Column(String, nullable=True)
    receiver_mobile = Column(String, nullable=True)
    
    # POD (Proof of Delivery)
    pod_photo_url = Column(Text, nullable=True)  # URL or base64
    pod_signature_url = Column(Text, nullable=True)  # URL or base64
    
    # Issues
    shortage_remarks = Column(Text, nullable=True)
    damage_remarks = Column(Text, nullable=True)
    
    # Delay Information
    delay_reason = Column(Text, nullable=True)
    expected_delivery_date = Column(Date, nullable=True)
    actual_delivery_date = Column(Date, nullable=True)
    
    # Audit
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Logistics user
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    dispatch = relationship("Dispatch", back_populates="delivery_tracking")
    updated_by_user = relationship("User")

