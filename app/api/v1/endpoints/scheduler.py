from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from datetime import datetime, date
import json

from app.schemas.user import (
    ProductionSchedule, 
    ProductionScheduleCreate, 
    ProductionScheduleUpdate,
    DepartmentScheduleItem
)
from app.db.models.user import (
    ProductionSchedule as DBProductionSchedule,
    ProductionPaper as DBProductionPaper,
    Measurement as DBMeasurement,
    Party as DBParty
)
from app.api.deps import get_db, get_production_scheduler

router = APIRouter()


def serialize_department_schedule(department_schedule: List[DepartmentScheduleItem]) -> str:
    """Convert department schedule list to JSON string, handling datetime serialization"""
    dept_schedule_list = []
    for item in department_schedule:
        item_dict = item.model_dump()
        # Convert datetime objects to ISO format strings
        if item_dict.get('planned_start') and isinstance(item_dict['planned_start'], datetime):
            item_dict['planned_start'] = item_dict['planned_start'].isoformat()
        elif item_dict.get('planned_start') and isinstance(item_dict['planned_start'], date):
            item_dict['planned_start'] = item_dict['planned_start'].isoformat()
        
        if item_dict.get('planned_end') and isinstance(item_dict['planned_end'], datetime):
            item_dict['planned_end'] = item_dict['planned_end'].isoformat()
        elif item_dict.get('planned_end') and isinstance(item_dict['planned_end'], date):
            item_dict['planned_end'] = item_dict['planned_end'].isoformat()
        
        dept_schedule_list.append(item_dict)
    
    return json.dumps(dept_schedule_list)


def check_material_availability(production_paper: DBProductionPaper, db: Session) -> dict:
    """Check material availability for a production paper"""
    checks = {
        "measurement_received": False,
        "production_paper_approved": False,
        "shutter_available": False,
        "laminate_available": False,
        "frame_material_available": False
    }
    
    # Check if measurement exists
    if production_paper.measurement_id:
        measurement = db.query(DBMeasurement).filter(DBMeasurement.id == production_paper.measurement_id).first()
        if measurement:
            checks["measurement_received"] = True
    
    # Check if production paper is approved
    if production_paper.status == "active" or production_paper.status == "approved":
        checks["production_paper_approved"] = True
    
    # TODO: Add actual material availability checks from inventory/purchase system
    # For now, we'll set defaults
    checks["shutter_available"] = True  # Placeholder
    checks["laminate_available"] = True  # Placeholder
    checks["frame_material_available"] = True  # Placeholder
    
    return checks


