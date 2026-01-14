from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Numeric, Date, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CHEQUE = "cheque"
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    NEFT = "neft"
    RTGS = "rtgs"
    IMPS = "imps"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    OTHER = "other"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    RECEIVED = "received"
    CLEARED = "cleared"
    BOUNCED = "bounced"
    CANCELLED = "cancelled"


class PaymentReceipt(Base):
    """Payment Receipts - Records of payments received from customers"""
    __tablename__ = "payment_receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String, unique=True, index=True, nullable=False)  # PR-0001
    tax_invoice_id = Column(Integer, ForeignKey("tax_invoices.id"), nullable=True, index=True)
    
    # Party Information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_name = Column(String, nullable=False)
    
    # Payment Details
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String, nullable=False)  # cash, cheque, bank_transfer, etc.
    payment_amount = Column(Numeric(15, 2), nullable=False)
    bank_name = Column(String, nullable=True)
    cheque_number = Column(String, nullable=True)
    transaction_reference = Column(String, nullable=True)  # UPI ref, NEFT ref, etc.
    bank_account = Column(String, nullable=True)  # Account number or UPI ID
    
    # Status
    status = Column(String, default="pending", nullable=False)  # pending, received, cleared, bounced, cancelled
    cleared_date = Column(Date, nullable=True)
    bounced_date = Column(Date, nullable=True)
    bounce_reason = Column(Text, nullable=True)
    
    # Allocation (if partial payment)
    allocated_amount = Column(Numeric(15, 2), nullable=False, default=0)  # Amount allocated to invoices
    unallocated_amount = Column(Numeric(15, 2), nullable=False, default=0)  # Amount not yet allocated
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tax_invoice = relationship("TaxInvoice", foreign_keys=[tax_invoice_id])
    party = relationship("Party")
    created_by_user = relationship("User")
    payment_allocations = relationship("PaymentAllocation", back_populates="payment_receipt", cascade="all, delete-orphan")


class PaymentAllocation(Base):
    """Allocation of payments to specific invoices"""
    __tablename__ = "payment_allocations"

    id = Column(Integer, primary_key=True, index=True)
    payment_receipt_id = Column(Integer, ForeignKey("payment_receipts.id"), nullable=False, index=True)
    tax_invoice_id = Column(Integer, ForeignKey("tax_invoices.id"), nullable=False, index=True)
    
    # Allocation Details
    allocated_amount = Column(Numeric(15, 2), nullable=False)
    allocation_date = Column(Date, nullable=False)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    payment_receipt = relationship("PaymentReceipt", back_populates="payment_allocations")
    tax_invoice = relationship("TaxInvoice")
    created_by_user = relationship("User")


