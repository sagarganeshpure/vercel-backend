from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Any, Optional
import json
import re
from datetime import date, datetime
from decimal import Decimal

from app.schemas.purchase import (
    Vendor, VendorCreate, BOM, BOMCreate, PurchaseRequisition, PurchaseRequisitionCreate,
    PurchaseOrder, PurchaseOrderCreate, GRN, GRNCreate, PurchaseReturn, PurchaseReturnCreate,
    VendorBill, VendorBillCreate, PurchaseDashboardKPIs, POLineItem
)
from app.db.models.purchase import (
    Vendor as DBVendor, BOM as DBBOM, PurchaseRequisition as DBPurchaseRequisition,
    PurchaseOrder as DBPurchaseOrder, GRN as DBGRN, PurchaseReturn as DBPurchaseReturn,
    VendorBill as DBVendorBill
)
from app.db.models.user import ProductionPaper as DBProductionPaper
from app.api.deps import get_db, get_purchase_executive, get_purchase_manager, get_store_incharge, get_purchase_user
from app.db.models.user import User as DBUser

router = APIRouter()


# Helper Functions
def generate_vendor_code(db: Session) -> str:
    """Generate vendor code: VEN0001, VEN0002, etc."""
    last_vendor = db.query(DBVendor).order_by(DBVendor.id.desc()).first()
    next_num = (last_vendor.id + 1) if last_vendor else 1
    return f"VEN{next_num:04d}"


def generate_pr_number(db: Session) -> str:
    """Generate PR number: PR-1023, PR-1024, etc."""
    last_pr = db.query(DBPurchaseRequisition).order_by(DBPurchaseRequisition.id.desc()).first()
    next_num = (last_pr.id + 1) if last_pr else 1
    return f"PR-{next_num}"


def generate_po_number(db: Session) -> str:
    """Generate PO number: PO-302, PO-303, etc."""
    last_po = db.query(DBPurchaseOrder).order_by(DBPurchaseOrder.id.desc()).first()
    next_num = (last_po.id + 1) if last_po else 1
    return f"PO-{next_num}"


def generate_grn_number(db: Session) -> str:
    """Generate GRN number: GRN-558, GRN-559, etc."""
    last_grn = db.query(DBGRN).order_by(DBGRN.id.desc()).first()
    next_num = (last_grn.id + 1) if last_grn else 1
    return f"GRN-{next_num}"


def generate_return_number(db: Session) -> str:
    """Generate return number: PRET-001, PRET-002, etc."""
    last_return = db.query(DBPurchaseReturn).order_by(DBPurchaseReturn.id.desc()).first()
    next_num = (last_return.id + 1) if last_return else 1
    return f"PRET-{next_num:03d}"


def generate_bill_number(db: Session) -> str:
    """Generate vendor bill number: VB-001, VB-002, etc."""
    last_bill = db.query(DBVendorBill).order_by(DBVendorBill.id.desc()).first()
    next_num = (last_bill.id + 1) if last_bill else 1
    return f"VB-{next_num:03d}"


# ==================== DASHBOARD ====================
@router.get("/dashboard/kpis", response_model=PurchaseDashboardKPIs)
def get_dashboard_kpis(
    db: Session = Depends(get_db),
    current_user = Depends(get_purchase_user)
) -> Any:
    """Get Purchase Dashboard KPIs"""
    # PR Pending Approval
    pr_pending = db.query(DBPurchaseRequisition).filter(
        DBPurchaseRequisition.status.in_(["Draft", "Submitted"])
    ).count()
    
    # Open Purchase Orders
    open_pos = db.query(DBPurchaseOrder).filter(
        DBPurchaseOrder.status.in_(["Approved", "Sent to Vendor", "Partially Received"])
    ).count()
    
    # Material In Transit (POs sent but not fully received)
    in_transit = db.query(DBPurchaseOrder).filter(
        and_(
            DBPurchaseOrder.status == "Sent to Vendor",
            DBPurchaseOrder.received_quantity < DBPurchaseOrder.total_quantity
        )
    ).count()
    
    # Shortage / Rejection (GRNs with shortage or rejection)
    shortage_rejection = db.query(DBGRN).filter(
        or_(
            DBGRN.shortage_quantity > 0,
            DBGRN.rejected_quantity > 0
        )
    ).count()
    
    # Payables Due (Vendor Bills pending payment)
    payables = db.query(DBVendorBill).filter(
        DBVendorBill.payment_status == "Pending"
    ).count()
    
    # Payables Amount
    payables_amount = db.query(func.sum(DBVendorBill.total_amount)).filter(
        DBVendorBill.payment_status == "Pending"
    ).scalar() or Decimal("0")
    
    return PurchaseDashboardKPIs(
        pr_pending_approval=pr_pending,
        open_purchase_orders=open_pos,
        material_in_transit=in_transit,
        shortage_rejection=shortage_rejection,
        payables_due=payables,
        payables_amount=payables_amount
    )


