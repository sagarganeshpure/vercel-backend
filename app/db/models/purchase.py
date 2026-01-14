from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Vendor(Base):
    """Vendor Master - Stores vendor information"""
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    vendor_code = Column(String, unique=True, index=True, nullable=False)  # Auto-generated
    vendor_name = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    
    # Vendor Type
    vendor_type = Column(String, nullable=False)  # Plywood Vendor, Laminate/Veneer Vendor, Hardware Vendor, Chemical/Resin Vendor
    
    # Contact Details
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    alternate_phone = Column(String, nullable=True)
    
    # Address
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    area = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pin_code = Column(String, nullable=True)
    country = Column(String, default="India", nullable=True)
    
    # Tax & Compliance
    gstin = Column(String, nullable=True, index=True)
    pan_number = Column(String, nullable=True)
    state_code = Column(String, nullable=True)
    
    # Material Categories (JSON - which materials this vendor supplies)
    material_categories = Column(Text, nullable=True)  # JSON array: ["Laminate", "Plywood", etc.]
    
    # Rate Contract (JSON - stores rate contracts for different materials)
    rate_contracts = Column(Text, nullable=True)  # JSON: [{material_category, rate, unit, valid_from, valid_to}]
    
    # Payment Terms
    payment_terms = Column(String, nullable=True)  # Advance, Credit 30 days, etc.
    credit_days = Column(Integer, nullable=True)
    credit_limit = Column(Numeric(15, 2), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String, default="Active", nullable=False)  # Active, Inactive, Blacklisted
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
    grns = relationship("GRN", back_populates="vendor")
    vendor_bills = relationship("VendorBill", back_populates="vendor")


class BOM(Base):
    """Bill of Materials - Links Production Papers to Material Requirements"""
    __tablename__ = "bom"

    id = Column(Integer, primary_key=True, index=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False, index=True)
    
    # Material Details
    material_category = Column(String, nullable=False)  # Laminate, Plywood, Hardware, Chemical, etc.
    material_name = Column(String, nullable=False)  # Walnut Laminate, 18mm Plywood, etc.
    specification = Column(Text, nullable=True)  # Detailed specifications
    quantity_required = Column(Float, nullable=False)
    unit = Column(String, default="pcs", nullable=False)  # pcs, sheets, kg, m, etc.
    
    # Status
    pr_created = Column(Boolean, default=False, nullable=False)  # Whether PR has been created
    pr_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=True)
    po_created = Column(Boolean, default=False, nullable=False)  # Whether PO has been created
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    material_received = Column(Boolean, default=False, nullable=False)  # Whether material received
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper")
    pr = relationship("PurchaseRequisition", foreign_keys=[pr_id])
    po = relationship("PurchaseOrder", foreign_keys=[po_id])


class PurchaseRequisition(Base):
    """Purchase Requisition (PR) - Material Requirement Request"""
    __tablename__ = "purchase_requisitions"

    id = Column(Integer, primary_key=True, index=True)
    pr_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: PR-1023
    
    # Source of PR
    source_type = Column(String, nullable=False)  # Production Paper, Minimum Stock Level, Manual
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=True, index=True)
    production_paper_number = Column(String, nullable=True, index=True)
    
    # Material Details
    material_category = Column(String, nullable=False)  # Laminate, Plywood, Hardware, etc.
    material_name = Column(String, nullable=False)  # Walnut Laminate, etc.
    specification = Column(Text, nullable=True)
    quantity_required = Column(Float, nullable=False)
    unit = Column(String, default="pcs", nullable=False)
    required_date = Column(Date, nullable=False)
    urgency = Column(String, default="Normal", nullable=False)  # Normal, Urgent
    
    # Status
    status = Column(String, default="Draft", nullable=False)  # Draft, Submitted, Approved, Rejected, Converted to PO
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # PO Link
    po_created = Column(Boolean, default=False, nullable=False)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    po = relationship("PurchaseOrder", foreign_keys=[po_id])


