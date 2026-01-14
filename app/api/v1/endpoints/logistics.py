from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_

from app.schemas.logistics import (
    Vehicle, VehicleCreate, VehicleUpdate,
    Driver, DriverCreate, DriverUpdate,
    LogisticsAssignment, LogisticsAssignmentCreate, LogisticsAssignmentUpdate,
    DeliveryIssue, DeliveryIssueCreate, DeliveryIssueUpdate
)
from app.schemas.dispatch import DeliveryTracking, DeliveryTrackingUpdate
from app.db.models.logistics import (
    Vehicle as DBVehicle,
    Driver as DBDriver,
    LogisticsAssignment as DBLogisticsAssignment,
    DeliveryIssue as DBDeliveryIssue
)
from app.db.models.dispatch import (
    Dispatch as DBDispatch,
    DeliveryTracking as DBDeliveryTracking
)
from app.api.deps import (
    get_db, get_logistics_manager, get_logistics_executive, 
    get_logistics_user, get_driver, get_current_user
)

router = APIRouter()


# ============= DASHBOARD =============
@router.get("/dashboard/stats")
def get_logistics_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user)
) -> Any:
    """Get logistics dashboard statistics"""
    today = date.today()
    
    # Orders Assigned Today
    assigned_today = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.assigned_at >= datetime.combine(today, datetime.min.time()),
        DBLogisticsAssignment.assigned_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
    ).count()
    
    # In Transit
    in_transit = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.status == "in_transit"
    ).count()
    
    # Delivered Today
    delivered_today = db.query(DBDispatch).filter(
        DBDispatch.status == "delivered",
        DBDispatch.dispatched_at >= datetime.combine(today, datetime.min.time()),
        DBDispatch.dispatched_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
    ).count()
    
    # Delayed Deliveries
    delayed = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.status == "delayed"
    ).count()
    
    # Vehicle Availability
    total_vehicles = db.query(DBVehicle).count()
    available_vehicles = db.query(DBVehicle).filter(
        DBVehicle.is_available == True
    ).count()
    
    return {
        "orders_assigned_today": assigned_today,
        "in_transit": in_transit,
        "delivered_today": delivered_today,
        "delayed_deliveries": delayed,
        "vehicle_availability": available_vehicles,
        "total_vehicles": total_vehicles
    }


@router.get("/dashboard/live-deliveries")
def get_live_deliveries(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    limit: int = 20
) -> Any:
    """Get live delivery board"""
    assignments = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.status.in_(["assigned", "in_transit"])
    ).order_by(DBLogisticsAssignment.planned_delivery_date.asc()).limit(limit).all()
    
    result = []
    for assignment in assignments:
        dispatch = db.query(DBDispatch).filter(
            DBDispatch.id == assignment.dispatch_id
        ).first()
        
        if dispatch:
            # Calculate ETA (simplified - can be enhanced with actual routing)
            result.append({
                "dispatch_number": dispatch.dispatch_number,
                "party_name": dispatch.party_name,
                "vehicle_no": assignment.vehicle_no,
                "driver_name": assignment.driver_name,
                "status": assignment.status,
                "planned_delivery_date": assignment.planned_delivery_date,
                "route_area": assignment.route_area
            })
    
    return result


# ============= ASSIGNED DISPATCH ORDERS =============
@router.get("/assigned-orders")
def get_assigned_dispatch_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None
) -> Any:
    """Get dispatch orders assigned to logistics (read-only)"""
    # Get all approved dispatches
    query = db.query(DBDispatch).filter(
        DBDispatch.status.in_(["approved", "dispatched"])
    )
    
    if status_filter:
        query = query.filter(DBDispatch.status == status_filter)
    
    dispatches = query.order_by(DBDispatch.dispatch_date.desc()).offset(skip).limit(limit).all()
    
    result = []
    for dispatch in dispatches:
        # Check if already assigned
        assignment = db.query(DBLogisticsAssignment).filter(
            DBLogisticsAssignment.dispatch_id == dispatch.id
        ).first()
        
        # Get delivery tracking
        tracking = db.query(DBDeliveryTracking).filter(
            DBDeliveryTracking.dispatch_id == dispatch.id
        ).first()
        
        result.append({
            "id": dispatch.id,
            "dispatch_number": dispatch.dispatch_number,
            "party_name": dispatch.party_name,
            "delivery_address": dispatch.delivery_address,
            "dispatch_date": dispatch.dispatch_date,
            "expected_delivery_date": dispatch.expected_delivery_date,
            "status": dispatch.status,
            "is_assigned": assignment is not None,
            "assignment_status": assignment.status if assignment else None,
            "delivery_status": tracking.status if tracking else "pending",
            "dc_number": dispatch.dc_number,
            "invoice_number": dispatch.invoice_number,
            "production_paper_number": dispatch.production_paper_number
        })
    
    return result