# ==================== VENDOR MASTER ====================
@router.post("/vendors", response_model=Vendor, status_code=status.HTTP_201_CREATED)
def create_vendor(
    *,
    db: Session = Depends(get_db),
    vendor_in: VendorCreate,
    current_user = Depends(get_purchase_executive)
) -> Any:
    """Create a new vendor"""
    vendor_data = vendor_in.model_dump()
    
    # Generate vendor code if not provided
    if not vendor_data.get('vendor_code'):
        vendor_data['vendor_code'] = generate_vendor_code(db)
    
    # Serialize JSON fields
    if 'material_categories' in vendor_data and vendor_data['material_categories']:
        vendor_data['material_categories'] = json.dumps(vendor_data['material_categories'])
    if 'rate_contracts' in vendor_data and vendor_data['rate_contracts']:
        vendor_data['rate_contracts'] = json.dumps(vendor_data['rate_contracts'])
    
    db_vendor = DBVendor(**vendor_data, created_by=current_user.id)
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    
    # Parse JSON fields for response
    if db_vendor.material_categories:
        db_vendor.material_categories = json.loads(db_vendor.material_categories) if isinstance(db_vendor.material_categories, str) else db_vendor.material_categories
    if db_vendor.rate_contracts:
        db_vendor.rate_contracts = json.loads(db_vendor.rate_contracts) if isinstance(db_vendor.rate_contracts, str) else db_vendor.rate_contracts
    
    return db_vendor