class AccountReceivable(Base):
    """Accounts Receivable - Outstanding invoices and aging analysis"""
    __tablename__ = "account_receivables"

    id = Column(Integer, primary_key=True, index=True)
    tax_invoice_id = Column(Integer, ForeignKey("tax_invoices.id"), nullable=False, unique=True, index=True)
    
    # Invoice Details
    invoice_number = Column(String, nullable=False, index=True)
    invoice_date = Column(Date, nullable=False)
    invoice_amount = Column(Numeric(15, 2), nullable=False)
    
    # Party Information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_name = Column(String, nullable=False)
    
    # Payment Terms
    payment_terms = Column(String, nullable=True)  # e.g., "Net 30", "Advance", "Credit 45 days"
    due_date = Column(Date, nullable=True)
    
    # Amounts
    total_paid = Column(Numeric(15, 2), nullable=False, default=0)
    outstanding_amount = Column(Numeric(15, 2), nullable=False)
    
    # Aging
    days_overdue = Column(Integer, nullable=True, default=0)
    aging_bucket = Column(String, nullable=True)  # current, 0-30, 31-60, 61-90, 90+
    
    # Status
    status = Column(String, nullable=False, default="outstanding")  # outstanding, partially_paid, paid, overdue, written_off
    
    # Audit
    last_payment_date = Column(Date, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tax_invoice = relationship("TaxInvoice")
    party = relationship("Party")


class AccountReconciliation(Base):
    """Account Reconciliation Records"""
    __tablename__ = "account_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    reconciliation_number = Column(String, unique=True, index=True, nullable=False)  # REC-0001
    
    # Reconciliation Period
    reconciliation_date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Party (if party-specific reconciliation)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    
    # Summary
    opening_balance = Column(Numeric(15, 2), nullable=False, default=0)
    invoices_issued = Column(Numeric(15, 2), nullable=False, default=0)
    payments_received = Column(Numeric(15, 2), nullable=False, default=0)
    closing_balance = Column(Numeric(15, 2), nullable=False, default=0)
    discrepancies = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Status
    status = Column(String, nullable=False, default="draft")  # draft, in_review, approved, rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    party = relationship("Party")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class VendorPayable(Base):
    """Vendor Payables - Bills from suppliers/vendors"""
    __tablename__ = "vendor_payables"

    id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String, unique=True, index=True, nullable=False)
    po_number = Column(String, nullable=True, index=True)  # Purchase Order reference
    
    # Vendor Information
    vendor_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    vendor_name = Column(String, nullable=False)
    
    # Bill Details
    bill_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    bill_amount = Column(Numeric(15, 2), nullable=False)
    
    # Payment Details
    paid_amount = Column(Numeric(15, 2), nullable=False, default=0)
    pending_amount = Column(Numeric(15, 2), nullable=False)
    
    # Status
    status = Column(String, nullable=False, default="pending")  # pending, partially_paid, paid, overdue
    
    # Payment Terms
    payment_terms = Column(String, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vendor = relationship("Supplier")
    created_by_user = relationship("User")
    payments = relationship("VendorPayment", back_populates="vendor_payable")


class VendorPayment(Base):
    """Payments made to vendors"""
    __tablename__ = "vendor_payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String, unique=True, index=True, nullable=False)  # VP-0001
    vendor_payable_id = Column(Integer, ForeignKey("vendor_payables.id"), nullable=False, index=True)
    
    # Payment Details
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String, nullable=False)
    payment_amount = Column(Numeric(15, 2), nullable=False)
    bank_name = Column(String, nullable=True)
    cheque_number = Column(String, nullable=True)
    transaction_reference = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="pending", nullable=False)  # pending, approved, paid, cancelled
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vendor_payable = relationship("VendorPayable", back_populates="payments")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class Ledger(Base):
    """General Ledger - Customer, Vendor, Expense, Asset ledgers"""
    __tablename__ = "ledgers"

    id = Column(Integer, primary_key=True, index=True)
    ledger_code = Column(String, unique=True, index=True, nullable=False)
    ledger_name = Column(String, nullable=False)
    ledger_type = Column(String, nullable=False)  # customer, vendor, expense, asset, income
    
    # Party/Entity Reference
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    
    # Opening Balance
    opening_balance = Column(Numeric(15, 2), nullable=False, default=0)
    opening_balance_type = Column(String, nullable=False, default="debit")  # debit, credit
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    party = relationship("Party")
    supplier = relationship("Supplier")
    created_by_user = relationship("User")
    ledger_entries = relationship("LedgerEntry", back_populates="ledger")


class LedgerEntry(Base):
    """Ledger Entries - Transactions posted to ledgers"""
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String, unique=True, index=True, nullable=False)  # LE-0001
    ledger_id = Column(Integer, ForeignKey("ledgers.id"), nullable=False, index=True)
    
    # Entry Details
    entry_date = Column(Date, nullable=False)
    entry_type = Column(String, nullable=False)  # debit, credit
    amount = Column(Numeric(15, 2), nullable=False)
    
    # Reference
    reference_type = Column(String, nullable=True)  # invoice, payment, receipt, journal
    reference_id = Column(Integer, nullable=True)
    reference_number = Column(String, nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    narration = Column(Text, nullable=True)
    
    # Period Locking
    period_locked = Column(Boolean, default=False, nullable=False)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ledger = relationship("Ledger", back_populates="ledger_entries")
    created_by_user = relationship("User")


class Contractor(Base):
    """Contractor Master"""
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, index=True)
    contractor_code = Column(String, unique=True, index=True, nullable=False)
    contractor_name = Column(String, nullable=False)
    
    # Contractor Details
    contractor_type = Column(String, nullable=False)  # door_contractor, frame_contractor, multi_skill
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    # Payment Method
    payment_method = Column(String, nullable=False)  # per_door, per_frame, per_stage
    
    # Rate Card
    door_rate = Column(Numeric(10, 2), nullable=True)  # Rate per door
    frame_rate = Column(Numeric(10, 2), nullable=True)  # Rate per frame
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    created_by_user = relationship("User")
    work_orders = relationship("ContractorWorkOrder", back_populates="contractor")
    output_records = relationship("ContractorOutput", back_populates="contractor")


class ContractorWorkOrder(Base):
    """Work orders assigned to contractors"""
    __tablename__ = "contractor_work_orders"

    id = Column(Integer, primary_key=True, index=True)
    work_order_number = Column(String, unique=True, index=True, nullable=False)  # WO-0001
    
    # Production Reference
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    production_paper_number = Column(String, nullable=False)
    
    # Contractor
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False, index=True)
    
    # Work Details
    product_type = Column(String, nullable=False)  # door, frame
    stage = Column(String, nullable=True)  # e.g., "Laminate Press", "Assembly"
    assigned_quantity = Column(Integer, nullable=False)
    
    # Status
    status = Column(String, nullable=False, default="assigned")  # assigned, in_progress, completed, cancelled
    
    # Audit
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Production Supervisor
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper")
    contractor = relationship("Contractor", back_populates="work_orders")
    assigned_by_user = relationship("User")
    output_records = relationship("ContractorOutput", back_populates="work_order")