@router.get("/assigned-orders/{dispatch_id}")
def get_assigned_order_details(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user)
) -> Any:
    """Get detailed view of an assigned dispatch order (read-only)"""
    dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch order not found")
    
    # Get items
    items = [{
        "product_type": item.product_type,
        "product_description": item.product_description,
        "quantity": item.quantity,
        "packaging_type": item.packaging_type,
        "weight": item.weight,
        "volume": item.volume
    } for item in dispatch.dispatch_items]
    
    # Get assignment if exists
    assignment = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.dispatch_id == dispatch_id
    ).first()
    
    # Get tracking if exists
    tracking = db.query(DBDeliveryTracking).filter(
        DBDeliveryTracking.dispatch_id == dispatch_id
    ).first()
    
    return {
        "dispatch": {
            "id": dispatch.id,
            "dispatch_number": dispatch.dispatch_number,
            "party_name": dispatch.party_name,
            "delivery_address": dispatch.delivery_address,
            "dispatch_date": dispatch.dispatch_date,
            "expected_delivery_date": dispatch.expected_delivery_date,
            "status": dispatch.status,
            "dc_number": dispatch.dc_number,
            "invoice_number": dispatch.invoice_number,
            "production_paper_number": dispatch.production_paper_number,
            "remarks": dispatch.remarks
        },
        "items": items,
        "assignment": {
            "vehicle_no": assignment.vehicle_no if assignment else None,
            "driver_name": assignment.driver_name if assignment else None,
            "driver_mobile": assignment.driver_mobile if assignment else None,
            "planned_delivery_date": assignment.planned_delivery_date if assignment else None,
            "route_area": assignment.route_area if assignment else None,
            "status": assignment.status if assignment else None
        } if assignment else None,
        "tracking": {
            "status": tracking.status if tracking else None,
            "delivered_date": tracking.delivered_date if tracking else None,
            "receiver_name": tracking.receiver_name if tracking else None,
            "delay_reason": tracking.delay_reason if tracking else None
        } if tracking else None
    }


# ============= VEHICLE & DRIVER MASTER =============
@router.get("/vehicles", response_model=List[Vehicle])
def get_vehicles(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    available_only: bool = False
) -> Any:
    """Get all vehicles"""
    query = db.query(DBVehicle)
    if available_only:
        query = query.filter(DBVehicle.is_available == True)
    return query.order_by(DBVehicle.vehicle_no).all()


@router.post("/vehicles", response_model=Vehicle)
def create_vehicle(
    vehicle: VehicleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_manager)
) -> Any:
    """Create a new vehicle (Logistics Manager only)"""
    # Check if vehicle_no already exists
    existing = db.query(DBVehicle).filter(DBVehicle.vehicle_no == vehicle.vehicle_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vehicle number already exists")
    
    db_vehicle = DBVehicle(**vehicle.dict())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle


@router.put("/vehicles/{vehicle_id}", response_model=Vehicle)
def update_vehicle(
    vehicle_id: int,
    vehicle: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_manager)
) -> Any:
    """Update vehicle (Logistics Manager only)"""
    db_vehicle = db.query(DBVehicle).filter(DBVehicle.id == vehicle_id).first()
    if not db_vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    update_data = vehicle.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_vehicle, field, value)
    
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle


@router.get("/drivers", response_model=List[Driver])
def get_drivers(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    active_only: bool = False
) -> Any:
    """Get all drivers"""
    query = db.query(DBDriver)
    if active_only:
        query = query.filter(DBDriver.is_active == True)
    return query.order_by(DBDriver.name).all()


@router.post("/drivers", response_model=Driver)
def create_driver(
    driver: DriverCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_manager)
) -> Any:
    """Create a new driver (Logistics Manager only)"""
    # Check if mobile or license already exists
    existing_mobile = db.query(DBDriver).filter(DBDriver.mobile == driver.mobile).first()
    if existing_mobile:
        raise HTTPException(status_code=400, detail="Driver mobile number already exists")
    
    existing_license = db.query(DBDriver).filter(DBDriver.license_number == driver.license_number).first()
    if existing_license:
        raise HTTPException(status_code=400, detail="Driver license number already exists")
    
    db_driver = DBDriver(**driver.dict())
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    return db_driver


