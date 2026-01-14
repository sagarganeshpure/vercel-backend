from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import json
import re

from app.schemas.billing import (
    BillingRequest, BillingRequestCreate, BillingRequestItem,
    DeliveryChallan, DeliveryChallanCreate, DeliveryChallanUpdate,
    TaxInvoice, TaxInvoiceCreate, TaxInvoiceUpdate,
    TallySync, TallySyncCreate
)
from app.db.models.billing import (
    BillingRequest as DBBillingRequest,
    DeliveryChallan as DBDeliveryChallan,
    TaxInvoice as DBTaxInvoice,
    TallySync as DBTallySync
)
from app.db.models.user import ProductionPaper as DBProductionPaper, Party as DBParty
from app.api.deps import get_db, get_billing_executive, get_accounts_manager, get_dispatch_executive

router = APIRouter()


# Helper Functions
def generate_dc_number(db: Session) -> str:
    """Generate next DC number"""
    last_dc = db.query(DBDeliveryChallan).order_by(DBDeliveryChallan.id.desc()).first()
    if last_dc:
        match = re.search(r'DC-(\d+)', last_dc.dc_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"DC-{next_num:04d}"


def generate_invoice_number(db: Session) -> str:
    """Generate next Invoice number"""
    last_inv = db.query(DBTaxInvoice).order_by(DBTaxInvoice.id.desc()).first()
    if last_inv:
        match = re.search(r'INV-(\d+)', last_inv.invoice_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"INV-{next_num:04d}"


def generate_dispatch_request_no(db: Session) -> str:
    """Generate next Dispatch Request number"""
    last_req = db.query(DBBillingRequest).order_by(DBBillingRequest.id.desc()).first()
    if last_req:
        match = re.search(r'DR-(\d+)', last_req.dispatch_request_no)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"DR-{next_num:04d}"


# Billing Request Endpoints
@router.get("/billing-requests", response_model=List[BillingRequest])
def get_billing_requests(
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all billing requests"""
    query = db.query(DBBillingRequest)
    if status_filter:
        query = query.filter(DBBillingRequest.status == status_filter)
    requests = query.order_by(DBBillingRequest.created_at.desc()).offset(skip).limit(limit).all()
    return requests


@router.get("/billing-requests/{request_id}", response_model=BillingRequest)
def get_billing_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive)
) -> Any:
    """Get a specific billing request"""
    request = db.query(DBBillingRequest).filter(DBBillingRequest.id == request_id).first()
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing request not found"
        )
    return request


@router.get("/pending-billing-requests", response_model=List[Any])
def get_pending_billing_requests(
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get production papers that are QC approved and ready for billing"""
    # Get production papers with status "ready_for_dispatch"
    papers = db.query(DBProductionPaper).filter(
        DBProductionPaper.status == "ready_for_dispatch"
    ).offset(skip).limit(limit).all()
    
    result = []
    for paper in papers:
        # Check if billing request already exists
        existing_request = db.query(DBBillingRequest).filter(
            DBBillingRequest.production_paper_id == paper.id
        ).first()
        
        if not existing_request:
            party = db.query(DBParty).filter(DBParty.id == paper.party_id).first() if paper.party_id else None
            
            result.append({
                "production_paper_id": paper.id,
                "production_paper_number": paper.paper_number,
                "party_id": paper.party_id,
                "party_name": paper.party_name or (party.name if party else None),
                "party_gstin": party.gstin_number if party else None,
                "project_site_name": paper.project_site_name,
                "product_category": paper.product_category,
                "product_type": paper.product_type,
                "product_sub_type": paper.product_sub_type,
                "order_type": paper.order_type,
                "expected_dispatch_date": paper.expected_dispatch_date,
                "status": "Ready for Billing"
            })
    
    return result


@router.post("/billing-requests", response_model=BillingRequest)
def create_billing_request(
    *,
    db: Session = Depends(get_db),
    request_data: BillingRequestCreate,
    current_user = Depends(get_dispatch_executive)  # Dispatch creates billing requests
) -> Any:
    """Create a billing request (typically created by Dispatch department)"""
    # Verify production paper exists and is ready
    paper = db.query(DBProductionPaper).filter(
        DBProductionPaper.id == request_data.production_paper_id
    ).first()
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production paper not found"
        )
    
    if paper.status != "ready_for_dispatch":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Production paper is not ready for dispatch"
        )
    
    # Check if billing request already exists
    existing = db.query(DBBillingRequest).filter(
        DBBillingRequest.production_paper_id == request_data.production_paper_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing request already exists for this production paper"
        )
    
    # Generate dispatch request number if not provided
    if not request_data.dispatch_request_no:
        request_data.dispatch_request_no = generate_dispatch_request_no(db)
    
    # Create billing request
    db_request = DBBillingRequest(
        dispatch_request_no=request_data.dispatch_request_no,
        production_paper_id=request_data.production_paper_id,
        production_paper_number=request_data.production_paper_number,
        party_id=request_data.party_id,
        party_name=request_data.party_name,
        party_gstin=request_data.party_gstin,
        site_name=request_data.site_name,
        delivery_address=request_data.delivery_address,
        vehicle_no=request_data.vehicle_no,
        driver_name=request_data.driver_name,
        dispatch_date=request_data.dispatch_date,
        items=json.dumps([item.model_dump() for item in request_data.items]),
        status="pending",
        created_by=current_user.id
    )
    
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    return db_request


# Delivery Challan Endpoints
@router.get("/delivery-challans", response_model=List[DeliveryChallan])
def get_delivery_challans(
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all delivery challans"""
    query = db.query(DBDeliveryChallan)
    if status_filter:
        query = query.filter(DBDeliveryChallan.status == status_filter)
    challans = query.order_by(DBDeliveryChallan.created_at.desc()).offset(skip).limit(limit).all()
    return challans


@router.get("/delivery-challans/{dc_id}", response_model=DeliveryChallan)
def get_delivery_challan(
    dc_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive)
) -> Any:
    """Get a specific delivery challan"""
    dc = db.query(DBDeliveryChallan).filter(DBDeliveryChallan.id == dc_id).first()
    if not dc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery challan not found"
        )
    return dc


@router.post("/delivery-challans", response_model=DeliveryChallan)
def create_delivery_challan(
    *,
    db: Session = Depends(get_db),
    dc_data: DeliveryChallanCreate,
    current_user = Depends(get_billing_executive)
) -> Any:
    """Create a delivery challan"""
    # Verify billing request exists
    billing_request = db.query(DBBillingRequest).filter(
        DBBillingRequest.id == dc_data.billing_request_id
    ).first()
    
    if not billing_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing request not found"
        )
    
    # Generate DC number
    dc_number = generate_dc_number(db)
    
    # Create delivery challan
    db_dc = DBDeliveryChallan(
        dc_number=dc_number,
        billing_request_id=dc_data.billing_request_id,
        dispatch_request_no=dc_data.dispatch_request_no,
        party_id=dc_data.party_id,
        party_name=dc_data.party_name,
        delivery_address=dc_data.delivery_address,
        vehicle_no=dc_data.vehicle_no,
        driver_name=dc_data.driver_name,
        dc_date=dc_data.dc_date,
        line_items=json.dumps([item.model_dump() for item in dc_data.line_items]),
        remarks=dc_data.remarks,
        status="draft",
        created_by=current_user.id
    )
    
    db.add(db_dc)
    
    # Update billing request status
    billing_request.status = "dc_created"
    
    db.commit()
    db.refresh(db_dc)
    
    return db_dc


@router.put("/delivery-challans/{dc_id}", response_model=DeliveryChallan)
def update_delivery_challan(
    dc_id: int,
    *,
    db: Session = Depends(get_db),
    dc_update: DeliveryChallanUpdate,
    current_user = Depends(get_billing_executive)
) -> Any:
    """Update a delivery challan"""
    dc = db.query(DBDeliveryChallan).filter(DBDeliveryChallan.id == dc_id).first()
    if not dc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery challan not found"
        )
    
    if dc.status == "sent_to_dispatch":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update DC that has been sent to dispatch"
        )
    
    update_data = dc_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dc, field, value)
    
    db.commit()
    db.refresh(dc)
    
    return dc


@router.post("/delivery-challans/{dc_id}/approve", response_model=DeliveryChallan)
def approve_delivery_challan(
    dc_id: int,
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Approve a delivery challan (Accounts Manager only)"""
    dc = db.query(DBDeliveryChallan).filter(DBDeliveryChallan.id == dc_id).first()
    if not dc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery challan not found"
        )
    
    dc.status = "approved"
    dc.approved_by = current_user.id
    dc.approved_at = datetime.now()
    
    db.commit()
    db.refresh(dc)
    
    return dc


# Tax Invoice Endpoints
@router.get("/tax-invoices", response_model=List[TaxInvoice])
def get_tax_invoices(
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all tax invoices"""
    query = db.query(DBTaxInvoice)
    if status_filter:
        query = query.filter(DBTaxInvoice.status == status_filter)
    invoices = query.order_by(DBTaxInvoice.created_at.desc()).offset(skip).limit(limit).all()
    return invoices


@router.get("/tax-invoices/{invoice_id}", response_model=TaxInvoice)
def get_tax_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive)
) -> Any:
    """Get a specific tax invoice"""
    invoice = db.query(DBTaxInvoice).filter(DBTaxInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax invoice not found"
        )
    return invoice


@router.post("/tax-invoices", response_model=TaxInvoice)
def create_tax_invoice(
    *,
    db: Session = Depends(get_db),
    invoice_data: TaxInvoiceCreate,
    current_user = Depends(get_billing_executive)
) -> Any:
    """Create a tax invoice"""
    # Verify billing request exists
    billing_request = db.query(DBBillingRequest).filter(
        DBBillingRequest.id == invoice_data.billing_request_id
    ).first()
    
    if not billing_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing request not found"
        )
    
    # Check credit limit if party has credit terms
    party = db.query(DBParty).filter(DBParty.id == invoice_data.party_id).first()
    credit_limit_exceeded = False
    outstanding_amount = Decimal("0.00")
    
    if party and party.credit_limit:
        try:
            credit_limit = Decimal(str(party.credit_limit))
            # Calculate outstanding from unpaid invoices
            unpaid_invoices = db.query(DBTaxInvoice).filter(
                DBTaxInvoice.party_id == invoice_data.party_id,
                DBTaxInvoice.status.in_(["approved", "sent_to_dispatch"])
            ).all()
            
            outstanding_amount = sum(Decimal(str(inv.grand_total)) for inv in unpaid_invoices)
            
            # Calculate new total
            new_total = sum(Decimal(str(item.taxable_value)) + Decimal(str(item.cgst_amount)) + 
                          Decimal(str(item.sgst_amount)) + Decimal(str(item.igst_amount)) 
                          for item in invoice_data.line_items)
            new_total += invoice_data.freight or Decimal("0.00")
            new_total += invoice_data.round_off or Decimal("0.00")
            
            if outstanding_amount + new_total > credit_limit:
                credit_limit_exceeded = True
        except:
            pass
    
    # Calculate totals
    subtotal = sum(Decimal(str(item.taxable_value)) for item in invoice_data.line_items)
    cgst_total = sum(Decimal(str(item.cgst_amount)) for item in invoice_data.line_items)
    sgst_total = sum(Decimal(str(item.sgst_amount)) for item in invoice_data.line_items)
    igst_total = sum(Decimal(str(item.igst_amount)) for item in invoice_data.line_items)
    
    freight = invoice_data.freight or Decimal("0.00")
    round_off = invoice_data.round_off or Decimal("0.00")
    grand_total = subtotal + cgst_total + sgst_total + igst_total + freight + round_off
    
    # Generate invoice number
    invoice_number = generate_invoice_number(db)
    
    # Create tax invoice
    db_invoice = DBTaxInvoice(
        invoice_number=invoice_number,
        billing_request_id=invoice_data.billing_request_id,
        delivery_challan_id=invoice_data.delivery_challan_id,
        dispatch_request_no=invoice_data.dispatch_request_no,
        party_id=invoice_data.party_id,
        party_name=invoice_data.party_name,
        party_gstin=invoice_data.party_gstin,
        place_of_supply=invoice_data.place_of_supply,
        state_code=invoice_data.state_code,
        invoice_date=invoice_data.invoice_date,
        payment_terms=invoice_data.payment_terms,
        dc_reference=invoice_data.dc_reference,
        line_items=json.dumps([item.model_dump() for item in invoice_data.line_items]),
        subtotal=subtotal,
        cgst_total=cgst_total,
        sgst_total=sgst_total,
        igst_total=igst_total,
        freight=freight,
        round_off=round_off,
        grand_total=grand_total,
        status="draft",
        credit_limit_check=bool(party and party.credit_limit),
        credit_limit_exceeded=credit_limit_exceeded,
        outstanding_amount=outstanding_amount,
        remarks=invoice_data.remarks,
        created_by=current_user.id
    )
    
    db.add(db_invoice)
    
    # Update billing request status
    billing_request.status = "invoice_created"
    
    db.commit()
    db.refresh(db_invoice)
    
    return db_invoice


@router.put("/tax-invoices/{invoice_id}", response_model=TaxInvoice)
def update_tax_invoice(
    invoice_id: int,
    *,
    db: Session = Depends(get_db),
    invoice_update: TaxInvoiceUpdate,
    current_user = Depends(get_billing_executive)
) -> Any:
    """Update a tax invoice"""
    invoice = db.query(DBTaxInvoice).filter(DBTaxInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax invoice not found"
        )
    
    if invoice.status == "sent_to_dispatch":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update invoice that has been sent to dispatch"
        )
    
    update_data = invoice_update.model_dump(exclude_unset=True)
    
    # Recalculate totals if freight or round_off changed
    if "freight" in update_data or "round_off" in update_data:
        freight = update_data.get("freight", invoice.freight) or Decimal("0.00")
        round_off = update_data.get("round_off", invoice.round_off) or Decimal("0.00")
        invoice.grand_total = invoice.subtotal + invoice.cgst_total + invoice.sgst_total + invoice.igst_total + freight + round_off
        invoice.freight = freight
        invoice.round_off = round_off
    
    for field, value in update_data.items():
        if field not in ["freight", "round_off"]:
            setattr(invoice, field, value)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.post("/tax-invoices/{invoice_id}/approve", response_model=TaxInvoice)
def approve_tax_invoice(
    invoice_id: int,
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Approve a tax invoice (Accounts Manager only)"""
    invoice = db.query(DBTaxInvoice).filter(DBTaxInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax invoice not found"
        )
    
    if invoice.credit_limit_exceeded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve invoice: Credit limit exceeded"
        )
    
    invoice.status = "approved"
    invoice.approved_by = current_user.id
    invoice.approved_at = datetime.now()
    
    # Update billing request status
    billing_request = db.query(DBBillingRequest).filter(
        DBBillingRequest.id == invoice.billing_request_id
    ).first()
    if billing_request:
        billing_request.status = "billing_approved"
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.post("/tax-invoices/{invoice_id}/send-to-dispatch", response_model=TaxInvoice)
def send_invoice_to_dispatch(
    invoice_id: int,
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_accounts_manager)
) -> Any:
    """Send approved invoice to dispatch"""
    invoice = db.query(DBTaxInvoice).filter(DBTaxInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax invoice not found"
        )
    
    if invoice.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must be approved before sending to dispatch"
        )
    
    invoice.status = "sent_to_dispatch"
    
    # Update billing request status
    billing_request = db.query(DBBillingRequest).filter(
        DBBillingRequest.id == invoice.billing_request_id
    ).first()
    if billing_request:
        billing_request.status = "sent_to_dispatch"
    
    # Update DC status if exists
    if invoice.delivery_challan_id:
        dc = db.query(DBDeliveryChallan).filter(DBDeliveryChallan.id == invoice.delivery_challan_id).first()
        if dc:
            dc.status = "sent_to_dispatch"
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


