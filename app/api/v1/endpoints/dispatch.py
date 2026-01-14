from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from datetime import datetime, date
import json
import re

from app.schemas.dispatch import (
    Dispatch, DispatchCreate, DispatchUpdate, DispatchItem,
    GatePass, GatePassCreate, GatePassVerify,
    DeliveryTracking, DeliveryTrackingCreate, DeliveryTrackingUpdate,
    ReadyForDispatch
)
from app.db.models.dispatch import (
    Dispatch as DBDispatch,
    DispatchItem as DBDispatchItem,
    GatePass as DBGatePass,
    DeliveryTracking as DBDeliveryTracking
)
from app.db.models.billing import (
    BillingRequest as DBBillingRequest,
    DeliveryChallan as DBDeliveryChallan,
    TaxInvoice as DBTaxInvoice
)
from app.db.models.user import ProductionPaper as DBProductionPaper, Party as DBParty
from app.db.models.quality_check import QualityCheck as DBQualityCheck
from app.api.deps import get_db, get_dispatch_executive, get_dispatch_supervisor, get_logistics_manager, get_current_user

router = APIRouter()


# Helper Functions
def generate_dispatch_number(db: Session) -> str:
    """Generate next Dispatch number"""
    last_dispatch = db.query(DBDispatch).order_by(DBDispatch.id.desc()).first()
    if last_dispatch:
        match = re.search(r'DSP-(\d+)', last_dispatch.dispatch_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"DSP-{next_num:04d}"


def generate_gate_pass_number(db: Session) -> str:
    """Generate next Gate Pass number"""
    last_gp = db.query(DBGatePass).order_by(DBGatePass.id.desc()).first()
    if last_gp:
        match = re.search(r'GP-(\d+)', last_gp.gate_pass_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"GP-{next_num:04d}"


# Dashboard Stats
@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive)
) -> Any:
    """Get dispatch dashboard statistics"""
    # Ready for Dispatch (QC + Billing Approved)
    ready_count = db.query(DBProductionPaper).filter(
        DBProductionPaper.status == "ready_for_dispatch"
    ).count()
    
    # Check billing approval
    billing_approved_papers = []
    papers = db.query(DBProductionPaper).filter(
        DBProductionPaper.status == "ready_for_dispatch"
    ).all()
    
    for paper in papers:
        billing_request = db.query(DBBillingRequest).filter(
            DBBillingRequest.production_paper_id == paper.id,
            DBBillingRequest.status.in_(["billing_approved", "sent_to_dispatch"])
        ).first()
        if billing_request:
            billing_approved_papers.append(paper.id)
    
    ready_for_dispatch = len(billing_approved_papers)
    
    # Dispatch Pending
    pending_count = db.query(DBDispatch).filter(
        DBDispatch.status == "draft"
    ).count()
    
    # Dispatched Today
    today = date.today()
    dispatched_today = db.query(DBDispatch).filter(
        DBDispatch.dispatch_date == today,
        DBDispatch.status.in_(["dispatched", "in_transit"])
    ).count()
    
    # Pending Delivery
    pending_delivery = db.query(DBDispatch).filter(
        DBDispatch.status.in_(["dispatched", "in_transit"])
    ).count()
    
    # Delivery Delayed
    delayed = db.query(DBDispatch).filter(
        DBDispatch.status == "delayed"
    ).count()
    
    return {
        "ready_for_dispatch": ready_for_dispatch,
        "dispatch_pending": pending_count,
        "dispatched_today": dispatched_today,
        "pending_delivery": pending_delivery,
        "delivery_delayed": delayed
    }