@router.put("/drivers/{driver_id}", response_model=Driver)
def update_driver(
    driver_id: int,
    driver: DriverUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_manager)
) -> Any:
    """Update driver (Logistics Manager only)"""
    db_driver = db.query(DBDriver).filter(DBDriver.id == driver_id).first()
    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    update_data = driver.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_driver, field, value)
    
    db.commit()
    db.refresh(db_driver)
    return db_driver


# ============= VEHICLE & DRIVER ASSIGNMENT =============
@router.post("/assignments", response_model=LogisticsAssignment)
def create_assignment(
    assignment: LogisticsAssignmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_manager)
) -> Any:
    """Assign vehicle and driver to a dispatch order (Logistics Manager only)"""
    # Check if dispatch exists and is approved
    dispatch = db.query(DBDispatch).filter(DBDispatch.id == assignment.dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch order not found")
    
    if dispatch.status not in ["approved", "dispatched"]:
        raise HTTPException(status_code=400, detail="Dispatch order must be approved before assignment")
    
    # Check if already assigned
    existing = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.dispatch_id == assignment.dispatch_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dispatch order already has an assignment")
    
    # Get vehicle and driver details
    vehicle = db.query(DBVehicle).filter(DBVehicle.id == assignment.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if not vehicle.is_available:
        raise HTTPException(status_code=400, detail="Vehicle is not available")
    
    driver = db.query(DBDriver).filter(DBDriver.id == assignment.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    if not driver.is_active:
        raise HTTPException(status_code=400, detail="Driver is not active")
    
    # Create assignment
    db_assignment = DBLogisticsAssignment(
        dispatch_id=assignment.dispatch_id,
        dispatch_number=dispatch.dispatch_number,
        vehicle_id=assignment.vehicle_id,
        vehicle_no=vehicle.vehicle_no,
        driver_id=assignment.driver_id,
        driver_name=driver.name,
        driver_mobile=driver.mobile,
        planned_delivery_date=assignment.planned_delivery_date,
        route_area=assignment.route_area,
        assignment_notes=assignment.assignment_notes,
        status="assigned",
        assigned_by=current_user.id
    )
    
    # Update vehicle availability
    vehicle.is_available = False
    
    # Update dispatch status
    dispatch.status = "dispatched"
    dispatch.vehicle_no = vehicle.vehicle_no
    dispatch.driver_name = driver.name
    dispatch.driver_mobile = driver.mobile
    dispatch.dispatched_at = datetime.now()
    
    # Create delivery tracking
    tracking = db.query(DBDeliveryTracking).filter(
        DBDeliveryTracking.dispatch_id == assignment.dispatch_id
    ).first()
    
    if not tracking:
        tracking = DBDeliveryTracking(
            dispatch_id=assignment.dispatch_id,
            dispatch_number=dispatch.dispatch_number,
            status="dispatched"
        )
        db.add(tracking)
    
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


@router.put("/assignments/{assignment_id}", response_model=LogisticsAssignment)
def update_assignment(
    assignment_id: int,
    assignment: LogisticsAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_manager)
) -> Any:
    """Update assignment (Logistics Manager only)"""
    db_assignment = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.id == assignment_id
    ).first()
    
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    update_data = assignment.dict(exclude_unset=True)
    
    # Handle vehicle change
    if "vehicle_id" in update_data:
        vehicle = db.query(DBVehicle).filter(DBVehicle.id == update_data["vehicle_id"]).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        # Release old vehicle
        old_vehicle = db.query(DBVehicle).filter(DBVehicle.id == db_assignment.vehicle_id).first()
        if old_vehicle:
            old_vehicle.is_available = True
        
        # Assign new vehicle
        db_assignment.vehicle_id = vehicle.id
        db_assignment.vehicle_no = vehicle.vehicle_no
        vehicle.is_available = False
    
    # Handle driver change
    if "driver_id" in update_data:
        driver = db.query(DBDriver).filter(DBDriver.id == update_data["driver_id"]).first()
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        db_assignment.driver_id = driver.id
        db_assignment.driver_name = driver.name
        db_assignment.driver_mobile = driver.mobile
    
    # Handle status change
    if "status" in update_data:
        db_assignment.status = update_data["status"]
        
        # Update delivery tracking status
        tracking = db.query(DBDeliveryTracking).filter(
            DBDeliveryTracking.dispatch_id == db_assignment.dispatch_id
        ).first()
        
        if tracking:
            tracking.status = update_data["status"]
            
            # If delivered, release vehicle
            if update_data["status"] == "delivered":
                vehicle = db.query(DBVehicle).filter(DBVehicle.id == db_assignment.vehicle_id).first()
                if vehicle:
                    vehicle.is_available = True
                
                dispatch = db.query(DBDispatch).filter(DBDispatch.id == db_assignment.dispatch_id).first()
                if dispatch:
                    dispatch.status = "delivered"
                
                tracking.status = "delivered"
                tracking.delivered_date = datetime.now()
    
    # Update other fields
    for field, value in update_data.items():
        if field not in ["vehicle_id", "driver_id", "status"]:
            setattr(db_assignment, field, value)
    
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


@router.get("/assignments", response_model=List[LogisticsAssignment])
def get_assignments(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    status_filter: Optional[str] = None
) -> Any:
    """Get all assignments"""
    query = db.query(DBLogisticsAssignment)
    if status_filter:
        query = query.filter(DBLogisticsAssignment.status == status_filter)
    return query.order_by(DBLogisticsAssignment.assigned_at.desc()).all()


# ============= DELIVERY TRACKING =============
@router.get("/tracking", response_model=List[DeliveryTracking])
def get_delivery_tracking(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    status_filter: Optional[str] = None
) -> Any:
    """Get all delivery tracking records"""
    query = db.query(DBDeliveryTracking)
    if status_filter:
        query = query.filter(DBDeliveryTracking.status == status_filter)
    return query.order_by(DBDeliveryTracking.updated_at.desc()).all()


@router.put("/tracking/{dispatch_id}", response_model=DeliveryTracking)
def update_delivery_tracking(
    dispatch_id: int,
    tracking: DeliveryTrackingUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_executive)
) -> Any:
    """Update delivery tracking (Logistics Executive or Driver)"""
    db_tracking = db.query(DBDeliveryTracking).filter(
        DBDeliveryTracking.dispatch_id == dispatch_id
    ).first()
    
    if not db_tracking:
        raise HTTPException(status_code=404, detail="Delivery tracking not found")
    
    update_data = tracking.dict(exclude_unset=True)
    
    # If marking as delivered, update assignment and dispatch
    if "status" in update_data and update_data["status"] == "delivered":
        assignment = db.query(DBLogisticsAssignment).filter(
            DBLogisticsAssignment.dispatch_id == dispatch_id
        ).first()
        
        if assignment:
            assignment.status = "delivered"
            # Release vehicle
            vehicle = db.query(DBVehicle).filter(DBVehicle.id == assignment.vehicle_id).first()
            if vehicle:
                vehicle.is_available = True
        
        dispatch = db.query(DBDispatch).filter(DBDispatch.id == dispatch_id).first()
        if dispatch:
            dispatch.status = "delivered"
        
        db_tracking.delivered_date = datetime.now()
    
    # Update fields
    for field, value in update_data.items():
        if field != "status" or update_data["status"] != "delivered":
            setattr(db_tracking, field, value)
    
    db_tracking.status = update_data.get("status", db_tracking.status)
    db_tracking.updated_by = current_user.id
    db_tracking.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_tracking)
    return db_tracking