class ContractorOutput(Base):
    """Contractor production output records"""
    __tablename__ = "contractor_outputs"

    id = Column(Integer, primary_key=True, index=True)
    output_date = Column(Date, nullable=False)
    
    # References
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False, index=True)
    work_order_id = Column(Integer, ForeignKey("contractor_work_orders.id"), nullable=True, index=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, index=True)
    
    # Product Details
    product_type = Column(String, nullable=False)  # door, frame
    stage = Column(String, nullable=True)
    
    # Quantities
    completed_quantity = Column(Integer, nullable=False, default=0)
    rework_quantity = Column(Integer, nullable=False, default=0)
    rejected_quantity = Column(Integer, nullable=False, default=0)
    
    # QC Approval
    qc_approved_quantity = Column(Integer, nullable=False, default=0)
    supervisor_approval = Column(Boolean, default=False, nullable=False)
    supervisor_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    supervisor_approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Payment Calculation
    payable_quantity = Column(Integer, nullable=False, default=0)  # Only QC-approved
    payable_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Status
    status = Column(String, nullable=False, default="pending")  # pending, approved, paid
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    contractor = relationship("Contractor", back_populates="output_records")
    work_order = relationship("ContractorWorkOrder", back_populates="output_records")
    production_paper = relationship("ProductionPaper")
    supervisor_approved_by_user = relationship("User", foreign_keys=[supervisor_approved_by])
    created_by_user = relationship("User", foreign_keys=[created_by])


class ContractorPayment(Base):
    """Payments made to contractors"""
    __tablename__ = "contractor_payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String, unique=True, index=True, nullable=False)  # CP-0001
    
    # Contractor
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False, index=True)
    
    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Payment Details
    payment_date = Column(Date, nullable=False)
    payment_amount = Column(Numeric(15, 2), nullable=False)
    payment_method = Column(String, nullable=False)
    
    # Output Summary
    doors_completed = Column(Integer, nullable=False, default=0)
    frames_completed = Column(Integer, nullable=False, default=0)
    total_payable_qty = Column(Integer, nullable=False, default=0)
    
    # Status
    status = Column(String, nullable=False, default="pending")  # pending, approved, paid
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    contractor = relationship("Contractor")
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    created_by_user = relationship("User", foreign_keys=[created_by])


class OrderCosting(Base):
    """Order-wise costing and profitability"""
    __tablename__ = "order_costings"

    id = Column(Integer, primary_key=True, index=True)
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=False, unique=True, index=True)
    production_paper_number = Column(String, nullable=False)
    
    # Costs
    material_cost = Column(Numeric(15, 2), nullable=False, default=0)
    labor_cost = Column(Numeric(15, 2), nullable=False, default=0)
    overhead_cost = Column(Numeric(15, 2), nullable=False, default=0)
    logistics_cost = Column(Numeric(15, 2), nullable=False, default=0)
    contractor_cost = Column(Numeric(15, 2), nullable=False, default=0)
    total_cost = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Revenue
    invoice_amount = Column(Numeric(15, 2), nullable=True)
    revenue = Column(Numeric(15, 2), nullable=True)
    
    # Profitability
    profit = Column(Numeric(15, 2), nullable=True)
    profit_margin = Column(Numeric(5, 2), nullable=True)  # Percentage
    
    # Product Breakdown
    door_count = Column(Integer, nullable=False, default=0)
    frame_count = Column(Integer, nullable=False, default=0)
    door_profit = Column(Numeric(15, 2), nullable=True)
    frame_profit = Column(Numeric(15, 2), nullable=True)
    
    # Audit
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    production_paper = relationship("ProductionPaper")


class CreditControl(Base):
    """Credit Control Settings for Parties"""
    __tablename__ = "credit_controls"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    
    # Credit Limits
    credit_limit = Column(Numeric(15, 2), nullable=True)
    credit_days = Column(Integer, nullable=True)  # e.g., 30, 45, 60
    
    # Current Status
    current_outstanding = Column(Numeric(15, 2), nullable=False, default=0)
    available_credit = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Controls
    is_blocked = Column(Boolean, default=False, nullable=False)
    block_reason = Column(Text, nullable=True)
    blocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Override
    override_allowed = Column(Boolean, default=False, nullable=False)  # Finance Head can override
    last_override_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_override_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    party = relationship("Party")
    blocked_by_user = relationship("User", foreign_keys=[blocked_by])
    last_override_by_user = relationship("User", foreign_keys=[last_override_by])