# Ready for Dispatch (Auto-filtered by QC + Billing)
@router.get("/ready-for-dispatch", response_model=List[ReadyForDispatch])
def get_ready_for_dispatch(
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get production papers ready for dispatch (QC approved + Billing approved)"""
    # Get QC approved papers
    qc_approved_papers = db.query(DBQualityCheck).filter(
        DBQualityCheck.qc_status == "approved"
    ).all()
    
    qc_approved_paper_ids = [qc.production_paper_id for qc in qc_approved_papers]
    
    if not qc_approved_paper_ids:
        return []
    
    # Get production papers with QC approval
    papers = db.query(DBProductionPaper).filter(
        DBProductionPaper.id.in_(qc_approved_paper_ids),
        DBProductionPaper.status == "ready_for_dispatch"
    ).offset(skip).limit(limit).all()
    
    result = []
    for paper in papers:
        # Check if billing is approved
        billing_request = db.query(DBBillingRequest).filter(
            DBBillingRequest.production_paper_id == paper.id,
            DBBillingRequest.status.in_(["billing_approved", "sent_to_dispatch"])
        ).first()
        
        if not billing_request:
            continue
        
        # Get DC and Invoice
        dc = db.query(DBDeliveryChallan).filter(
            DBDeliveryChallan.billing_request_id == billing_request.id,
            DBDeliveryChallan.status == "approved"
        ).first()
        
        invoice = db.query(DBTaxInvoice).filter(
            DBTaxInvoice.billing_request_id == billing_request.id,
            DBTaxInvoice.status.in_(["approved", "sent_to_dispatch"])
        ).first()
        
        # Check if dispatch already exists
        existing_dispatch = db.query(DBDispatch).filter(
            DBDispatch.production_paper_id == paper.id
        ).first()
        
        if existing_dispatch:
            continue
        
        # Get party info
        party = db.query(DBParty).filter(DBParty.id == paper.party_id).first() if paper.party_id else None
        
        # Parse items from billing request
        items = json.loads(billing_request.items) if billing_request.items else []
        
        result.append({
            "production_paper_id": paper.id,
            "production_paper_number": paper.paper_number,
            "party_id": paper.party_id,
            "party_name": paper.party_name or (party.name if party else "Unknown"),
            "delivery_address": billing_request.delivery_address,
            "qc_approved": True,
            "billing_request_id": billing_request.id,
            "dc_number": dc.dc_number if dc else None,
            "invoice_number": invoice.invoice_number if invoice else None,
            "billing_approved": True,
            "items": items
        })
    
    return result


# Dispatch CRUD
@router.get("/dispatches", response_model=List[Dispatch])
def get_dispatches(
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all dispatches"""
    query = db.query(DBDispatch)
    if status_filter:
        query = query.filter(DBDispatch.status == status_filter)
    dispatches = query.order_by(DBDispatch.created_at.desc()).offset(skip).limit(limit).all()
    return dispatches


@router.get("/dispatches/{dispatch_id}", response_model=Dispatch)
def get_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive)
) -> Any:
    """Get a specific dispatch"""
    dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispatch not found"
        )
    return dispatch