@router.get("/tracking/{dispatch_id}", response_model=DeliveryTracking)
def get_delivery_tracking_by_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user)
) -> Any:
    """Get delivery tracking for a specific dispatch"""
    tracking = db.query(DBDeliveryTracking).filter(
        DBDeliveryTracking.dispatch_id == dispatch_id
    ).first()
    
    if not tracking:
        raise HTTPException(status_code=404, detail="Delivery tracking not found")
    
    return tracking


# ============= DELIVERY ISSUES =============
@router.post("/issues", response_model=DeliveryIssue)
def create_delivery_issue(
    issue: DeliveryIssueCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user)
) -> Any:
    """Report a delivery issue"""
    # Verify dispatch exists
    dispatch = db.query(DBDispatch).filter(DBDispatch.id == issue.dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch order not found")
    
    db_issue = DBDeliveryIssue(
        dispatch_id=issue.dispatch_id,
        dispatch_number=dispatch.dispatch_number,
        issue_type=issue.issue_type,
        title=issue.title,
        description=issue.description,
        severity=issue.severity,
        issue_photo_url=issue.issue_photo_url,
        status="reported",
        reported_by=current_user.id
    )
    
    # If delay, update assignment status
    if issue.issue_type == "delivery_delay":
        assignment = db.query(DBLogisticsAssignment).filter(
            DBLogisticsAssignment.dispatch_id == issue.dispatch_id
        ).first()
        if assignment:
            assignment.status = "delayed"
        
        tracking = db.query(DBDeliveryTracking).filter(
            DBDeliveryTracking.dispatch_id == issue.dispatch_id
        ).first()
        if tracking:
            tracking.status = "delayed"
            tracking.delay_reason = issue.description
        
        dispatch = db.query(DBDispatch).filter(DBDispatch.id == issue.dispatch_id).first()
        if dispatch:
            dispatch.status = "delayed"
    
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    return db_issue


@router.get("/issues", response_model=List[DeliveryIssue])
def get_delivery_issues(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    status_filter: Optional[str] = None
) -> Any:
    """Get all delivery issues"""
    query = db.query(DBDeliveryIssue)
    if status_filter:
        query = query.filter(DBDeliveryIssue.status == status_filter)
    return query.order_by(DBDeliveryIssue.created_at.desc()).all()


@router.put("/issues/{issue_id}", response_model=DeliveryIssue)
def update_delivery_issue(
    issue_id: int,
    issue: DeliveryIssueUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_manager)
) -> Any:
    """Update delivery issue (Logistics Manager only - for review/resolution)"""
    db_issue = db.query(DBDeliveryIssue).filter(DBDeliveryIssue.id == issue_id).first()
    if not db_issue:
        raise HTTPException(status_code=404, detail="Delivery issue not found")
    
    update_data = issue.dict(exclude_unset=True)
    
    if "status" in update_data:
        db_issue.status = update_data["status"]
        if update_data["status"] == "resolved":
            db_issue.resolved_at = datetime.now()
            db_issue.reviewed_by = current_user.id
    
    if "resolution_notes" in update_data:
        db_issue.resolution_notes = update_data["resolution_notes"]
    
    if "reviewed_by" in update_data:
        db_issue.reviewed_by = update_data["reviewed_by"]
    
    db.commit()
    db.refresh(db_issue)
    return db_issue


