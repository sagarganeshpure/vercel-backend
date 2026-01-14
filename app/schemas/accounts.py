from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal


# Payment Receipt Schemas
class PaymentReceiptBase(BaseModel):
    tax_invoice_id: Optional[int] = None
    party_id: int
    party_name: str
    payment_date: date
    payment_method: str  # cash, cheque, bank_transfer, upi, neft, rtgs, imps, credit_card, debit_card, other
    payment_amount: Decimal
    bank_name: Optional[str] = None
    cheque_number: Optional[str] = None
    transaction_reference: Optional[str] = None
    bank_account: Optional[str] = None
    remarks: Optional[str] = None


class PaymentReceiptCreate(PaymentReceiptBase):
    pass


class PaymentReceiptUpdate(BaseModel):
    status: Optional[str] = None
    cleared_date: Optional[date] = None
    bounced_date: Optional[date] = None
    bounce_reason: Optional[str] = None
    remarks: Optional[str] = None


class PaymentReceipt(PaymentReceiptBase):
    id: int
    receipt_number: str
    status: str
    allocated_amount: Decimal
    unallocated_amount: Decimal
    cleared_date: Optional[date] = None
    bounced_date: Optional[date] = None
    bounce_reason: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Payment Allocation Schemas
class PaymentAllocationBase(BaseModel):
    payment_receipt_id: int
    tax_invoice_id: int
    allocated_amount: Decimal
    allocation_date: date
    remarks: Optional[str] = None


class PaymentAllocationCreate(PaymentAllocationBase):
    pass


class PaymentAllocation(PaymentAllocationBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Account Receivable Schemas
class AccountReceivableBase(BaseModel):
    tax_invoice_id: int
    invoice_number: str
    invoice_date: date
    invoice_amount: Decimal
    party_id: int
    party_name: str
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None


class AccountReceivableCreate(AccountReceivableBase):
    pass


class AccountReceivableUpdate(BaseModel):
    total_paid: Optional[Decimal] = None
    outstanding_amount: Optional[Decimal] = None
    days_overdue: Optional[int] = None
    aging_bucket: Optional[str] = None
    status: Optional[str] = None
    last_payment_date: Optional[date] = None


class AccountReceivable(AccountReceivableBase):
    id: int
    total_paid: Decimal
    outstanding_amount: Decimal
    days_overdue: Optional[int] = None
    aging_bucket: Optional[str] = None
    status: str
    last_payment_date: Optional[date] = None
    updated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Account Reconciliation Schemas
class AccountReconciliationBase(BaseModel):
    reconciliation_date: date
    period_start: date
    period_end: date
    party_id: Optional[int] = None
    opening_balance: Decimal = Decimal("0.00")
    invoices_issued: Decimal = Decimal("0.00")
    payments_received: Decimal = Decimal("0.00")
    closing_balance: Decimal = Decimal("0.00")
    discrepancies: Decimal = Decimal("0.00")
    remarks: Optional[str] = None


class AccountReconciliationCreate(AccountReconciliationBase):
    pass


class AccountReconciliationUpdate(BaseModel):
    status: Optional[str] = None
    remarks: Optional[str] = None


class AccountReconciliation(AccountReconciliationBase):
    id: int
    reconciliation_number: str
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Dashboard and Reports Schemas
class AccountsDashboardStats(BaseModel):
    total_outstanding: Decimal
    overdue_amount: Decimal
    payments_received_today: Decimal
    payments_received_this_month: Decimal
    pending_payments: int
    overdue_invoices: int
    aging_summary: Dict[str, Decimal]  # { "current": amount, "0-30": amount, "31-60": amount, "61-90": amount, "90+": amount }


class AgingAnalysis(BaseModel):
    party_id: int
    party_name: str
    total_outstanding: Decimal
    current: Decimal
    days_0_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_90_plus: Decimal