class PurchaseOrder(Base):
    """Purchase Order (PO) - Order placed to vendor"""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: PO-302
    
    # Vendor Information
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    vendor_name = Column(String, nullable=False)  # Store for reference
    
    # PR Link
    pr_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=True, index=True)
    pr_number = Column(String, nullable=True, index=True)
    
    # Production Paper Link
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=True, index=True)
    production_paper_number = Column(String, nullable=True, index=True)
    
    # Dates
    po_date = Column(Date, nullable=False)
    delivery_date = Column(Date, nullable=False)
    
    # Payment Terms
    payment_terms = Column(String, nullable=True)
    
    # Line Items (JSON)
    line_items = Column(Text, nullable=False)  # JSON: [{material_name, specification, quantity, rate, tax_percent, amount}]
    
    # Totals
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(15, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Status
    status = Column(String, default="Draft", nullable=False)  # Draft, Approved, Sent to Vendor, Partially Received, Closed, Cancelled
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    sent_to_vendor_at = Column(DateTime(timezone=True), nullable=True)
    
    # Receipt Status
    total_quantity = Column(Float, nullable=False, default=0)
    received_quantity = Column(Float, nullable=False, default=0)
    pending_quantity = Column(Float, nullable=False, default=0)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vendor = relationship("Vendor", back_populates="purchase_orders")
    pr = relationship("PurchaseRequisition", foreign_keys=[pr_id])
    production_paper = relationship("ProductionPaper")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    grns = relationship("GRN", back_populates="purchase_order")
    purchase_returns = relationship("PurchaseReturn", back_populates="purchase_order")


class GRN(Base):
    """Goods Receipt Note (GRN) - Material Receipt at Store"""
    __tablename__ = "grns"

    id = Column(Integer, primary_key=True, index=True)
    grn_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: GRN-558
    
    # PO Link (Mandatory)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)
    po_number = Column(String, nullable=False, index=True)
    
    # Vendor Information
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    vendor_name = Column(String, nullable=False)
    
    # Material Details
    material_category = Column(String, nullable=False)
    material_name = Column(String, nullable=False)
    specification = Column(Text, nullable=True)
    
    # Quantities
    ordered_quantity = Column(Float, nullable=False)
    received_quantity = Column(Float, nullable=False)
    rejected_quantity = Column(Float, nullable=False, default=0)
    shortage_quantity = Column(Float, nullable=False, default=0)
    accepted_quantity = Column(Float, nullable=False)  # received - rejected
    
    # Quality Check
    qc_status = Column(String, default="Pending", nullable=False)  # Pending, Accepted, Rejected, Partially Accepted
    qc_checked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    qc_checked_at = Column(DateTime(timezone=True), nullable=True)
    qc_remarks = Column(Text, nullable=True)
    
    # QC Parameters (JSON)
    qc_parameters = Column(Text, nullable=True)  # JSON: {size: "OK", thickness: "OK", shade: "OK", damage: "None"}
    
    # Status
    status = Column(String, default="Draft", nullable=False)  # Draft, Approved, Rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Purchase Return Link (if rejected)
    purchase_return_id = Column(Integer, ForeignKey("purchase_returns.id"), nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Store Incharge
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="grns")
    vendor = relationship("Vendor", back_populates="grns")
    created_by_user = relationship("User", foreign_keys=[created_by])
    qc_checker = relationship("User", foreign_keys=[qc_checked_by])
    approver = relationship("User", foreign_keys=[approved_by])
    purchase_return = relationship("PurchaseReturn", foreign_keys=[purchase_return_id], uselist=False)
    vendor_bills = relationship("VendorBill", back_populates="grn")


class PurchaseReturn(Base):
    """Purchase Return - Return of rejected/damaged material"""
    __tablename__ = "purchase_returns"

    id = Column(Integer, primary_key=True, index=True)
    return_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: PRET-001
    
    # PO & GRN Links
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)
    po_number = Column(String, nullable=False)
    grn_id = Column(Integer, ForeignKey("grns.id"), nullable=True, index=True)
    grn_number = Column(String, nullable=True)
    
    # Vendor Information
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    vendor_name = Column(String, nullable=False)
    
    # Material Details
    material_category = Column(String, nullable=False)
    material_name = Column(String, nullable=False)
    specification = Column(Text, nullable=True)
    return_quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    
    # Return Reason
    return_reason = Column(String, nullable=False)  # Damaged, Wrong Specification, Excess Received
    return_description = Column(Text, nullable=True)
    
    # Status
    status = Column(String, default="Draft", nullable=False)  # Draft, Sent to Vendor, Acknowledged, Completed
    vendor_notified = Column(Boolean, default=False, nullable=False)
    vendor_notified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Stock Update
    stock_updated = Column(Boolean, default=False, nullable=False)
    stock_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="purchase_returns")
    grn = relationship("GRN", foreign_keys=[grn_id])
    vendor = relationship("Vendor")
    created_by_user = relationship("User")


class VendorBill(Base):
    """Vendor Bill - Bill received from vendor for payment"""
    __tablename__ = "vendor_bills"

    id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated: VB-001
    
    # GRN Link (Mandatory - No payment without GRN)
    grn_id = Column(Integer, ForeignKey("grns.id"), nullable=False, index=True)
    grn_number = Column(String, nullable=False, index=True)
    
    # PO Link
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True, index=True)
    po_number = Column(String, nullable=True)
    
    # Vendor Information
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    vendor_name = Column(String, nullable=False)
    vendor_gstin = Column(String, nullable=True)
    
    # Bill Details
    vendor_bill_no = Column(String, nullable=False, index=True)  # Bill number from vendor
    vendor_bill_date = Column(Date, nullable=False)
    bill_amount = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)
    
    # GST Details (JSON)
    gst_breakup = Column(Text, nullable=True)  # JSON: {cgst: 0, sgst: 0, igst: 0, etc.}
    
    # Payment Status
    payment_status = Column(String, default="Pending", nullable=False)  # Pending, Approved, Paid, Partially Paid
    payment_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    payment_approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Payment Details (JSON - links to payment records)
    payment_details = Column(Text, nullable=True)  # JSON: [{payment_id, amount, payment_date}]
    
    # Tally Integration
    tally_synced = Column(Boolean, default=False, nullable=False)
    tally_sync_date = Column(DateTime(timezone=True), nullable=True)
    tally_voucher_no = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="Draft", nullable=False)  # Draft, Submitted, Approved, Paid, Rejected
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    grn = relationship("GRN", back_populates="vendor_bills")
    purchase_order = relationship("PurchaseOrder")
    vendor = relationship("Vendor", back_populates="vendor_bills")
    created_by_user = relationship("User", foreign_keys=[created_by])
    payment_approver = relationship("User", foreign_keys=[payment_approved_by])