# ============= REPORTS =============
@router.get("/reports/summary")
def get_logistics_reports_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_logistics_user),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Any:
    """Get logistics reports summary"""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    
    # Total deliveries
    total_deliveries = db.query(DBDispatch).filter(
        DBDispatch.status == "delivered",
        DBDispatch.dispatched_at >= datetime.combine(start_date, datetime.min.time()),
        DBDispatch.dispatched_at <= datetime.combine(end_date, datetime.max.time())
    ).count()
    
    # On-time deliveries
    on_time_deliveries = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.status == "delivered",
        DBLogisticsAssignment.planned_delivery_date >= start_date,
        DBLogisticsAssignment.planned_delivery_date <= end_date
    ).join(DBDispatch).filter(
        DBDispatch.status == "delivered",
        DBDispatch.dispatched_at <= datetime.combine(DBLogisticsAssignment.planned_delivery_date, datetime.max.time())
    ).count()
    
    # Vehicle utilization
    total_assignments = db.query(DBLogisticsAssignment).filter(
        DBLogisticsAssignment.assigned_at >= datetime.combine(start_date, datetime.min.time()),
        DBLogisticsAssignment.assigned_at <= datetime.combine(end_date, datetime.max.time())
    ).count()
    
    # Delay reasons analysis
    delay_issues = db.query(DBDeliveryIssue).filter(
        DBDeliveryIssue.issue_type == "delivery_delay",
        DBDeliveryIssue.created_at >= datetime.combine(start_date, datetime.min.time()),
        DBDeliveryIssue.created_at <= datetime.combine(end_date, datetime.max.time())
    ).all()
    
    delay_reasons = {}
    for issue in delay_issues:
        reason = issue.description[:50]  # First 50 chars as reason summary
        delay_reasons[reason] = delay_reasons.get(reason, 0) + 1
    
    on_time_percentage = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "total_deliveries": total_deliveries,
        "on_time_deliveries": on_time_deliveries,
        "on_time_percentage": round(on_time_percentage, 2),
        "delayed_deliveries": len(delay_issues),
        "vehicle_assignments": total_assignments,
        "delay_reasons_analysis": delay_reasons
    }