# Dashboard Stats
@router.get("/dashboard/stats")
def get_billing_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_billing_executive)
) -> Any:
    """Get billing dashboard statistics"""
    pending_requests = db.query(DBBillingRequest).filter(
        DBBillingRequest.status == "pending"
    ).count()
    
    dc_created_pending_invoice = db.query(DBBillingRequest).filter(
        DBBillingRequest.status == "dc_created"
    ).count()
    
    invoices_today = db.query(DBTaxInvoice).filter(
        DBTaxInvoice.invoice_date == date.today()
    ).count()
    
    ready_for_dispatch = db.query(DBBillingRequest).filter(
        DBBillingRequest.status == "sent_to_dispatch"
    ).count()
    
    # Calculate outstanding amount
    outstanding_invoices = db.query(DBTaxInvoice).filter(
        DBTaxInvoice.status.in_(["approved", "sent_to_dispatch"])
    ).all()
    outstanding_amount = sum(float(inv.grand_total) for inv in outstanding_invoices)
    
    return {
        "pending_billing_requests": pending_requests,
        "dc_created_pending_invoice": dc_created_pending_invoice,
        "invoices_created_today": invoices_today,
        "ready_for_dispatch": ready_for_dispatch,
        "outstanding_amount": outstanding_amount
    }