@router.post("/dispatches", response_model=Dispatch)
def create_dispatch(
    *,
    db: Session = Depends(get_db),
    dispatch_data: DispatchCreate,
    current_user = Depends(get_dispatch_executive)
) -> Any:
    """Create a new dispatch"""
    # Verify production paper exists
    paper = db.query(DBProductionPaper).filter(
        DBProductionPaper.id == dispatch_data.production_paper_id
    ).first()
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production paper not found"
        )
    
    # Verify QC approval
    qc = db.query(DBQualityCheck).filter(
        DBQualityCheck.production_paper_id == dispatch_data.production_paper_id,
        DBQualityCheck.qc_status == "approved"
    ).first()
    
    if not qc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QC approval required before dispatch"
        )
    
    # Verify billing approval
    billing_request = None
    if dispatch_data.billing_request_id:
        billing_request = db.query(DBBillingRequest).filter(
            DBBillingRequest.id == dispatch_data.billing_request_id
        ).first()
        
        if not billing_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Billing request not found"
            )
        
        if billing_request.status not in ["billing_approved", "sent_to_dispatch"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billing must be approved before dispatch"
            )
    
    # Get DC and Invoice info
    dc_number = None
    invoice_number = None
    
    if dispatch_data.delivery_challan_id:
        dc = db.query(DBDeliveryChallan).filter(
            DBDeliveryChallan.id == dispatch_data.delivery_challan_id
        ).first()
        if dc:
            dc_number = dc.dc_number
    
    if dispatch_data.tax_invoice_id:
        invoice = db.query(DBTaxInvoice).filter(
            DBTaxInvoice.id == dispatch_data.tax_invoice_id
        ).first()
        if invoice:
            invoice_number = invoice.invoice_number
    
    # Generate dispatch number
    dispatch_number = generate_dispatch_number(db)
    
    # Create dispatch
    db_dispatch = DBDispatch(
        dispatch_number=dispatch_number,
        dispatch_request_no=dispatch_data.dispatch_request_no,
        production_paper_id=dispatch_data.production_paper_id,
        production_paper_number=dispatch_data.production_paper_number,
        billing_request_id=dispatch_data.billing_request_id,
        delivery_challan_id=dispatch_data.delivery_challan_id,
        tax_invoice_id=dispatch_data.tax_invoice_id,
        dc_number=dc_number,
        invoice_number=invoice_number,
        party_id=dispatch_data.party_id,
        party_name=dispatch_data.party_name,
        delivery_address=dispatch_data.delivery_address,
        dispatch_date=dispatch_data.dispatch_date,
        expected_delivery_date=dispatch_data.expected_delivery_date,
        vehicle_type=dispatch_data.vehicle_type,
        vehicle_no=dispatch_data.vehicle_no,
        driver_name=dispatch_data.driver_name,
        driver_mobile=dispatch_data.driver_mobile,
        status="draft",
        qc_approved=True,
        billing_approved=True if billing_request else False,
        remarks=dispatch_data.remarks,
        created_by=current_user.id
    )
    
    db.add(db_dispatch)
    db.flush()
    
    # Create dispatch items
    for item_data in dispatch_data.items:
        db_item = DBDispatchItem(
            dispatch_id=db_dispatch.id,
            product_type=item_data.product_type,
            product_description=item_data.product_description,
            quantity=item_data.quantity,
            packaging_type=item_data.packaging_type,
            weight=item_data.weight,
            volume=item_data.volume,
            remarks=item_data.remarks
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_dispatch)
    
    return db_dispatch


@router.put("/dispatches/{dispatch_id}", response_model=Dispatch)
def update_dispatch(
    dispatch_id: int,
    *,
    db: Session = Depends(get_db),
    dispatch_update: DispatchUpdate,
    current_user = Depends(get_dispatch_executive)
) -> Any:
    """Update a dispatch"""
    dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispatch not found"
        )
    
    if dispatch.status not in ["draft", "approved"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update dispatch in current status"
        )
    
    update_data = dispatch_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dispatch, field, value)
    
    db.commit()
    db.refresh(dispatch)
    
    return dispatch


@router.post("/dispatches/{dispatch_id}/approve", response_model=Dispatch)
def approve_dispatch(
    dispatch_id: int,
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_supervisor)
) -> Any:
    """Approve dispatch (Dispatch Supervisor)"""
    dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispatch not found"
        )
    
    if dispatch.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft dispatches can be approved"
        )
    
    dispatch.status = "approved"
    dispatch.approved_by = current_user.id
    dispatch.approved_at = datetime.now()
    
    # Generate gate pass
    gate_pass_number = generate_gate_pass_number(db)
    
    # Create item summary
    items = db.query(DBDispatchItem).filter(DBDispatchItem.dispatch_id == dispatch_id).all()
    item_summary = json.dumps([{
        "product_type": item.product_type,
        "description": item.product_description,
        "quantity": item.quantity
    } for item in items])
    
    gate_pass = DBGatePass(
        gate_pass_number=gate_pass_number,
        dispatch_id=dispatch_id,
        dispatch_number=dispatch.dispatch_number,
        vehicle_no=dispatch.vehicle_no,
        driver_name=dispatch.driver_name,
        driver_mobile=dispatch.driver_mobile,
        item_summary=item_summary,
        verified=False
    )
    
    db.add(gate_pass)
    db.commit()
    db.refresh(dispatch)
    
    return dispatch