@router.get("/vendors", response_model=List[Vendor])
def get_vendors(
    db: Session = Depends(get_db),
    current_user = Depends(get_purchase_user),
    skip: int = 0,
    limit: int = 100,
    vendor_type: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Any:
    """Get all vendors"""
    query = db.query(DBVendor)
    
    if vendor_type:
        query = query.filter(DBVendor.vendor_type == vendor_type)
    if is_active is not None:
        query = query.filter(DBVendor.is_active == is_active)
    
    vendors = query.offset(skip).limit(limit).all()
    
    # Parse JSON fields
    for vendor in vendors:
        if vendor.material_categories and isinstance(vendor.material_categories, str):
            vendor.material_categories = json.loads(vendor.material_categories)
        if vendor.rate_contracts and isinstance(vendor.rate_contracts, str):
            vendor.rate_contracts = json.loads(vendor.rate_contracts)
    
    return vendors


@router.get("/vendors/{vendor_id}", response_model=Vendor)
def get_vendor(
    *,
    db: Session = Depends(get_db),
    vendor_id: int,
    current_user = Depends(get_purchase_user)
) -> Any:
    """Get a specific vendor"""
    vendor = db.query(DBVendor).filter(DBVendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Parse JSON fields
    if vendor.material_categories and isinstance(vendor.material_categories, str):
        vendor.material_categories = json.loads(vendor.material_categories)
    if vendor.rate_contracts and isinstance(vendor.rate_contracts, str):
        vendor.rate_contracts = json.loads(vendor.rate_contracts)
    
    return vendor


# ==================== BOM ====================
@router.get("/bom/production-paper/{production_paper_id}", response_model=List[BOM])
def get_bom_by_production_paper(
    *,
    db: Session = Depends(get_db),
    production_paper_id: int,
    current_user = Depends(get_purchase_user)
) -> Any:
    """Get BOM for a production paper"""
    bom_items = db.query(DBBOM).filter(
        DBBOM.production_paper_id == production_paper_id
    ).all()
    return bom_items


# ==================== PURCHASE REQUISITION (PR) ====================
@router.post("/purchase-requisitions", response_model=PurchaseRequisition, status_code=status.HTTP_201_CREATED)
def create_purchase_requisition(
    *,
    db: Session = Depends(get_db),
    pr_in: PurchaseRequisitionCreate,
    current_user = Depends(get_purchase_executive)
) -> Any:
    """Create a new Purchase Requisition"""
    pr_data = pr_in.model_dump()
    
    # Generate PR number if not provided
    if not pr_data.get('pr_number'):
        pr_data['pr_number'] = generate_pr_number(db)
    
    # Validate production paper if linked
    if pr_data.get('production_paper_id'):
        paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == pr_data['production_paper_id']).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Production paper not found")
        if not pr_data.get('production_paper_number'):
            pr_data['production_paper_number'] = paper.paper_number
    
    db_pr = DBPurchaseRequisition(**pr_data, created_by=current_user.id)
    db.add(db_pr)
    db.commit()
    db.refresh(db_pr)
    return db_pr


@router.get("/purchase-requisitions", response_model=List[PurchaseRequisition])
def get_purchase_requisitions(
    db: Session = Depends(get_db),
    current_user = Depends(get_purchase_user),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> Any:
    """Get all Purchase Requisitions"""
    query = db.query(DBPurchaseRequisition)
    if status:
        query = query.filter(DBPurchaseRequisition.status == status)
    
    prs = query.offset(skip).limit(limit).all()
    return prs


@router.get("/purchase-requisitions/{pr_id}", response_model=PurchaseRequisition)
def get_purchase_requisition(
    *,
    db: Session = Depends(get_db),
    pr_id: int,
    current_user = Depends(get_purchase_user)
) -> Any:
    """Get a specific Purchase Requisition"""
    pr = db.query(DBPurchaseRequisition).filter(DBPurchaseRequisition.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")
    return pr


@router.put("/purchase-requisitions/{pr_id}/approve", response_model=PurchaseRequisition)
def approve_purchase_requisition(
    *,
    db: Session = Depends(get_db),
    pr_id: int,
    current_user = Depends(get_purchase_manager)
) -> Any:
    """Approve a Purchase Requisition"""
    pr = db.query(DBPurchaseRequisition).filter(DBPurchaseRequisition.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase Requisition not found")
    
    if pr.status != "Submitted":
        raise HTTPException(status_code=400, detail="PR must be in Submitted status to approve")
    
    pr.status = "Approved"
    pr.approved_by = current_user.id
    pr.approved_at = datetime.now()
    db.commit()
    db.refresh(pr)
    return pr


# ==================== PURCHASE ORDER (PO) ====================
@router.post("/purchase-orders", response_model=PurchaseOrder, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    *,
    db: Session = Depends(get_db),
    po_in: PurchaseOrderCreate,
    current_user = Depends(get_purchase_executive)
) -> Any:
    """Create a new Purchase Order"""
    po_data = po_in.model_dump()
    
    # Generate PO number if not provided
    if not po_data.get('po_number'):
        po_data['po_number'] = generate_po_number(db)
    
    # Validate PR if linked
    if po_data.get('pr_id'):
        pr = db.query(DBPurchaseRequisition).filter(DBPurchaseRequisition.id == po_data['pr_id']).first()
        if not pr:
            raise HTTPException(status_code=404, detail="Purchase Requisition not found")
        if pr.status != "Approved":
            raise HTTPException(status_code=400, detail="PR must be approved before creating PO")
        if not po_data.get('pr_number'):
            po_data['pr_number'] = pr.pr_number
    
    # Validate vendor
    vendor = db.query(DBVendor).filter(DBVendor.id == po_data['vendor_id']).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not po_data.get('vendor_name'):
        po_data['vendor_name'] = vendor.vendor_name
    
    # Calculate totals from line items
    line_items = po_data['line_items']
    subtotal = sum(Decimal(str(item['amount'])) for item in line_items)
    tax_amount = sum(Decimal(str(item['amount'])) * Decimal(str(item.get('tax_percent', 0))) / 100 for item in line_items)
    total_amount = subtotal + tax_amount
    total_quantity = sum(item['quantity'] for item in line_items)
    
    po_data['subtotal'] = subtotal
    po_data['tax_amount'] = tax_amount
    po_data['total_amount'] = total_amount
    po_data['total_quantity'] = total_quantity
    po_data['pending_quantity'] = total_quantity
    
    # Serialize line items to JSON
    po_data['line_items'] = json.dumps(line_items)
    
    db_po = DBPurchaseOrder(**po_data, created_by=current_user.id)
    db.add(db_po)
    
    # Update PR status if linked
    if po_data.get('pr_id'):
        pr = db.query(DBPurchaseRequisition).filter(DBPurchaseRequisition.id == po_data['pr_id']).first()
        pr.po_created = True
        pr.po_id = db_po.id
        pr.status = "Converted to PO"
    
    db.commit()
    db.refresh(db_po)
    
    # Parse line items for response
    db_po.line_items = json.loads(db_po.line_items) if isinstance(db_po.line_items, str) else db_po.line_items
    
    return db_po


@router.get("/purchase-orders", response_model=List[PurchaseOrder])
def get_purchase_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_purchase_user),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> Any:
    """Get all Purchase Orders"""
    query = db.query(DBPurchaseOrder)
    if status:
        query = query.filter(DBPurchaseOrder.status == status)
    
    pos = query.offset(skip).limit(limit).all()
    
    # Parse line items
    for po in pos:
        if po.line_items and isinstance(po.line_items, str):
            po.line_items = json.loads(po.line_items)
    
    return pos


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrder)
def get_purchase_order(
    *,
    db: Session = Depends(get_db),
    po_id: int,
    current_user = Depends(get_purchase_user)
) -> Any:
    """Get a specific Purchase Order"""
    po = db.query(DBPurchaseOrder).filter(DBPurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    # Parse line items
    if po.line_items and isinstance(po.line_items, str):
        po.line_items = json.loads(po.line_items)
    
    return po


@router.put("/purchase-orders/{po_id}/approve", response_model=PurchaseOrder)
def approve_purchase_order(
    *,
    db: Session = Depends(get_db),
    po_id: int,
    current_user = Depends(get_purchase_manager)
) -> Any:
    """Approve a Purchase Order"""
    po = db.query(DBPurchaseOrder).filter(DBPurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    if po.status != "Draft":
        raise HTTPException(status_code=400, detail="PO must be in Draft status to approve")
    
    po.status = "Approved"
    po.approved_by = current_user.id
    po.approved_at = datetime.now()
    db.commit()
    db.refresh(po)
    
    # Parse line items
    if po.line_items and isinstance(po.line_items, str):
        po.line_items = json.loads(po.line_items)
    
    return po


@router.put("/purchase-orders/{po_id}/send-to-vendor", response_model=PurchaseOrder)
def send_po_to_vendor(
    *,
    db: Session = Depends(get_db),
    po_id: int,
    current_user = Depends(get_purchase_executive)
) -> Any:
    """Mark PO as sent to vendor"""
    po = db.query(DBPurchaseOrder).filter(DBPurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    if po.status != "Approved":
        raise HTTPException(status_code=400, detail="PO must be approved before sending to vendor")
    
    po.status = "Sent to Vendor"
    po.sent_to_vendor_at = datetime.now()
    db.commit()
    db.refresh(po)
    
    # Parse line items
    if po.line_items and isinstance(po.line_items, str):
        po.line_items = json.loads(po.line_items)
    
    return po


# ==================== GRN (Goods Receipt Note) ====================
@router.post("/grns", response_model=GRN, status_code=status.HTTP_201_CREATED)
def create_grn(
    *,
    db: Session = Depends(get_db),
    grn_in: GRNCreate,
    current_user = Depends(get_store_incharge)
) -> Any:
    """Create a new GRN (Store Incharge only)"""
    grn_data = grn_in.model_dump()
    
    # Generate GRN number if not provided
    if not grn_data.get('grn_number'):
        grn_data['grn_number'] = generate_grn_number(db)
    
    # Validate PO (Mandatory - No GRN without PO)
    po = db.query(DBPurchaseOrder).filter(DBPurchaseOrder.id == grn_data['po_id']).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if not grn_data.get('po_number'):
        grn_data['po_number'] = po.po_number
    
    # Validate vendor
    vendor = db.query(DBVendor).filter(DBVendor.id == grn_data['vendor_id']).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not grn_data.get('vendor_name'):
        grn_data['vendor_name'] = vendor.vendor_name
    
    # Calculate accepted quantity
    grn_data['accepted_quantity'] = grn_data['received_quantity'] - grn_data.get('rejected_quantity', 0)
    
    # Serialize QC parameters
    if 'qc_parameters' in grn_data and grn_data['qc_parameters']:
        if isinstance(grn_data['qc_parameters'], dict):
            grn_data['qc_parameters'] = json.dumps(grn_data['qc_parameters'])
    
    db_grn = DBGRN(**grn_data, created_by=current_user.id)
    db.add(db_grn)
    
    # Update PO receipt status
    po.received_quantity += grn_data['accepted_quantity']
    po.pending_quantity = po.total_quantity - po.received_quantity
    
    if po.received_quantity >= po.total_quantity:
        po.status = "Closed"
    elif po.received_quantity > 0:
        po.status = "Partially Received"
    
    db.commit()
    db.refresh(db_grn)
    
    # Parse QC parameters for response
    if db_grn.qc_parameters and isinstance(db_grn.qc_parameters, str):
        db_grn.qc_parameters = json.loads(db_grn.qc_parameters)
    
    return db_grn


@router.get("/grns", response_model=List[GRN])
def get_grns(
    db: Session = Depends(get_db),
    current_user = Depends(get_purchase_user),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> Any:
    """Get all GRNs"""
    query = db.query(DBGRN)
    if status:
        query = query.filter(DBGRN.status == status)
    
    grns = query.offset(skip).limit(limit).all()
    
    # Parse QC parameters
    for grn in grns:
        if grn.qc_parameters and isinstance(grn.qc_parameters, str):
            grn.qc_parameters = json.loads(grn.qc_parameters)
    
    return grns


@router.get("/grns/{grn_id}", response_model=GRN)
def get_grn(
    *,
    db: Session = Depends(get_db),
    grn_id: int,
    current_user = Depends(get_purchase_user)
) -> Any:
    """Get a specific GRN"""
    grn = db.query(DBGRN).filter(DBGRN.id == grn_id).first()
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")
    
    # Parse QC parameters
    if grn.qc_parameters and isinstance(grn.qc_parameters, str):
        grn.qc_parameters = json.loads(grn.qc_parameters)
    
    return grn


@router.put("/grns/{grn_id}/approve", response_model=GRN)
def approve_grn(
    *,
    db: Session = Depends(get_db),
    grn_id: int,
    current_user = Depends(get_store_incharge)
) -> Any:
    """Approve a GRN"""
    grn = db.query(DBGRN).filter(DBGRN.id == grn_id).first()
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")
    
    if grn.status != "Draft":
        raise HTTPException(status_code=400, detail="GRN must be in Draft status to approve")
    
    grn.status = "Approved"
    grn.approved_by = current_user.id
    grn.approved_at = datetime.now()
    db.commit()
    db.refresh(grn)
    
    # Parse QC parameters
    if grn.qc_parameters and isinstance(grn.qc_parameters, str):
        grn.qc_parameters = json.loads(grn.qc_parameters)
    
    return grn


# ==================== PURCHASE RETURN ====================
@router.post("/purchase-returns", response_model=PurchaseReturn, status_code=status.HTTP_201_CREATED)
def create_purchase_return(
    *,
    db: Session = Depends(get_db),
    return_in: PurchaseReturnCreate,
    current_user = Depends(get_store_incharge)
) -> Any:
    """Create a Purchase Return"""
    return_data = return_in.model_dump()
    
    # Generate return number if not provided
    if not return_data.get('return_number'):
        return_data['return_number'] = generate_return_number(db)
    
    # Validate PO
    po = db.query(DBPurchaseOrder).filter(DBPurchaseOrder.id == return_data['po_id']).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if not return_data.get('po_number'):
        return_data['po_number'] = po.po_number
    
    db_return = DBPurchaseReturn(**return_data, created_by=current_user.id)
    db.add(db_return)
    
    # Link to GRN if provided
    if return_data.get('grn_id'):
        grn = db.query(DBGRN).filter(DBGRN.id == return_data['grn_id']).first()
        if grn:
            grn.purchase_return_id = db_return.id
    
    db.commit()
    db.refresh(db_return)
    return db_return


@router.get("/purchase-returns", response_model=List[PurchaseReturn])
def get_purchase_returns(
    db: Session = Depends(get_db),
    current_user = Depends(get_purchase_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all Purchase Returns"""
    returns = db.query(DBPurchaseReturn).offset(skip).limit(limit).all()
    return returns


# ==================== VENDOR BILL ====================
@router.post("/vendor-bills", response_model=VendorBill, status_code=status.HTTP_201_CREATED)
def create_vendor_bill(
    *,
    db: Session = Depends(get_db),
    bill_in: VendorBillCreate,
    current_user = Depends(get_purchase_executive)
) -> Any:
    """Create a Vendor Bill (No payment without GRN)"""
    bill_data = bill_in.model_dump()
    
    # Generate bill number if not provided
    if not bill_data.get('bill_number'):
        bill_data['bill_number'] = generate_bill_number(db)
    
    # Validate GRN (Mandatory - No payment without GRN)
    grn = db.query(DBGRN).filter(DBGRN.id == bill_data['grn_id']).first()
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")
    if grn.status != "Approved":
        raise HTTPException(status_code=400, detail="GRN must be approved before creating vendor bill")
    if not bill_data.get('grn_number'):
        bill_data['grn_number'] = grn.grn_number
    
    # Validate vendor
    vendor = db.query(DBVendor).filter(DBVendor.id == bill_data['vendor_id']).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not bill_data.get('vendor_name'):
        bill_data['vendor_name'] = vendor.vendor_name
    if not bill_data.get('vendor_gstin'):
        bill_data['vendor_gstin'] = vendor.gstin
    
    # Serialize GST breakup
    if 'gst_breakup' in bill_data and bill_data['gst_breakup']:
        if isinstance(bill_data['gst_breakup'], dict):
            bill_data['gst_breakup'] = json.dumps(bill_data['gst_breakup'])
    
    db_bill = DBVendorBill(**bill_data, created_by=current_user.id)
    db.add(db_bill)
    db.commit()
    db.refresh(db_bill)
    
    # Parse GST breakup for response
    if db_bill.gst_breakup and isinstance(db_bill.gst_breakup, str):
        db_bill.gst_breakup = json.loads(db_bill.gst_breakup)
    
    return db_bill


@router.get("/vendor-bills", response_model=List[VendorBill])
def get_vendor_bills(
    db: Session = Depends(get_db),
    current_user = Depends(get_purchase_user),
    skip: int = 0,
    limit: int = 100,
    payment_status: Optional[str] = None
) -> Any:
    """Get all Vendor Bills"""
    query = db.query(DBVendorBill)
    if payment_status:
        query = query.filter(DBVendorBill.payment_status == payment_status)
    
    bills = query.offset(skip).limit(limit).all()
    
    # Parse JSON fields
    for bill in bills:
        if bill.gst_breakup and isinstance(bill.gst_breakup, str):
            bill.gst_breakup = json.loads(bill.gst_breakup)
        if bill.payment_details and isinstance(bill.payment_details, str):
            bill.payment_details = json.loads(bill.payment_details)
    
    return bills


@router.get("/vendor-bills/{bill_id}", response_model=VendorBill)
def get_vendor_bill(
    *,
    db: Session = Depends(get_db),
    bill_id: int,
    current_user = Depends(get_purchase_user)
) -> Any:
    """Get a specific Vendor Bill"""
    bill = db.query(DBVendorBill).filter(DBVendorBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Vendor Bill not found")
    
    # Parse JSON fields
    if bill.gst_breakup and isinstance(bill.gst_breakup, str):
        bill.gst_breakup = json.loads(bill.gst_breakup)
    if bill.payment_details and isinstance(bill.payment_details, str):
        bill.payment_details = json.loads(bill.payment_details)
    
    return bill

