from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import json
import re

from app.schemas.sales import (
    Lead, LeadCreate, LeadUpdate,
    SiteProject, SiteProjectCreate, SiteProjectUpdate,
    Quotation, QuotationCreate, QuotationUpdate, QuotationLineItem,
    SalesOrder, SalesOrderCreate, SalesOrderUpdate,
    MeasurementRequest, MeasurementRequestCreate, MeasurementRequestUpdate,
    FollowUp, FollowUpCreate, FollowUpUpdate,
    SalesDashboardStats
)
from app.db.models.sales import (
    Lead as DBLead,
    SiteProject as DBSiteProject,
    Quotation as DBQuotation,
    SalesOrder as DBSalesOrder,
    MeasurementRequest as DBMeasurementRequest,
    FollowUp as DBFollowUp
)
from app.db.models.user import Party as DBParty, Measurement as DBMeasurement, ProductionPaper as DBProductionPaper
from app.api.deps import get_db, get_marketing_executive, get_sales_executive, get_sales_manager, get_sales_user

router = APIRouter()


# Helper Functions
def generate_lead_number(db: Session) -> str:
    """Generate next Lead number"""
    last_lead = db.query(DBLead).order_by(DBLead.id.desc()).first()
    if last_lead:
        match = re.search(r'LD-(\d+)', last_lead.lead_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"LD-{next_num:04d}"


def generate_project_code(db: Session, party_id: int) -> str:
    """Generate project code"""
    last_project = db.query(DBSiteProject).filter(DBSiteProject.party_id == party_id).order_by(DBSiteProject.id.desc()).first()
    if last_project and last_project.project_code:
        match = re.search(r'PJ-(\d+)', last_project.project_code)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"PJ-{next_num:04d}"


def generate_quotation_number(db: Session) -> str:
    """Generate next Quotation number"""
    last_qt = db.query(DBQuotation).order_by(DBQuotation.id.desc()).first()
    if last_qt:
        match = re.search(r'QT-(\d+)', last_qt.quotation_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"QT-{next_num:04d}"


def generate_order_number(db: Session) -> str:
    """Generate next Sales Order number"""
    last_order = db.query(DBSalesOrder).order_by(DBSalesOrder.id.desc()).first()
    if last_order:
        match = re.search(r'SO-(\d+)', last_order.order_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"SO-{next_num:04d}"


def generate_measurement_request_number(db: Session) -> str:
    """Generate next Measurement Request number"""
    last_mr = db.query(DBMeasurementRequest).order_by(DBMeasurementRequest.id.desc()).first()
    if last_mr:
        match = re.search(r'MR-(\d+)', last_mr.request_number)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1
    return f"MR-{next_num:04d}"


def calculate_quotation_totals(line_items: List[dict], discount_amount: Decimal = Decimal("0.00"), discount_percentage: Optional[Decimal] = None) -> dict:
    """Calculate quotation totals including GST"""
    subtotal = Decimal("0.00")
    for item in line_items:
        quantity = Decimal(str(item.get('quantity', 0)))
        rate = Decimal(str(item.get('rate', 0)))
        item_discount = Decimal(str(item.get('discount', 0)))
        amount = (quantity * rate) - item_discount
        subtotal += amount
    
    # Apply discount
    if discount_percentage:
        discount_amount = subtotal * (discount_percentage / Decimal("100"))
    
    taxable_amount = subtotal - discount_amount
    
    # GST calculation (assuming 18% GST)
    gst_rate = Decimal("18.00")
    tax_amount = taxable_amount * (gst_rate / Decimal("100"))
    total_amount = taxable_amount + tax_amount
    
    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "total_amount": total_amount
    }


# Dashboard Endpoints
@router.get("/dashboard/stats", response_model=SalesDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_sales_user)
) -> Any:
    """Get sales dashboard statistics"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # New Leads (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        new_leads = db.query(DBLead).filter(DBLead.created_at >= thirty_days_ago).count()
        
        # Active Opportunities (Qualified, Quotation Sent)
        active_opportunities = db.query(DBLead).filter(
            DBLead.lead_status.in_(["Qualified", "Quotation Sent"])
        ).count()
        
        # Orders Confirmed
        orders_confirmed = db.query(DBSalesOrder).filter(
            DBSalesOrder.status == "Confirmed"
        ).count()
        
        # Measurement Pending
        measurement_pending = db.query(DBMeasurementRequest).filter(
            DBMeasurementRequest.status.in_(["Pending", "Assigned", "Scheduled"])
        ).count()
        
        # Sales Value MTD
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        sales_value_result = db.query(func.sum(DBSalesOrder.total_amount)).filter(
            DBSalesOrder.created_at >= current_month_start,
            DBSalesOrder.status.in_(["Confirmed", "Measurement Pending", "In Production", "Ready for Dispatch", "Dispatched", "Delivered"])
        ).scalar()
        sales_value_mtd = Decimal(str(sales_value_result)) if sales_value_result is not None else Decimal("0.00")
        
        # Lead Conversion Rate
        total_leads = db.query(DBLead).count()
        won_leads = db.query(DBLead).filter(DBLead.lead_status == "Won").count()
        conversion_rate = (Decimal(str(won_leads)) / Decimal(str(total_leads)) * Decimal("100")) if total_leads > 0 else Decimal("0.00")
        
        return SalesDashboardStats(
            new_leads=new_leads,
            active_opportunities=active_opportunities,
            orders_confirmed=orders_confirmed,
            measurement_pending=measurement_pending,
            sales_value_mtd=sales_value_mtd,
            lead_conversion_rate=conversion_rate
        )
    except Exception as e:
        logger.error(f"Error fetching sales dashboard stats: {str(e)}", exc_info=True)
        # Return default values on error
        return SalesDashboardStats(
            new_leads=0,
            active_opportunities=0,
            orders_confirmed=0,
            measurement_pending=0,
            sales_value_mtd=Decimal("0.00"),
            lead_conversion_rate=Decimal("0.00")
        )


# Lead Management Endpoints
@router.post("/leads", response_model=Lead, status_code=status.HTTP_201_CREATED)
def create_lead(
    *,
    db: Session = Depends(get_db),
    lead_in: LeadCreate,
    current_user = Depends(get_marketing_executive)
) -> Any:
    """Create a new lead"""
    lead_data = lead_in.model_dump()
    lead_data['lead_number'] = generate_lead_number(db)
    lead_data['created_by'] = current_user.id
    if not lead_data.get('assigned_to'):
        lead_data['assigned_to'] = current_user.id
        lead_data['assigned_sales_executive'] = current_user.username
    
    db_lead = DBLead(**lead_data)
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return db_lead


@router.get("/leads", response_model=List[Lead])
def get_leads(
    db: Session = Depends(get_db),
    current_user = Depends(get_sales_user),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all leads"""
    query = db.query(DBLead)
    if status_filter:
        query = query.filter(DBLead.lead_status == status_filter)
    
    leads = query.order_by(DBLead.created_at.desc()).offset(skip).limit(limit).all()
    return leads


@router.get("/leads/{lead_id}", response_model=Lead)
def get_lead(
    *,
    db: Session = Depends(get_db),
    lead_id: int,
    current_user = Depends(get_sales_user)
) -> Any:
    """Get a specific lead"""
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/leads/{lead_id}", response_model=Lead)
def update_lead(
    *,
    db: Session = Depends(get_db),
    lead_id: int,
    lead_in: LeadUpdate,
    current_user = Depends(get_sales_user)
) -> Any:
    """Update a lead"""
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_in.model_dump(exclude_unset=True)
    if 'last_follow_up_date' not in update_data:
        update_data['last_follow_up_date'] = datetime.now()
    
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/leads/{lead_id}/convert", response_model=Lead)
def convert_lead_to_party(
    *,
    db: Session = Depends(get_db),
    lead_id: int,
    party_id: int,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Convert a lead to party"""
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    party = db.query(DBParty).filter(DBParty.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    lead.converted_to_party_id = party_id
    lead.converted_at = datetime.now()
    lead.lead_status = "Won"
    
    db.commit()
    db.refresh(lead)
    return lead


# Site/Project Management Endpoints
@router.post("/sites", response_model=SiteProject, status_code=status.HTTP_201_CREATED)
def create_site_project(
    *,
    db: Session = Depends(get_db),
    site_in: SiteProjectCreate,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Create a new site/project"""
    site_data = site_in.model_dump()
    site_data['project_code'] = generate_project_code(db, site_data['party_id'])
    site_data['created_by'] = current_user.id
    
    db_site = DBSiteProject(**site_data)
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site


@router.get("/sites", response_model=List[SiteProject])
def get_sites(
    db: Session = Depends(get_db),
    current_user = Depends(get_sales_user),
    party_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all sites/projects"""
    query = db.query(DBSiteProject)
    if party_id:
        query = query.filter(DBSiteProject.party_id == party_id)
    
    sites = query.order_by(DBSiteProject.created_at.desc()).offset(skip).limit(limit).all()
    return sites


@router.get("/sites/{site_id}", response_model=SiteProject)
def get_site(
    *,
    db: Session = Depends(get_db),
    site_id: int,
    current_user = Depends(get_sales_user)
) -> Any:
    """Get a specific site/project"""
    site = db.query(DBSiteProject).filter(DBSiteProject.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site/Project not found")
    return site


@router.put("/sites/{site_id}", response_model=SiteProject)
def update_site(
    *,
    db: Session = Depends(get_db),
    site_id: int,
    site_in: SiteProjectUpdate,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Update a site/project"""
    site = db.query(DBSiteProject).filter(DBSiteProject.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site/Project not found")
    
    update_data = site_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(site, field, value)
    
    db.commit()
    db.refresh(site)
    return site


# Quotation Management Endpoints
@router.post("/quotations", response_model=Quotation, status_code=status.HTTP_201_CREATED)
def create_quotation(
    *,
    db: Session = Depends(get_db),
    quotation_in: QuotationCreate,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Create a new quotation"""
    quotation_data = quotation_in.model_dump()
    quotation_data['quotation_number'] = generate_quotation_number(db)
    quotation_data['created_by'] = current_user.id
    
    # Calculate totals
    line_items = quotation_data.get('line_items', [])
    discount_amount = Decimal(str(quotation_data.get('discount_amount', 0)))
    discount_percentage = quotation_data.get('discount_percentage')
    
    totals = calculate_quotation_totals(line_items, discount_amount, discount_percentage)
    quotation_data.update(totals)
    
    # Store line_items as JSON
    quotation_data['line_items'] = json.dumps(line_items)
    
    db_quotation = DBQuotation(**quotation_data)
    db.add(db_quotation)
    db.commit()
    db.refresh(db_quotation)
    
    # Convert back for response
    quotation_dict = {
        'id': db_quotation.id,
        'quotation_number': db_quotation.quotation_number,
        'party_id': db_quotation.party_id,
        'party_name': db_quotation.party_name,
        'site_project_id': db_quotation.site_project_id,
        'lead_id': db_quotation.lead_id,
        'validity_date': db_quotation.validity_date,
        'payment_terms': db_quotation.payment_terms,
        'delivery_timeline': db_quotation.delivery_timeline,
        'line_items': json.loads(db_quotation.line_items) if isinstance(db_quotation.line_items, str) else db_quotation.line_items,
        'subtotal': db_quotation.subtotal,
        'discount_amount': db_quotation.discount_amount,
        'discount_percentage': db_quotation.discount_percentage,
        'tax_amount': db_quotation.tax_amount,
        'total_amount': db_quotation.total_amount,
        'discount_approved_by': db_quotation.discount_approved_by,
        'discount_approved_at': db_quotation.discount_approved_at,
        'status': db_quotation.status,
        'notes': db_quotation.notes,
        'created_by': db_quotation.created_by,
        'created_at': db_quotation.created_at,
        'updated_at': db_quotation.updated_at
    }
    
    return Quotation(**quotation_dict)


@router.get("/quotations", response_model=List[Quotation])
def get_quotations(
    db: Session = Depends(get_db),
    current_user = Depends(get_sales_user),
    party_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all quotations"""
    query = db.query(DBQuotation)
    if party_id:
        query = query.filter(DBQuotation.party_id == party_id)
    if status_filter:
        query = query.filter(DBQuotation.status == status_filter)
    
    quotations = query.order_by(DBQuotation.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for qt in quotations:
        qt_dict = {
            'id': qt.id,
            'quotation_number': qt.quotation_number,
            'party_id': qt.party_id,
            'party_name': qt.party_name,
            'site_project_id': qt.site_project_id,
            'lead_id': qt.lead_id,
            'validity_date': qt.validity_date,
            'payment_terms': qt.payment_terms,
            'delivery_timeline': qt.delivery_timeline,
            'line_items': json.loads(qt.line_items) if isinstance(qt.line_items, str) else qt.line_items,
            'subtotal': qt.subtotal,
            'discount_amount': qt.discount_amount,
            'discount_percentage': qt.discount_percentage,
            'tax_amount': qt.tax_amount,
            'total_amount': qt.total_amount,
            'discount_approved_by': qt.discount_approved_by,
            'discount_approved_at': qt.discount_approved_at,
            'status': qt.status,
            'notes': qt.notes,
            'created_by': qt.created_by,
            'created_at': qt.created_at,
            'updated_at': qt.updated_at
        }
        result.append(Quotation(**qt_dict))
    
    return result


@router.get("/quotations/{quotation_id}", response_model=Quotation)
def get_quotation(
    *,
    db: Session = Depends(get_db),
    quotation_id: int,
    current_user = Depends(get_sales_user)
) -> Any:
    """Get a specific quotation"""
    qt = db.query(DBQuotation).filter(DBQuotation.id == quotation_id).first()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    qt_dict = {
        'id': qt.id,
        'quotation_number': qt.quotation_number,
        'party_id': qt.party_id,
        'party_name': qt.party_name,
        'site_project_id': qt.site_project_id,
        'lead_id': qt.lead_id,
        'validity_date': qt.validity_date,
        'payment_terms': qt.payment_terms,
        'delivery_timeline': qt.delivery_timeline,
        'line_items': json.loads(qt.line_items) if isinstance(qt.line_items, str) else qt.line_items,
        'subtotal': qt.subtotal,
        'discount_amount': qt.discount_amount,
        'discount_percentage': qt.discount_percentage,
        'tax_amount': qt.tax_amount,
        'total_amount': qt.total_amount,
        'discount_approved_by': qt.discount_approved_by,
        'discount_approved_at': qt.discount_approved_at,
        'status': qt.status,
        'notes': qt.notes,
        'created_by': qt.created_by,
        'created_at': qt.created_at,
        'updated_at': qt.updated_at
    }
    
    return Quotation(**qt_dict)


@router.put("/quotations/{quotation_id}", response_model=Quotation)
def update_quotation(
    *,
    db: Session = Depends(get_db),
    quotation_id: int,
    quotation_in: QuotationUpdate,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Update a quotation"""
    qt = db.query(DBQuotation).filter(DBQuotation.id == quotation_id).first()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    update_data = quotation_in.model_dump(exclude_unset=True)
    
    # Recalculate totals if line_items or discount changed
    if 'line_items' in update_data or 'discount_amount' in update_data or 'discount_percentage' in update_data:
        line_items = update_data.get('line_items') or (json.loads(qt.line_items) if isinstance(qt.line_items, str) else qt.line_items)
        discount_amount = Decimal(str(update_data.get('discount_amount', qt.discount_amount)))
        discount_percentage = update_data.get('discount_percentage', qt.discount_percentage)
        
        totals = calculate_quotation_totals(line_items, discount_amount, discount_percentage)
        update_data.update(totals)
        
        if 'line_items' in update_data:
            update_data['line_items'] = json.dumps(update_data['line_items'])
    
    for field, value in update_data.items():
        setattr(qt, field, value)
    
    db.commit()
    db.refresh(qt)
    
    qt_dict = {
        'id': qt.id,
        'quotation_number': qt.quotation_number,
        'party_id': qt.party_id,
        'party_name': qt.party_name,
        'site_project_id': qt.site_project_id,
        'lead_id': qt.lead_id,
        'validity_date': qt.validity_date,
        'payment_terms': qt.payment_terms,
        'delivery_timeline': qt.delivery_timeline,
        'line_items': json.loads(qt.line_items) if isinstance(qt.line_items, str) else qt.line_items,
        'subtotal': qt.subtotal,
        'discount_amount': qt.discount_amount,
        'discount_percentage': qt.discount_percentage,
        'tax_amount': qt.tax_amount,
        'total_amount': qt.total_amount,
        'discount_approved_by': qt.discount_approved_by,
        'discount_approved_at': qt.discount_approved_at,
        'status': qt.status,
        'notes': qt.notes,
        'created_by': qt.created_by,
        'created_at': qt.created_at,
        'updated_at': qt.updated_at
    }
    
    return Quotation(**qt_dict)


@router.post("/quotations/{quotation_id}/approve-discount", response_model=Quotation)
def approve_discount(
    *,
    db: Session = Depends(get_db),
    quotation_id: int,
    current_user = Depends(get_sales_manager)
) -> Any:
    """Approve discount on quotation (Sales Manager only)"""
    qt = db.query(DBQuotation).filter(DBQuotation.id == quotation_id).first()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if qt.discount_amount == 0:
        raise HTTPException(status_code=400, detail="No discount to approve")
    
    qt.discount_approved_by = current_user.id
    qt.discount_approved_at = datetime.now()
    
    db.commit()
    db.refresh(qt)
    
    qt_dict = {
        'id': qt.id,
        'quotation_number': qt.quotation_number,
        'party_id': qt.party_id,
        'party_name': qt.party_name,
        'site_project_id': qt.site_project_id,
        'lead_id': qt.lead_id,
        'validity_date': qt.validity_date,
        'payment_terms': qt.payment_terms,
        'delivery_timeline': qt.delivery_timeline,
        'line_items': json.loads(qt.line_items) if isinstance(qt.line_items, str) else qt.line_items,
        'subtotal': qt.subtotal,
        'discount_amount': qt.discount_amount,
        'discount_percentage': qt.discount_percentage,
        'tax_amount': qt.tax_amount,
        'total_amount': qt.total_amount,
        'discount_approved_by': qt.discount_approved_by,
        'discount_approved_at': qt.discount_approved_at,
        'status': qt.status,
        'notes': qt.notes,
        'created_by': qt.created_by,
        'created_at': qt.created_at,
        'updated_at': qt.updated_at
    }
    
    return Quotation(**qt_dict)


# Sales Order Endpoints
@router.post("/sales-orders", response_model=SalesOrder, status_code=status.HTTP_201_CREATED)
def create_sales_order(
    *,
    db: Session = Depends(get_db),
    order_in: SalesOrderCreate,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Create a new sales order"""
    order_data = order_in.model_dump()
    order_data['order_number'] = generate_order_number(db)
    order_data['created_by'] = current_user.id
    order_data['status'] = "Confirmed"
    
    db_order = DBSalesOrder(**order_data)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Auto-create measurement request
    measurement_request_data = {
        'request_number': generate_measurement_request_number(db),
        'sales_order_id': db_order.id,
        'sales_order_number': db_order.order_number,
        'party_id': db_order.party_id,
        'party_name': db_order.party_name,
        'site_project_id': db_order.site_project_id,
        'status': 'Pending',
        'created_by': current_user.id
    }
    db_mr = DBMeasurementRequest(**measurement_request_data)
    db.add(db_mr)
    
    # Update order
    db_order.measurement_requested = True
    db.commit()
    db.refresh(db_order)
    
    return db_order


@router.get("/sales-orders", response_model=List[SalesOrder])
def get_sales_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_sales_user),
    party_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all sales orders"""
    query = db.query(DBSalesOrder)
    if party_id:
        query = query.filter(DBSalesOrder.party_id == party_id)
    if status_filter:
        query = query.filter(DBSalesOrder.status == status_filter)
    
    orders = query.order_by(DBSalesOrder.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/sales-orders/{order_id}", response_model=SalesOrder)
def get_sales_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    current_user = Depends(get_sales_user)
) -> Any:
    """Get a specific sales order"""
    order = db.query(DBSalesOrder).filter(DBSalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return order


@router.put("/sales-orders/{order_id}", response_model=SalesOrder)
def update_sales_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    order_in: SalesOrderUpdate,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Update a sales order"""
    order = db.query(DBSalesOrder).filter(DBSalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    
    # Sales cannot edit after production starts
    if order.status in ["In Production", "Ready for Dispatch", "Dispatched", "Delivered"]:
        raise HTTPException(status_code=403, detail="Cannot edit order after production has started")
    
    update_data = order_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order


# Measurement Request Endpoints
@router.get("/measurement-requests", response_model=List[MeasurementRequest])
def get_measurement_requests(
    db: Session = Depends(get_db),
    current_user = Depends(get_sales_user),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all measurement requests"""
    query = db.query(DBMeasurementRequest)
    if status_filter:
        query = query.filter(DBMeasurementRequest.status == status_filter)
    
    requests = query.order_by(DBMeasurementRequest.created_at.desc()).offset(skip).limit(limit).all()
    return requests


@router.get("/measurement-requests/{request_id}", response_model=MeasurementRequest)
def get_measurement_request(
    *,
    db: Session = Depends(get_db),
    request_id: int,
    current_user = Depends(get_sales_user)
) -> Any:
    """Get a specific measurement request"""
    request = db.query(DBMeasurementRequest).filter(DBMeasurementRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Measurement request not found")
    return request


@router.put("/measurement-requests/{request_id}", response_model=MeasurementRequest)
def update_measurement_request(
    *,
    db: Session = Depends(get_db),
    request_id: int,
    request_in: MeasurementRequestUpdate,
    current_user = Depends(get_sales_executive)
) -> Any:
    """Update a measurement request"""
    request = db.query(DBMeasurementRequest).filter(DBMeasurementRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Measurement request not found")
    
    update_data = request_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(request, field, value)
    
    db.commit()
    db.refresh(request)
    return request


# Follow-up Endpoints
@router.post("/follow-ups", response_model=FollowUp, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    *,
    db: Session = Depends(get_db),
    follow_up_in: FollowUpCreate,
    current_user = Depends(get_sales_user)
) -> Any:
    """Create a new follow-up"""
    follow_up_data = follow_up_in.model_dump()
    follow_up_data['created_by'] = current_user.id
    
    db_follow_up = DBFollowUp(**follow_up_data)
    db.add(db_follow_up)
    
    # Update lead's last follow-up date if linked
    if follow_up_data.get('lead_id'):
        lead = db.query(DBLead).filter(DBLead.id == follow_up_data['lead_id']).first()
        if lead:
            lead.last_follow_up_date = follow_up_data['follow_up_date']
            if follow_up_data.get('next_follow_up_date'):
                lead.next_follow_up_date = follow_up_data['next_follow_up_date']
    
    db.commit()
    db.refresh(db_follow_up)
    return db_follow_up


@router.get("/follow-ups", response_model=List[FollowUp])
def get_follow_ups(
    db: Session = Depends(get_db),
    current_user = Depends(get_sales_user),
    lead_id: Optional[int] = None,
    sales_order_id: Optional[int] = None,
    party_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all follow-ups"""
    query = db.query(DBFollowUp)
    if lead_id:
        query = query.filter(DBFollowUp.lead_id == lead_id)
    if sales_order_id:
        query = query.filter(DBFollowUp.sales_order_id == sales_order_id)
    if party_id:
        query = query.filter(DBFollowUp.party_id == party_id)
    
    follow_ups = query.order_by(DBFollowUp.follow_up_date.desc()).offset(skip).limit(limit).all()
    return follow_ups


@router.get("/follow-ups/{follow_up_id}", response_model=FollowUp)
def get_follow_up(
    *,
    db: Session = Depends(get_db),
    follow_up_id: int,
    current_user = Depends(get_sales_user)
) -> Any:
    """Get a specific follow-up"""
    follow_up = db.query(DBFollowUp).filter(DBFollowUp.id == follow_up_id).first()
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return follow_up


@router.put("/follow-ups/{follow_up_id}", response_model=FollowUp)
def update_follow_up(
    *,
    db: Session = Depends(get_db),
    follow_up_id: int,
    follow_up_in: FollowUpUpdate,
    current_user = Depends(get_sales_user)
) -> Any:
    """Update a follow-up"""
    follow_up = db.query(DBFollowUp).filter(DBFollowUp.id == follow_up_id).first()
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    update_data = follow_up_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(follow_up, field, value)
    
    db.commit()
    db.refresh(follow_up)
    return follow_up