@router.get("/pending-for-scheduling", response_model=List[Any])
def get_pending_for_scheduling(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_scheduler),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get production papers that are not yet scheduled"""
    # Get all production papers that don't have a schedule
    scheduled_paper_ids = db.query(DBProductionSchedule.production_paper_id).distinct().all()
    scheduled_ids = [row[0] for row in scheduled_paper_ids]
    
    query = db.query(DBProductionPaper).filter(
        DBProductionPaper.status.in_(["active", "approved", "draft"])
    )
    
    if scheduled_ids:
        query = query.filter(~DBProductionPaper.id.in_(scheduled_ids))
    
    papers = query.offset(skip).limit(limit).all()
    
    result = []
    for paper in papers:
        # Get party info
        party_name = None
        if paper.party_id:
            party = db.query(DBParty).filter(DBParty.id == paper.party_id).first()
            if party:
                party_name = party.name
        
        # Get measurement info to determine product type
        product_type = "Unknown"
        if paper.measurement_id:
            measurement = db.query(DBMeasurement).filter(DBMeasurement.id == paper.measurement_id).first()
            if measurement:
                if "shutter" in measurement.measurement_type.lower():
                    product_type = "Door"
                elif "frame" in measurement.measurement_type.lower():
                    product_type = "Frame"
        
        # Determine order type (can be enhanced based on priority/urgency)
        order_type = "Regular"
        if paper.status == "active":
            order_type = "Urgent"
        
        # Check material availability
        material_checks = check_material_availability(paper, db)
        
        result.append({
            "production_paper_id": paper.id,
            "paper_number": paper.paper_number,
            "party_name": party_name,
            "product_type": product_type,
            "order_type": order_type,
            "quantity": 1,  # TODO: Get from measurement items
            "expected_dispatch_date": None,  # TODO: Calculate from party preferences
            "raw_material_status": "Available" if all([
                material_checks["shutter_available"],
                material_checks["laminate_available"],
                material_checks["frame_material_available"]
            ]) else "Pending",
            "material_checks": material_checks
        })
    
    return result


@router.post("/schedule", response_model=ProductionSchedule)
def create_schedule(
    *,
    db: Session = Depends(get_db),
    schedule_in: ProductionScheduleCreate,
    current_user = Depends(get_production_scheduler)
) -> Any:
    """Create a new production schedule"""
    try:
        # Check if production paper exists
        production_paper = db.query(DBProductionPaper).filter(
            DBProductionPaper.id == schedule_in.production_paper_id
        ).first()
        
        if not production_paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production paper not found"
            )
        
        # Check if already scheduled
        existing_schedule = db.query(DBProductionSchedule).filter(
            DBProductionSchedule.production_paper_id == schedule_in.production_paper_id
        ).first()
        
        if existing_schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Production paper is already scheduled"
            )
        
        # Check material availability
        material_checks = check_material_availability(production_paper, db)
        
        # Convert department schedule to JSON
        department_schedule_json = None
        if schedule_in.department_schedule and len(schedule_in.department_schedule) > 0:
            try:
                department_schedule_json = serialize_department_schedule(schedule_in.department_schedule)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid department schedule format: {str(e)}"
                )
        
        # Handle date conversion
        try:
            if isinstance(schedule_in.production_start_date, datetime):
                production_start_date = schedule_in.production_start_date.date()
            elif isinstance(schedule_in.production_start_date, date):
                production_start_date = schedule_in.production_start_date
            else:
                production_start_date = schedule_in.production_start_date
            
            if isinstance(schedule_in.target_completion_date, datetime):
                target_completion_date = schedule_in.target_completion_date.date()
            elif isinstance(schedule_in.target_completion_date, date):
                target_completion_date = schedule_in.target_completion_date
            else:
                target_completion_date = schedule_in.target_completion_date
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {str(e)}"
            )
        
        # Create schedule
        db_schedule = DBProductionSchedule(
            production_paper_id=schedule_in.production_paper_id,
            production_start_date=production_start_date,
            target_completion_date=target_completion_date,
            priority=schedule_in.priority,
            department_schedule=department_schedule_json,
            primary_supervisor=schedule_in.primary_supervisor,
            backup_supervisor=schedule_in.backup_supervisor,
            remarks=schedule_in.remarks,
            status="Scheduled",
            measurement_received=material_checks["measurement_received"],
            production_paper_approved=material_checks["production_paper_approved"],
            shutter_available=material_checks["shutter_available"],
            laminate_available=material_checks["laminate_available"],
            frame_material_available=material_checks["frame_material_available"],
            scheduled_by=current_user.id
        )
        
        db.add(db_schedule)
        db.commit()
        db.refresh(db_schedule)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create schedule: {str(e)}"
        )
    
    # Parse department schedule back
    schedule_dict = {
        "id": db_schedule.id,
        "production_paper_id": db_schedule.production_paper_id,
        "production_start_date": db_schedule.production_start_date,
        "target_completion_date": db_schedule.target_completion_date,
        "priority": db_schedule.priority,
        "department_schedule": json.loads(db_schedule.department_schedule) if db_schedule.department_schedule else None,
        "primary_supervisor": db_schedule.primary_supervisor,
        "backup_supervisor": db_schedule.backup_supervisor,
        "remarks": db_schedule.remarks,
        "status": db_schedule.status,
        "measurement_received": db_schedule.measurement_received,
        "production_paper_approved": db_schedule.production_paper_approved,
        "shutter_available": db_schedule.shutter_available,
        "laminate_available": db_schedule.laminate_available,
        "frame_material_available": db_schedule.frame_material_available,
        "scheduled_by": db_schedule.scheduled_by,
        "created_at": db_schedule.created_at,
        "updated_at": db_schedule.updated_at
    }
    
    return ProductionSchedule(**schedule_dict)


@router.get("/schedules", response_model=List[Any])
def get_schedules(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_scheduler),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    order_type: Optional[str] = None,
    product_type: Optional[str] = None,
    supervisor: Optional[str] = None
) -> Any:
    """Get all production schedules with filters"""
    query = db.query(DBProductionSchedule)
    
    # Apply filters
    if status_filter:
        query = query.filter(DBProductionSchedule.status == status_filter)
    if supervisor:
        query = query.filter(
            (DBProductionSchedule.primary_supervisor == supervisor) |
            (DBProductionSchedule.backup_supervisor == supervisor)
        )
    
    schedules = query.offset(skip).limit(limit).all()
    
    result = []
    for schedule in schedules:
        # Get production paper info
        paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == schedule.production_paper_id).first()
        if not paper:
            continue
        
        # Get party info
        party_name = None
        if paper.party_id:
            party = db.query(DBParty).filter(DBParty.id == paper.party_id).first()
            if party:
                party_name = party.name
        
        # Get product type
        product_type_val = "Unknown"
        if paper.measurement_id:
            measurement = db.query(DBMeasurement).filter(DBMeasurement.id == paper.measurement_id).first()
            if measurement:
                if "shutter" in measurement.measurement_type.lower():
                    product_type_val = "Door"
                elif "frame" in measurement.measurement_type.lower():
                    product_type_val = "Frame"
        
        # Determine order type
        order_type_val = "Regular"
        if schedule.priority == "High":
            order_type_val = "Urgent"
        elif schedule.priority == "Low":
            order_type_val = "Sample"
        
        # Apply filters
        if order_type and order_type_val != order_type:
            continue
        if product_type and product_type_val != product_type:
            continue
        
        # Parse department schedule
        department_schedule = None
        if schedule.department_schedule:
            try:
                department_schedule = json.loads(schedule.department_schedule)
            except:
                pass
        
        result.append({
            "id": schedule.id,
            "production_paper_id": schedule.production_paper_id,
            "paper_number": paper.paper_number,
            "party_name": party_name,
            "product_type": product_type_val,
            "order_type": order_type_val,
            "start_date": schedule.production_start_date,
            "target_date": schedule.target_completion_date,
            "supervisor": schedule.primary_supervisor,
            "current_stage": "Scheduled",  # TODO: Get from production tracking
            "status": schedule.status,
            "priority": schedule.priority,
            "department_schedule": department_schedule
        })
    
    return result


@router.get("/schedules/{schedule_id}", response_model=ProductionSchedule)
def get_schedule(
    *,
    db: Session = Depends(get_db),
    schedule_id: int,
    current_user = Depends(get_production_scheduler)
) -> Any:
    """Get a specific production schedule"""
    schedule = db.query(DBProductionSchedule).filter(DBProductionSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Parse department schedule
    department_schedule = None
    if schedule.department_schedule:
        try:
            department_schedule = json.loads(schedule.department_schedule)
        except:
            pass
    
    schedule_dict = {
        "id": schedule.id,
        "production_paper_id": schedule.production_paper_id,
        "production_start_date": schedule.production_start_date,
        "target_completion_date": schedule.target_completion_date,
        "priority": schedule.priority,
        "department_schedule": department_schedule,
        "primary_supervisor": schedule.primary_supervisor,
        "backup_supervisor": schedule.backup_supervisor,
        "remarks": schedule.remarks,
        "status": schedule.status,
        "measurement_received": schedule.measurement_received,
        "production_paper_approved": schedule.production_paper_approved,
        "shutter_available": schedule.shutter_available,
        "laminate_available": schedule.laminate_available,
        "frame_material_available": schedule.frame_material_available,
        "scheduled_by": schedule.scheduled_by,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at
    }
    
    return ProductionSchedule(**schedule_dict)


@router.put("/schedules/{schedule_id}", response_model=ProductionSchedule)
def update_schedule(
    *,
    db: Session = Depends(get_db),
    schedule_id: int,
    schedule_in: ProductionScheduleUpdate,
    current_user = Depends(get_production_scheduler)
) -> Any:
    """Update a production schedule (for rescheduling/maintenance)"""
    db_schedule = db.query(DBProductionSchedule).filter(DBProductionSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Validate reason for change if dates are being changed
    if (schedule_in.production_start_date or schedule_in.target_completion_date) and not schedule_in.reason_for_change:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason for change is required when rescheduling"
        )
    
    # Update fields
    if schedule_in.production_start_date is not None:
        db_schedule.production_start_date = schedule_in.production_start_date.date() if isinstance(schedule_in.production_start_date, datetime) else schedule_in.production_start_date
    if schedule_in.target_completion_date is not None:
        db_schedule.target_completion_date = schedule_in.target_completion_date.date() if isinstance(schedule_in.target_completion_date, datetime) else schedule_in.target_completion_date
    if schedule_in.priority is not None:
        db_schedule.priority = schedule_in.priority
    if schedule_in.department_schedule is not None:
        try:
            if len(schedule_in.department_schedule) > 0:
                db_schedule.department_schedule = serialize_department_schedule(schedule_in.department_schedule)
            else:
                db_schedule.department_schedule = None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid department schedule format: {str(e)}"
            )
    if schedule_in.primary_supervisor is not None:
        db_schedule.primary_supervisor = schedule_in.primary_supervisor
    if schedule_in.backup_supervisor is not None:
        db_schedule.backup_supervisor = schedule_in.backup_supervisor
    if schedule_in.status is not None:
        db_schedule.status = schedule_in.status
    if schedule_in.remarks is not None:
        # Append reason to remarks if provided
        if schedule_in.reason_for_change:
            existing_remarks = db_schedule.remarks or ""
            db_schedule.remarks = f"{existing_remarks}\n[Change Reason: {schedule_in.reason_for_change}]" if existing_remarks else f"[Change Reason: {schedule_in.reason_for_change}]"
        else:
            db_schedule.remarks = schedule_in.remarks
    
    db.commit()
    db.refresh(db_schedule)
    
    # Parse department schedule back
    department_schedule = None
    if db_schedule.department_schedule:
        try:
            department_schedule = json.loads(db_schedule.department_schedule)
        except:
            pass
    
    schedule_dict = {
        "id": db_schedule.id,
        "production_paper_id": db_schedule.production_paper_id,
        "production_start_date": db_schedule.production_start_date,
        "target_completion_date": db_schedule.target_completion_date,
        "priority": db_schedule.priority,
        "department_schedule": department_schedule,
        "primary_supervisor": db_schedule.primary_supervisor,
        "backup_supervisor": db_schedule.backup_supervisor,
        "remarks": db_schedule.remarks,
        "status": db_schedule.status,
        "measurement_received": db_schedule.measurement_received,
        "production_paper_approved": db_schedule.production_paper_approved,
        "shutter_available": db_schedule.shutter_available,
        "laminate_available": db_schedule.laminate_available,
        "frame_material_available": db_schedule.frame_material_available,
        "scheduled_by": db_schedule.scheduled_by,
        "created_at": db_schedule.created_at,
        "updated_at": db_schedule.updated_at
    }
    
    return ProductionSchedule(**schedule_dict)


@router.get("/dashboard/stats", response_model=dict)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_scheduler)
) -> Any:
    """Get dashboard statistics for production scheduler"""
    # Get all production papers
    all_papers = db.query(DBProductionPaper).filter(
        DBProductionPaper.status.in_(["active", "approved", "draft"])
    ).all()
    
    # Get scheduled paper IDs
    scheduled_paper_ids = db.query(DBProductionSchedule.production_paper_id).distinct().all()
    scheduled_ids = [row[0] for row in scheduled_paper_ids]
    
    # Count pending for scheduling
    pending_count = len([p for p in all_papers if p.id not in scheduled_ids])
    
    # Count by order type (simplified - can be enhanced)
    urgent_pending = 0
    regular_pending = 0
    sample_pending = 0
    
    for paper in all_papers:
        if paper.id not in scheduled_ids:
            if paper.status == "active":
                urgent_pending += 1
            else:
                regular_pending += 1
    
    # Get schedules by status
    scheduled_count = db.query(DBProductionSchedule).filter(
        DBProductionSchedule.status == "Scheduled"
    ).count()
    
    in_production_count = db.query(DBProductionSchedule).filter(
        DBProductionSchedule.status == "In Production"
    ).count()
    
    completed_count = db.query(DBProductionSchedule).filter(
        DBProductionSchedule.status == "Completed"
    ).count()
    
    # Get today's scheduled production
    today = date.today()
    today_schedules = db.query(DBProductionSchedule).filter(
        DBProductionSchedule.production_start_date == today
    ).all()
    
    return {
        "urgent_orders_pending": urgent_pending,
        "regular_orders_pending": regular_pending,
        "sample_orders": sample_pending,
        "orders_in_production": in_production_count,
        "ready_for_dispatch": completed_count,
        "today_scheduled_count": len(today_schedules)
    }


@router.get("/dashboard/today-scheduled", response_model=List[Any])
def get_today_scheduled(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_scheduler)
) -> Any:
    """Get today's scheduled production"""
    today = date.today()
    schedules = db.query(DBProductionSchedule).filter(
        DBProductionSchedule.production_start_date == today
    ).all()
    
    result = []
    for schedule in schedules:
        paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == schedule.production_paper_id).first()
        if not paper:
            continue
        
        # Get product type
        product_type = "Unknown"
        if paper.measurement_id:
            measurement = db.query(DBMeasurement).filter(DBMeasurement.id == paper.measurement_id).first()
            if measurement:
                if "shutter" in measurement.measurement_type.lower():
                    product_type = "Door"
                elif "frame" in measurement.measurement_type.lower():
                    product_type = "Frame"
        
        # Parse department schedule
        department_schedule = None
        if schedule.department_schedule:
            try:
                department_schedule = json.loads(schedule.department_schedule)
            except:
                pass
        
        # Get first department if available
        current_stage = "Scheduled"
        if department_schedule and len(department_schedule) > 0:
            current_stage = department_schedule[0].get("department", "Scheduled")
        
        result.append({
            "id": schedule.id,
            "supervisor": schedule.primary_supervisor,
            "department": current_stage,
            "product_type": product_type,
            "stage": current_stage,
            "quantity": 1,  # TODO: Get from measurement
            "status": schedule.status
        })
    
    return result