@router.post("/dispatches/{dispatch_id}/dispatch", response_model=Dispatch)
def mark_dispatched(
    dispatch_id: int,
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive)
) -> Any:
    """Mark dispatch as dispatched"""
    dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispatch not found"
        )
    
    if dispatch.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dispatch must be approved first"
        )
    
    dispatch.status = "dispatched"
    dispatch.dispatched_at = datetime.now()
    
    # Create delivery tracking
    tracking = db.query(DBDeliveryTracking).filter(
        DBDeliveryTracking.dispatch_id == dispatch_id
    ).first()
    
    if not tracking:
        tracking = DBDeliveryTracking(
            dispatch_id=dispatch_id,
            dispatch_number=dispatch.dispatch_number,
            status="dispatched"
        )
        db.add(tracking)
    
    db.commit()
    db.refresh(dispatch)
    
    return dispatch


# Gate Pass Endpoints
@router.get("/gate-passes", response_model=List[GatePass])
def get_gate_passes(
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all gate passes"""
    gate_passes = db.query(DBGatePass).order_by(
        DBGatePass.created_at.desc()
    ).offset(skip).limit(limit).all()
    return gate_passes


@router.get("/gate-passes/{gate_pass_id}", response_model=GatePass)
def get_gate_pass(
    gate_pass_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive)
) -> Any:
    """Get a specific gate pass"""
    gate_pass = db.query(DBGatePass).filter(DBGatePass.id == gate_pass_id).first()
    if not gate_pass:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gate pass not found"
        )
    return gate_pass


@router.post("/gate-passes/{gate_pass_id}/verify", response_model=GatePass)
def verify_gate_pass(
    gate_pass_id: int,
    *,
    db: Session = Depends(get_db),
    verify_data: GatePassVerify,
    current_user = Depends(get_current_user)  # Security can verify
) -> Any:
    """Verify gate pass (Security)"""
    gate_pass = db.query(DBGatePass).filter(DBGatePass.id == gate_pass_id).first()
    if not gate_pass:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gate pass not found"
        )
    
    gate_pass.verified = verify_data.verified
    gate_pass.verified_by = current_user.id
    gate_pass.time_out = verify_data.time_out or datetime.now()
    gate_pass.verified_at = datetime.now()
    
    db.commit()
    db.refresh(gate_pass)
    
    return gate_pass


# Delivery Tracking Endpoints
@router.get("/delivery-tracking", response_model=List[DeliveryTracking])
def get_delivery_tracking(
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all delivery tracking records"""
    query = db.query(DBDeliveryTracking)
    if status_filter:
        query = query.filter(DBDeliveryTracking.status == status_filter)
    tracking = query.order_by(DBDeliveryTracking.created_at.desc()).offset(skip).limit(limit).all()
    return tracking


@router.get("/delivery-tracking/{dispatch_id}", response_model=DeliveryTracking)
def get_delivery_tracking_by_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_dispatch_executive)
) -> Any:
    """Get delivery tracking for a dispatch"""
    tracking = db.query(DBDeliveryTracking).filter(
        DBDeliveryTracking.dispatch_id == dispatch_id
    ).first()
    
    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery tracking not found"
        )
    
    return tracking


@router.put("/delivery-tracking/{dispatch_id}", response_model=DeliveryTracking)
def update_delivery_tracking(
    dispatch_id: int,
    *,
    db: Session = Depends(get_db),
    tracking_update: DeliveryTrackingUpdate,
    current_user = Depends(get_logistics_manager)  # Logistics updates
) -> Any:
    """Update delivery tracking (Logistics)"""
    tracking = db.query(DBDeliveryTracking).filter(
        DBDeliveryTracking.dispatch_id == dispatch_id
    ).first()
    
    if not tracking:
        # Create if doesn't exist
        dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
        if not dispatch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispatch not found"
            )
        
        tracking = DBDeliveryTracking(
            dispatch_id=dispatch_id,
            dispatch_number=dispatch.dispatch_number,
            status="dispatched"
        )
        db.add(tracking)
    
    update_data = tracking_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tracking, field, value)
    
    tracking.updated_by = current_user.id
    
    # Update dispatch status if delivered
    if tracking_update.status == "delivered":
        dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
        if dispatch:
            dispatch.status = "delivered"
    
    db.commit()
    db.refresh(tracking)
    
    return tracking

