from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
import re
import json

from app.schemas.accounts import (
    PaymentReceipt, PaymentReceiptCreate, PaymentReceiptUpdate,
    PaymentAllocation, PaymentAllocationCreate,
    AccountReceivable, AccountReceivableCreate, AccountReceivableUpdate,
    AccountReconciliation, AccountReconciliationCreate, AccountReconciliationUpdate,
    AccountsDashboardStats, AgingAnalysis
)
from app.db.models.accounts import (
    PaymentReceipt as DBPaymentReceipt,
    PaymentAllocation as DBPaymentAllocation,
    AccountReceivable as DBAccountReceivable,
    AccountReconciliation as DBAccountReconciliation
)
from app.db.models.billing import TaxInvoice as DBTaxInvoice
from app.db.models.user import Party as DBParty
from app.api.deps import get_db, get_accounts_manager, get_billing_executive

router = APIRouter()


# Helper Functions
def generate_receipt_number(db: Session) -> str:
    """Generate next payment receipt number"""
    last_receipt = db.query(DBPaymentReceipt).order_by(DBPaymentReceipt.id.desc()).first()
    if last_receipt:
        match = re.search(r'PR-(\d+)', last_receipt.receipt_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"PR-{next_num:04d}"


def generate_reconciliation_number(db: Session) -> str:
    """Generate next reconciliation number"""
    last_rec = db.query(DBAccountReconciliation).order_by(DBAccountReconciliation.id.desc()).first()
    if last_rec:
        match = re.search(r'REC-(\d+)', last_rec.reconciliation_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"REC-{next_num:04d}"


def calculate_aging_bucket(days_overdue: int) -> str:
    """Calculate aging bucket based on days overdue"""
    if days_overdue < 0:
        return "current"
    elif days_overdue <= 30:
        return "0-30"
    elif days_overdue <= 60:
        return "31-60"
    elif days_overdue <= 90:
        return "61-90"
    else:
        return "90+"


def update_account_receivable(db: Session, invoice_id: int):
    """Update or create account receivable record for an invoice"""
    invoice = db.query(DBTaxInvoice).filter(DBTaxInvoice.id == invoice_id).first()
    if not invoice:
        return
    
    # Calculate total paid
    allocations = db.query(DBPaymentAllocation).filter(
        DBPaymentAllocation.tax_invoice_id == invoice_id
    ).all()
    total_paid = sum(Decimal(str(alloc.allocated_amount)) for alloc in allocations)
    
    outstanding = Decimal(str(invoice.grand_total)) - total_paid
    
    # Calculate days overdue
    due_date = None
    days_overdue = 0
    if invoice.payment_terms:
        # Try to parse payment terms (e.g., "Net 30", "Credit 45 days")
        match = re.search(r'(\d+)', invoice.payment_terms)
        if match:
            days = int(match.group(1))
            due_date = invoice.invoice_date + timedelta(days=days)
            if due_date < date.today():
                days_overdue = (date.today() - due_date).days
    
    aging_bucket = calculate_aging_bucket(days_overdue)
    
    # Determine status
    if outstanding <= Decimal("0.01"):  # Consider paid if less than 1 paisa
        status = "paid"
    elif total_paid > Decimal("0"):
        status = "partially_paid"
    elif days_overdue > 0:
        status = "overdue"
    else:
        status = "outstanding"
    
    # Get or create receivable record
    receivable = db.query(DBAccountReceivable).filter(
        DBAccountReceivable.tax_invoice_id == invoice_id
    ).first()
    
    if receivable:
        receivable.total_paid = total_paid
        receivable.outstanding_amount = outstanding
        receivable.days_overdue = days_overdue
        receivable.aging_bucket = aging_bucket
        receivable.status = status
        receivable.last_payment_date = date.today() if total_paid > 0 else None
    else:
        party = db.query(DBParty).filter(DBParty.id == invoice.party_id).first()
        receivable = DBAccountReceivable(
            tax_invoice_id=invoice_id,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            invoice_amount=invoice.grand_total,
            party_id=invoice.party_id,
            party_name=invoice.party_name,
            payment_terms=invoice.payment_terms,
            due_date=due_date,
            total_paid=total_paid,
            outstanding_amount=outstanding,
            days_overdue=days_overdue,
            aging_bucket=aging_bucket,
            status=status,
            last_payment_date=date.today() if total_paid > 0 else None
        )
        db.add(receivable)
    
    db.commit()


# Payment Receipt Endpoints
@router.get("/payment-receipts", response_model=List[PaymentReceipt])
def get_payment_receipts(
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager),
    status_filter: Optional[str] = None,
    party_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all payment receipts"""
    query = db.query(DBPaymentReceipt)
    if status_filter:
        query = query.filter(DBPaymentReceipt.status == status_filter)
    if party_id:
        query = query.filter(DBPaymentReceipt.party_id == party_id)
    receipts = query.order_by(DBPaymentReceipt.created_at.desc()).offset(skip).limit(limit).all()
    return receipts


@router.get("/payment-receipts/{receipt_id}", response_model=PaymentReceipt)
def get_payment_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Get a specific payment receipt"""
    receipt = db.query(DBPaymentReceipt).filter(DBPaymentReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment receipt not found"
        )
    return receipt


@router.post("/payment-receipts", response_model=PaymentReceipt)
def create_payment_receipt(
    *,
    db: Session = Depends(get_db),
    receipt_data: PaymentReceiptCreate,
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Create a payment receipt"""
    # Generate receipt number
    receipt_number = generate_receipt_number(db)
    
    # Create payment receipt
    db_receipt = DBPaymentReceipt(
        receipt_number=receipt_number,
        tax_invoice_id=receipt_data.tax_invoice_id,
        party_id=receipt_data.party_id,
        party_name=receipt_data.party_name,
        payment_date=receipt_data.payment_date,
        payment_method=receipt_data.payment_method,
        payment_amount=receipt_data.payment_amount,
        bank_name=receipt_data.bank_name,
        cheque_number=receipt_data.cheque_number,
        transaction_reference=receipt_data.transaction_reference,
        bank_account=receipt_data.bank_account,
        status="pending" if receipt_data.payment_method in ["cheque"] else "received",
        allocated_amount=Decimal("0.00"),
        unallocated_amount=receipt_data.payment_amount,
        remarks=receipt_data.remarks,
        created_by=current_user.id
    )
    
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    
    return db_receipt


@router.put("/payment-receipts/{receipt_id}", response_model=PaymentReceipt)
def update_payment_receipt(
    receipt_id: int,
    *,
    db: Session = Depends(get_db),
    receipt_update: PaymentReceiptUpdate,
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Update a payment receipt"""
    receipt = db.query(DBPaymentReceipt).filter(DBPaymentReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment receipt not found"
        )
    
    update_data = receipt_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(receipt, field, value)
    
    # If status changed to cleared, update cleared_date
    if receipt_update.status == "cleared" and not receipt.cleared_date:
        receipt.cleared_date = date.today()
    
    db.commit()
    db.refresh(receipt)
    
    return receipt


# Payment Allocation Endpoints
@router.post("/payment-allocations", response_model=PaymentAllocation)
def create_payment_allocation(
    *,
    db: Session = Depends(get_db),
    allocation_data: PaymentAllocationCreate,
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Allocate payment to an invoice"""
    # Verify payment receipt exists
    payment_receipt = db.query(DBPaymentReceipt).filter(
        DBPaymentReceipt.id == allocation_data.payment_receipt_id
    ).first()
    if not payment_receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment receipt not found"
        )
    
    # Verify invoice exists
    invoice = db.query(DBTaxInvoice).filter(
        DBTaxInvoice.id == allocation_data.tax_invoice_id
    ).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax invoice not found"
        )
    
    # Check if allocation amount is valid
    allocated_amount = Decimal(str(allocation_data.allocated_amount))
    if allocated_amount > payment_receipt.unallocated_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Allocation amount exceeds unallocated amount. Available: {payment_receipt.unallocated_amount}"
        )
    
    # Check if allocation exceeds invoice outstanding
    existing_allocations = db.query(DBPaymentAllocation).filter(
        DBPaymentAllocation.tax_invoice_id == allocation_data.tax_invoice_id
    ).all()
    total_allocated = sum(Decimal(str(alloc.allocated_amount)) for alloc in existing_allocations)
    invoice_outstanding = invoice.grand_total - total_allocated
    
    if allocated_amount > invoice_outstanding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Allocation amount exceeds invoice outstanding. Outstanding: {invoice_outstanding}"
        )
    
    # Create allocation
    db_allocation = DBPaymentAllocation(
        payment_receipt_id=allocation_data.payment_receipt_id,
        tax_invoice_id=allocation_data.tax_invoice_id,
        allocated_amount=allocated_amount,
        allocation_date=allocation_data.allocation_date,
        remarks=allocation_data.remarks,
        created_by=current_user.id
    )
    
    db.add(db_allocation)
    
    # Update payment receipt
    payment_receipt.allocated_amount += allocated_amount
    payment_receipt.unallocated_amount -= allocated_amount
    
    # Update account receivable
    update_account_receivable(db, allocation_data.tax_invoice_id)
    
    db.commit()
    db.refresh(db_allocation)
    
    return db_allocation


@router.get("/payment-allocations", response_model=List[PaymentAllocation])
def get_payment_allocations(
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager),
    payment_receipt_id: Optional[int] = None,
    tax_invoice_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get payment allocations"""
    query = db.query(DBPaymentAllocation)
    if payment_receipt_id:
        query = query.filter(DBPaymentAllocation.payment_receipt_id == payment_receipt_id)
    if tax_invoice_id:
        query = query.filter(DBPaymentAllocation.tax_invoice_id == tax_invoice_id)
    allocations = query.order_by(DBPaymentAllocation.created_at.desc()).offset(skip).limit(limit).all()
    return allocations


# Account Receivable Endpoints
@router.get("/receivables", response_model=List[AccountReceivable])
def get_receivables(
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager),
    party_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    aging_bucket: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all account receivables"""
    query = db.query(DBAccountReceivable)
    if party_id:
        query = query.filter(DBAccountReceivable.party_id == party_id)
    if status_filter:
        query = query.filter(DBAccountReceivable.status == status_filter)
    if aging_bucket:
        query = query.filter(DBAccountReceivable.aging_bucket == aging_bucket)
    receivables = query.order_by(DBAccountReceivable.invoice_date.desc()).offset(skip).limit(limit).all()
    return receivables


@router.get("/receivables/{receivable_id}", response_model=AccountReceivable)
def get_receivable(
    receivable_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Get a specific account receivable"""
    receivable = db.query(DBAccountReceivable).filter(DBAccountReceivable.id == receivable_id).first()
    if not receivable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account receivable not found"
        )
    return receivable


@router.post("/receivables/sync-invoice/{invoice_id}")
def sync_invoice_to_receivables(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Sync an invoice to account receivables (creates or updates receivable record)"""
    update_account_receivable(db, invoice_id)
    receivable = db.query(DBAccountReceivable).filter(
        DBAccountReceivable.tax_invoice_id == invoice_id
    ).first()
    return {"message": "Invoice synced to receivables", "receivable_id": receivable.id if receivable else None}


# Account Reconciliation Endpoints
@router.get("/reconciliations", response_model=List[AccountReconciliation])
def get_reconciliations(
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager),
    party_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all account reconciliations"""
    query = db.query(DBAccountReconciliation)
    if party_id:
        query = query.filter(DBAccountReconciliation.party_id == party_id)
    if status_filter:
        query = query.filter(DBAccountReconciliation.status == status_filter)
    reconciliations = query.order_by(DBAccountReconciliation.created_at.desc()).offset(skip).limit(limit).all()
    return reconciliations


@router.get("/reconciliations/{reconciliation_id}", response_model=AccountReconciliation)
def get_reconciliation(
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Get a specific account reconciliation"""
    reconciliation = db.query(DBAccountReconciliation).filter(
        DBAccountReconciliation.id == reconciliation_id
    ).first()
    if not reconciliation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account reconciliation not found"
        )
    return reconciliation


@router.post("/reconciliations", response_model=AccountReconciliation)
def create_reconciliation(
    *,
    db: Session = Depends(get_db),
    reconciliation_data: AccountReconciliationCreate,
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Create an account reconciliation"""
    # Generate reconciliation number
    reconciliation_number = generate_reconciliation_number(db)
    
    # Calculate summary if not provided
    if reconciliation_data.party_id:
        # Party-specific reconciliation
        invoices = db.query(DBTaxInvoice).filter(
            DBTaxInvoice.party_id == reconciliation_data.party_id,
            DBTaxInvoice.invoice_date >= reconciliation_data.period_start,
            DBTaxInvoice.invoice_date <= reconciliation_data.period_end
        ).all()
        invoices_issued = sum(Decimal(str(inv.grand_total)) for inv in invoices)
        
        payments = db.query(DBPaymentReceipt).filter(
            DBPaymentReceipt.party_id == reconciliation_data.party_id,
            DBPaymentReceipt.payment_date >= reconciliation_data.period_start,
            DBPaymentReceipt.payment_date <= reconciliation_data.period_end,
            DBPaymentReceipt.status.in_(["received", "cleared"])
        ).all()
        payments_received = sum(Decimal(str(pay.payment_amount)) for pay in payments)
    else:
        # Overall reconciliation
        invoices = db.query(DBTaxInvoice).filter(
            DBTaxInvoice.invoice_date >= reconciliation_data.period_start,
            DBTaxInvoice.invoice_date <= reconciliation_data.period_end
        ).all()
        invoices_issued = sum(Decimal(str(inv.grand_total)) for inv in invoices)
        
        payments = db.query(DBPaymentReceipt).filter(
            DBPaymentReceipt.payment_date >= reconciliation_data.period_start,
            DBPaymentReceipt.payment_date <= reconciliation_data.period_end,
            DBPaymentReceipt.status.in_(["received", "cleared"])
        ).all()
        payments_received = sum(Decimal(str(pay.payment_amount)) for pay in payments)
    
    closing_balance = reconciliation_data.opening_balance + invoices_issued - payments_received
    discrepancies = closing_balance - (reconciliation_data.opening_balance + invoices_issued - payments_received)
    
    db_reconciliation = DBAccountReconciliation(
        reconciliation_number=reconciliation_number,
        reconciliation_date=reconciliation_data.reconciliation_date,
        period_start=reconciliation_data.period_start,
        period_end=reconciliation_data.period_end,
        party_id=reconciliation_data.party_id,
        opening_balance=reconciliation_data.opening_balance,
        invoices_issued=invoices_issued,
        payments_received=payments_received,
        closing_balance=closing_balance,
        discrepancies=discrepancies,
        status="draft",
        remarks=reconciliation_data.remarks,
        created_by=current_user.id
    )
    
    db.add(db_reconciliation)
    db.commit()
    db.refresh(db_reconciliation)
    
    return db_reconciliation


@router.post("/reconciliations/{reconciliation_id}/approve", response_model=AccountReconciliation)
def approve_reconciliation(
    reconciliation_id: int,
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Approve an account reconciliation"""
    reconciliation = db.query(DBAccountReconciliation).filter(
        DBAccountReconciliation.id == reconciliation_id
    ).first()
    if not reconciliation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account reconciliation not found"
        )
    
    if reconciliation.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft reconciliations can be approved"
        )
    
    reconciliation.status = "approved"
    reconciliation.approved_by = current_user.id
    reconciliation.approved_at = datetime.now()
    
    db.commit()
    db.refresh(reconciliation)
    
    return reconciliation


# Dashboard and Reports
@router.get("/dashboard/stats", response_model=AccountsDashboardStats)
def get_accounts_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Get accounts dashboard statistics"""
    # Total outstanding
    receivables = db.query(DBAccountReceivable).filter(
        DBAccountReceivable.status.in_(["outstanding", "partially_paid", "overdue"])
    ).all()
    total_outstanding = sum(Decimal(str(rec.outstanding_amount)) for rec in receivables)
    
    # Overdue amount
    overdue_receivables = db.query(DBAccountReceivable).filter(
        DBAccountReceivable.status == "overdue"
    ).all()
    overdue_amount = sum(Decimal(str(rec.outstanding_amount)) for rec in overdue_receivables)
    
    # Payments received today
    payments_today = db.query(DBPaymentReceipt).filter(
        DBPaymentReceipt.payment_date == date.today(),
        DBPaymentReceipt.status.in_(["received", "cleared"])
    ).all()
    payments_received_today = sum(Decimal(str(pay.payment_amount)) for pay in payments_today)
    
    # Payments received this month
    month_start = date.today().replace(day=1)
    payments_month = db.query(DBPaymentReceipt).filter(
        DBPaymentReceipt.payment_date >= month_start,
        DBPaymentReceipt.payment_date <= date.today(),
        DBPaymentReceipt.status.in_(["received", "cleared"])
    ).all()
    payments_received_this_month = sum(Decimal(str(pay.payment_amount)) for pay in payments_month)
    
    # Pending payments (cheques not cleared)
    pending_payments = db.query(DBPaymentReceipt).filter(
        DBPaymentReceipt.status == "pending"
    ).count()
    
    # Overdue invoices count
    overdue_invoices = db.query(DBAccountReceivable).filter(
        DBAccountReceivable.status == "overdue"
    ).count()
    
    # Aging summary
    aging_summary = {
        "current": Decimal("0.00"),
        "0-30": Decimal("0.00"),
        "31-60": Decimal("0.00"),
        "61-90": Decimal("0.00"),
        "90+": Decimal("0.00")
    }
    
    for rec in receivables:
        bucket = rec.aging_bucket or "current"
        if bucket in aging_summary:
            aging_summary[bucket] += Decimal(str(rec.outstanding_amount))
    
    return {
        "total_outstanding": total_outstanding,
        "overdue_amount": overdue_amount,
        "payments_received_today": payments_received_today,
        "payments_received_this_month": payments_received_this_month,
        "pending_payments": pending_payments,
        "overdue_invoices": overdue_invoices,
        "aging_summary": aging_summary
    }


@router.get("/aging-analysis", response_model=List[AgingAnalysis])
def get_aging_analysis(
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager),
    party_id: Optional[int] = None
) -> Any:
    """Get aging analysis by party"""
    query = db.query(DBAccountReceivable)
    if party_id:
        query = query.filter(DBAccountReceivable.party_id == party_id)
    
    receivables = query.filter(
        DBAccountReceivable.status.in_(["outstanding", "partially_paid", "overdue"])
    ).all()
    
    # Group by party
    party_data = {}
    for rec in receivables:
        if rec.party_id not in party_data:
            party_data[rec.party_id] = {
                "party_id": rec.party_id,
                "party_name": rec.party_name,
                "total_outstanding": Decimal("0.00"),
                "current": Decimal("0.00"),
                "days_0_30": Decimal("0.00"),
                "days_31_60": Decimal("0.00"),
                "days_61_90": Decimal("0.00"),
                "days_90_plus": Decimal("0.00")
            }
        
        party_data[rec.party_id]["total_outstanding"] += Decimal(str(rec.outstanding_amount))
        bucket = rec.aging_bucket or "current"
        
        if bucket == "current":
            party_data[rec.party_id]["current"] += Decimal(str(rec.outstanding_amount))
        elif bucket == "0-30":
            party_data[rec.party_id]["days_0_30"] += Decimal(str(rec.outstanding_amount))
        elif bucket == "31-60":
            party_data[rec.party_id]["days_31_60"] += Decimal(str(rec.outstanding_amount))
        elif bucket == "61-90":
            party_data[rec.party_id]["days_61_90"] += Decimal(str(rec.outstanding_amount))
        elif bucket == "90+":
            party_data[rec.party_id]["days_90_plus"] += Decimal(str(rec.outstanding_amount))
    
    return list(party_data.values())

