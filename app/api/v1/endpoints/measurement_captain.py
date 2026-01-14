from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Any, List, Optional
from datetime import datetime, date

from app.schemas.user import (
    MeasurementTask, MeasurementTaskCreate, MeasurementTaskUpdate,
    MeasurementEntry, MeasurementEntryCreate, MeasurementEntryUpdate,
    Measurement, MeasurementCreate
)
from app.db.models.user import (
    User as DBUser, MeasurementTask as DBMeasurementTask,
    MeasurementEntry as DBMeasurementEntry, Measurement as DBMeasurement, Party
)
from app.api.deps import get_db, get_measurement_captain, get_measurement_task_assigner
import json

router = APIRouter()


def generate_task_number(db: Session) -> str:
    """Generate unique task number MT-YYYYMMDD-XXX"""
    today = datetime.now().strftime("%Y%m%d")
    last_task = db.query(DBMeasurementTask).filter(
        DBMeasurementTask.task_number.like(f"MT-{today}-%")
    ).order_by(DBMeasurementTask.id.desc()).first()
    
    if last_task:
        last_num = int(last_task.task_number.split("-")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"MT-{today}-{new_num:03d}"


def generate_measurement_number(db: Session) -> str:
    """Generate unique measurement number PG-XXX/DD.MM.YYYY"""
    today = datetime.now()
    date_str = today.strftime("%d.%m.%Y")
    
    # Find last measurement number for today
    prefix = f"PG-"
    last_entry = db.query(DBMeasurementEntry).filter(
        DBMeasurementEntry.measurement_number.like(f"{prefix}%")
    ).order_by(DBMeasurementEntry.id.desc()).first()
    
    if last_entry:
        try:
            # Extract number from format PG-XXX/DD.MM.YYYY
            parts = last_entry.measurement_number.split("/")[0].split("-")
            if len(parts) > 1:
                last_num = int(parts[1])
                new_num = last_num + 1
            else:
                new_num = 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"{prefix}{new_num}/{date_str}"


# ============= TASK ASSIGNMENT (Site Supervisor / Sales/Marketing) =============
@router.post("/tasks", response_model=MeasurementTask, status_code=status.HTTP_201_CREATED)
def create_measurement_task(
    task_in: MeasurementTaskCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_task_assigner)
) -> Any:
    """Create a measurement task (Site Supervisor or Sales/Marketing only)"""
    # Verify assigned_to user is a measurement captain
    assigned_user = db.query(DBUser).filter(DBUser.id == task_in.assigned_to).first()
    if not assigned_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found"
        )
    if assigned_user.role != "measurement_captain":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned user must have measurement_captain role"
        )
    
    # Verify party exists if party_id provided
    if task_in.party_id:
        party = db.query(Party).filter(Party.id == task_in.party_id).first()
        if not party:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Party not found"
            )
    
    task_number = generate_task_number(db)
    
    task = DBMeasurementTask(
        **task_in.model_dump(),
        task_number=task_number,
        assigned_by=current_user.id
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return task


@router.get("/tasks")
def get_all_tasks(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_task_assigner),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all measurement tasks (Site Supervisor / Sales/Marketing)"""
    query = db.query(DBMeasurementTask)
    
    if status_filter:
        query = query.filter(DBMeasurementTask.status == status_filter)
    
    tasks = query.order_by(DBMeasurementTask.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get measurement_entry_id for each task
    result = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "task_number": task.task_number,
            "assigned_to": task.assigned_to,
            "assigned_by": task.assigned_by,
            "party_id": task.party_id,
            "party_name": task.party_name,
            "project_site_name": task.project_site_name,
            "site_address": task.site_address,
            "task_description": task.task_description,
            "priority": task.priority,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
        
        # Get measurement_entry_id by querying MeasurementEntry with this task_id
        measurement_entry = db.query(DBMeasurementEntry).filter(
            DBMeasurementEntry.task_id == task.id
        ).first()
        task_dict["measurement_entry_id"] = measurement_entry.id if measurement_entry else None
        
        result.append(task_dict)
    
    return result


# ============= MEASUREMENT CAPTAIN ENDPOINTS =============
@router.get("/my-tasks")
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get tasks assigned to current measurement captain"""
    query = db.query(DBMeasurementTask).filter(
        DBMeasurementTask.assigned_to == current_user.id
    )
    
    if status_filter:
        query = query.filter(DBMeasurementTask.status == status_filter)
    
    tasks = query.order_by(DBMeasurementTask.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get measurement_entry_id for each task
    result = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "task_number": task.task_number,
            "assigned_to": task.assigned_to,
            "assigned_by": task.assigned_by,
            "party_id": task.party_id,
            "party_name": task.party_name,
            "project_site_name": task.project_site_name,
            "site_address": task.site_address,
            "task_description": task.task_description,
            "priority": task.priority,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
        
        # Get measurement_entry_id by querying MeasurementEntry with this task_id
        measurement_entry = db.query(DBMeasurementEntry).filter(
            DBMeasurementEntry.task_id == task.id
        ).first()
        task_dict["measurement_entry_id"] = measurement_entry.id if measurement_entry else None
        
        result.append(task_dict)
    
    return result


@router.get("/my-tasks/{task_id}")
def get_my_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain)
) -> Any:
    """Get a specific task assigned to current measurement captain"""
    task = db.query(DBMeasurementTask).filter(
        and_(
            DBMeasurementTask.id == task_id,
            DBMeasurementTask.assigned_to == current_user.id
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Get measurement_entry_id
    measurement_entry = db.query(DBMeasurementEntry).filter(
        DBMeasurementEntry.task_id == task.id
    ).first()
    
    task_dict = {
        "id": task.id,
        "task_number": task.task_number,
        "assigned_to": task.assigned_to,
        "assigned_by": task.assigned_by,
        "party_id": task.party_id,
        "party_name": task.party_name,
        "project_site_name": task.project_site_name,
        "site_address": task.site_address,
        "task_description": task.task_description,
        "priority": task.priority,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "measurement_entry_id": measurement_entry.id if measurement_entry else None
    }
    
    return task_dict


@router.put("/my-tasks/{task_id}/status", response_model=MeasurementTask)
def update_task_status(
    task_id: int,
    status_update: MeasurementTaskUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain)
) -> Any:
    """Update task status (Measurement Captain only)"""
    task = db.query(DBMeasurementTask).filter(
        and_(
            DBMeasurementTask.id == task_id,
            DBMeasurementTask.assigned_to == current_user.id
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if status_update.status:
        task.status = status_update.status
        if status_update.status == "completed":
            task.completed_at = datetime.now()
    
    if status_update.task_description:
        task.task_description = status_update.task_description
    if status_update.priority:
        task.priority = status_update.priority
    if status_update.due_date:
        task.due_date = status_update.due_date
    
    db.commit()
    db.refresh(task)
    
    return task


# ============= MEASUREMENT ENTRIES =============
# Note: These endpoints now use the unified measurements table
# They convert MeasurementEntry format to Measurement format for backward compatibility
@router.post("/measurements", response_model=Measurement, status_code=status.HTTP_201_CREATED)
def create_measurement_entry(
    measurement_in: MeasurementEntryCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain)
) -> Any:
    """Create a measurement entry (Measurement Captain only) - Now uses unified measurements table"""
    from app.api.v1.endpoints.production import generate_next_measurement_number
    
    # Convert MeasurementEntryCreate to MeasurementCreate format
    # Map category to measurement_type
    category_map = {
        'Sample Frame': 'frame_sample',
        'Sample Shutter': 'shutter_sample',
        'Regular Frame': 'regular_frame',
        'Regular Shutter': 'regular_shutter'
    }
    
    measurement_type = category_map.get(measurement_in.category, 'regular_shutter')
    if not measurement_in.category:
        measurement_type = 'regular_shutter'  # Default
    
    # Generate measurement number if not provided
    if not measurement_in.measurement_number:
        measurement_number = generate_next_measurement_number(db)
    else:
        measurement_number = measurement_in.measurement_number
    
    # Check if measurement number already exists
    existing = db.query(DBMeasurement).filter(
        DBMeasurement.measurement_number == measurement_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measurement number already exists"
        )
    
    # Convert measurement_items to items
    items = measurement_in.measurement_items if hasattr(measurement_in, 'measurement_items') else []
    
    # Create measurement using unified table
    measurement_data = {
        'measurement_type': measurement_type,
        'measurement_number': measurement_number,
        'party_name': measurement_in.party_name,
        'thickness': getattr(measurement_in, 'thickness', None),
        'measurement_date': getattr(measurement_in, 'measurement_date', None),
        'site_location': None,  # MeasurementEntry doesn't have site_location
        'items': items,
        'notes': getattr(measurement_in, 'notes', None),
        'external_foam_patti': getattr(measurement_in, 'external_foam_patti', None),
        'measurement_time': getattr(measurement_in, 'measurement_time', None),
        'task_id': getattr(measurement_in, 'task_id', None),
        'status': 'draft',
        'approval_status': 'pending_approval',  # Measurement Captain creates with pending_approval
    }
    
    # Store additional MeasurementEntry-specific fields in metadata
    metadata = {}
    if hasattr(measurement_in, 'category'):
        metadata['category'] = measurement_in.category
    
    if metadata:
        measurement_data['metadata'] = json.dumps(metadata)
    
    # Convert items to JSON string
    measurement_data['items'] = json.dumps(items)
    
    measurement = DBMeasurement(
        **measurement_data,
        created_by=current_user.id
    )
    
    db.add(measurement)
    db.flush()  # Get the measurement.id
    
    # Update task if task_id provided
    if measurement_data.get('task_id'):
        task = db.query(DBMeasurementTask).filter(
            and_(
                DBMeasurementTask.id == measurement_data['task_id'],
                DBMeasurementTask.assigned_to == current_user.id
            )
        ).first()
        if task:
            task.status = "completed"
            task.completed_at = datetime.now()
    
    db.commit()
    db.refresh(measurement)
    
    # Convert items back to list for response
    items_data = measurement.items
    if items_data:
        if isinstance(items_data, str):
            try:
                items_data = json.loads(items_data)
            except (json.JSONDecodeError, TypeError):
                items_data = []
    
    # Parse metadata
    metadata_data = None
    if measurement.metadata_json:
        if isinstance(measurement.metadata_json, str):
            try:
                metadata_data = json.loads(measurement.metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata_data = {}
        else:
            metadata_data = measurement.metadata_json
    
    # Get username
    username = None
    if measurement.created_by_user:
        username = measurement.created_by_user.username
    
    measurement_dict = {
        'id': measurement.id,
        'measurement_type': measurement.measurement_type,
        'measurement_number': measurement.measurement_number,
        'party_id': measurement.party_id,
        'party_name': measurement.party_name,
        'thickness': measurement.thickness,
        'measurement_date': measurement.measurement_date,
        'site_location': measurement.site_location,
        'items': items_data,
        'notes': measurement.notes,
        'approval_status': measurement.approval_status,
        'external_foam_patti': measurement.external_foam_patti,
        'measurement_time': measurement.measurement_time,
        'task_id': measurement.task_id,
        'status': measurement.status,
        'metadata': metadata_data,
        'rejection_reason': getattr(measurement, 'rejection_reason', None),
        'approved_by': getattr(measurement, 'approved_by', None),
        'approved_at': getattr(measurement, 'approved_at', None),
        'created_by': measurement.created_by,
        'created_at': measurement.created_at,
        'updated_at': measurement.updated_at,
        'created_by_username': username,
    }
    
    return Measurement(**measurement_dict)


@router.get("/measurements", response_model=List[Measurement])
def get_my_measurements(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all measurements created by current measurement captain - Now uses unified measurements table"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(DBMeasurement).options(
        joinedload(DBMeasurement.created_by_user)
    ).filter(
        DBMeasurement.created_by == current_user.id,
        DBMeasurement.is_deleted == False
    )
    
    if status_filter:
        # Map status_filter to approval_status or status field
        if status_filter in ['pending_approval', 'approved', 'rejected']:
            query = query.filter(DBMeasurement.approval_status == status_filter)
        else:
            query = query.filter(DBMeasurement.status == status_filter)
    
    measurements = query.order_by(DBMeasurement.created_at.desc()).offset(skip).limit(limit).all()
    
    # Parse JSON items and metadata
    result = []
    for measurement in measurements:
        # Parse items
        items_data = measurement.items
        if items_data:
            if isinstance(items_data, str):
                try:
                    items_data = json.loads(items_data)
                except (json.JSONDecodeError, TypeError):
                    items_data = []
        
        # Parse metadata
        metadata_data = None
        if measurement.metadata_json:
            if isinstance(measurement.metadata_json, str):
                try:
                    metadata_data = json.loads(measurement.metadata_json)
                except (json.JSONDecodeError, TypeError):
                    metadata_data = {}
            else:
                metadata_data = measurement.metadata_json
        
        username = measurement.created_by_user.username if measurement.created_by_user else None
        
        measurement_dict = {
            'id': measurement.id,
            'measurement_type': measurement.measurement_type,
            'measurement_number': measurement.measurement_number,
            'party_id': measurement.party_id,
            'party_name': measurement.party_name,
            'thickness': measurement.thickness,
            'measurement_date': measurement.measurement_date,
            'site_location': measurement.site_location,
            'items': items_data,
            'notes': measurement.notes,
            'approval_status': measurement.approval_status,
            'external_foam_patti': measurement.external_foam_patti,
            'measurement_time': measurement.measurement_time,
            'task_id': measurement.task_id,
            'status': measurement.status,
            'metadata': metadata_data,
            'rejection_reason': getattr(measurement, 'rejection_reason', None),
            'approved_by': getattr(measurement, 'approved_by', None),
            'approved_at': getattr(measurement, 'approved_at', None),
            'created_by': measurement.created_by,
            'created_at': measurement.created_at,
            'updated_at': measurement.updated_at,
            'created_by_username': username,
        }
        
        result.append(Measurement(**measurement_dict))
        
        entry_dict = {
            "id": entry.id,
            "task_id": entry.task_id,
            "measurement_number": entry.measurement_number,
            "category": entry.category,
            "party_name": entry.party_name,
            "thickness": entry.thickness,
            "external_foam_patti": entry.external_foam_patti,
            "measurement_date": entry.measurement_date,
            "measurement_time": entry.measurement_time,
            "measurement_items": measurement_items,
            "notes": entry.notes,
            "status": entry.status,
            "sent_to_production_at": entry.sent_to_production_at,
            "production_measurement_id": entry.production_measurement_id,
            "created_by": entry.created_by,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at
        }
        result.append(entry_dict)
    
    return result


@router.get("/measurements/{measurement_id}", response_model=Measurement)
def get_measurement_entry(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain)
) -> Any:
    """Get a specific measurement - Now uses unified measurements table"""
    from sqlalchemy.orm import joinedload
    
    measurement = db.query(DBMeasurement).options(
        joinedload(DBMeasurement.created_by_user)
    ).filter(
        DBMeasurement.id == measurement_id,
        DBMeasurement.created_by == current_user.id,
        DBMeasurement.is_deleted == False
    ).first()
    
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found"
        )
    
    # Parse items JSON
    items_data = measurement.items
    if items_data:
        if isinstance(items_data, str):
            try:
                items_data = json.loads(items_data)
            except (json.JSONDecodeError, TypeError):
                items_data = []
    
    # Parse metadata
    metadata_data = None
    if measurement.metadata_json:
        if isinstance(measurement.metadata_json, str):
            try:
                metadata_data = json.loads(measurement.metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata_data = {}
        else:
            metadata_data = measurement.metadata_json
    
    username = measurement.created_by_user.username if measurement.created_by_user else None
    
    measurement_dict = {
        'id': measurement.id,
        'measurement_type': measurement.measurement_type,
        'measurement_number': measurement.measurement_number,
        'party_id': measurement.party_id,
        'party_name': measurement.party_name,
        'thickness': measurement.thickness,
        'measurement_date': measurement.measurement_date,
        'site_location': measurement.site_location,
        'items': items_data,
        'notes': measurement.notes,
        'approval_status': measurement.approval_status,
        'external_foam_patti': measurement.external_foam_patti,
        'measurement_time': measurement.measurement_time,
        'task_id': measurement.task_id,
        'status': measurement.status,
        'metadata': metadata_data,
        'rejection_reason': getattr(measurement, 'rejection_reason', None),
        'approved_by': getattr(measurement, 'approved_by', None),
        'approved_at': getattr(measurement, 'approved_at', None),
        'created_by': measurement.created_by,
        'created_at': measurement.created_at,
        'updated_at': measurement.updated_at,
        'created_by_username': username,
    }
    
    return Measurement(**measurement_dict)


@router.put("/measurements/{measurement_id}", response_model=MeasurementEntry)
def update_measurement_entry(
    measurement_id: int,
    measurement_update: MeasurementEntryUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain)
) -> Any:
    """Update a measurement entry"""
    entry = db.query(DBMeasurementEntry).filter(
        and_(
            DBMeasurementEntry.id == measurement_id,
            DBMeasurementEntry.created_by == current_user.id
        )
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement entry not found"
        )
    
    if entry.status == "sent_to_production":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update measurement that has been sent to production"
        )
    
    if measurement_update.category is not None:
        entry.category = measurement_update.category
    if measurement_update.measurement_items is not None:
        entry.measurement_items = json.dumps(measurement_update.measurement_items)
    if measurement_update.notes is not None:
        entry.notes = measurement_update.notes
    if measurement_update.status:
        entry.status = measurement_update.status
    
    db.commit()
    db.refresh(entry)
    
    # Parse JSON for response
    try:
        measurement_items = json.loads(entry.measurement_items) if entry.measurement_items else []
    except (json.JSONDecodeError, TypeError):
        measurement_items = []
    
    entry_dict = {
        "id": entry.id,
        "task_id": entry.task_id,
        "measurement_number": entry.measurement_number,
        "category": entry.category,
        "party_name": entry.party_name,
        "thickness": entry.thickness,
        "external_foam_patti": entry.external_foam_patti,
        "measurement_date": entry.measurement_date,
        "measurement_time": entry.measurement_time,
        "measurement_items": measurement_items,
        "notes": entry.notes,
        "status": entry.status,
        "sent_to_production_at": entry.sent_to_production_at,
        "production_measurement_id": entry.production_measurement_id,
        "created_by": entry.created_by,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at
    }
    
    return entry_dict


@router.post("/measurements/{measurement_id}/send-to-production", response_model=MeasurementEntry)
def send_to_production(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain)
) -> Any:
    """Send measurement to production documentation system"""
    entry = db.query(DBMeasurementEntry).filter(
        and_(
            DBMeasurementEntry.id == measurement_id,
            DBMeasurementEntry.created_by == current_user.id
        )
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement entry not found"
        )
    
    if entry.status == "sent_to_production":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measurement already sent to production"
        )
    
    # Parse measurement items
    items = json.loads(entry.measurement_items) if entry.measurement_items else []
    
    # Get or create party
    party_id = None
    if entry.party_name:
        party = db.query(Party).filter(Party.name == entry.party_name).first()
        if not party:
            # Create a basic party entry (can be enhanced later)
            party = Party(
                name=entry.party_name,
                party_type="Builder",  # Default
                created_by=current_user.id
            )
            db.add(party)
            db.flush()
        party_id = party.id
    
    # Create production measurement (from existing Measurement model)
    from app.db.models.user import Measurement as DBMeasurement
    
    # Determine measurement type from items (can be enhanced)
    measurement_type = "regular_shutter"  # Default
    
    production_measurement = DBMeasurement(
        measurement_type=measurement_type,
        measurement_number=entry.measurement_number,
        party_id=party_id,
        party_name=entry.party_name,
        thickness=entry.thickness,
        measurement_date=entry.measurement_date or datetime.now(),
        items=entry.measurement_items,  # JSON string
        notes=entry.notes,
        created_by=current_user.id
    )
    
    db.add(production_measurement)
    db.flush()
    
    # Update entry
    entry.status = "sent_to_production"
    entry.sent_to_production_at = datetime.now()
    entry.production_measurement_id = production_measurement.id
    
    db.commit()
    db.refresh(entry)
    db.refresh(production_measurement)
    
    # Parse JSON for response
    try:
        measurement_items = json.loads(entry.measurement_items) if entry.measurement_items else []
    except (json.JSONDecodeError, TypeError):
        measurement_items = []
    
    entry_dict = {
        "id": entry.id,
        "task_id": entry.task_id,
        "measurement_number": entry.measurement_number,
        "category": entry.category,
        "party_name": entry.party_name,
        "thickness": entry.thickness,
        "external_foam_patti": entry.external_foam_patti,
        "measurement_date": entry.measurement_date,
        "measurement_time": entry.measurement_time,
        "measurement_items": measurement_items,
        "notes": entry.notes,
        "status": entry.status,
        "sent_to_production_at": entry.sent_to_production_at,
        "production_measurement_id": entry.production_measurement_id,
        "created_by": entry.created_by,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at
    }
    
    return entry_dict


@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_measurement_captain)
) -> Any:
    """Get dashboard statistics for measurement captain"""
    total_tasks = db.query(DBMeasurementTask).filter(
        DBMeasurementTask.assigned_to == current_user.id
    ).count()
    
    pending_tasks = db.query(DBMeasurementTask).filter(
        and_(
            DBMeasurementTask.assigned_to == current_user.id,
            DBMeasurementTask.status == "assigned"
        )
    ).count()
    
    in_progress_tasks = db.query(DBMeasurementTask).filter(
        and_(
            DBMeasurementTask.assigned_to == current_user.id,
            DBMeasurementTask.status == "in_progress"
        )
    ).count()
    
    completed_tasks = db.query(DBMeasurementTask).filter(
        and_(
            DBMeasurementTask.assigned_to == current_user.id,
            DBMeasurementTask.status == "completed"
        )
    ).count()
    
    total_measurements = db.query(DBMeasurementEntry).filter(
        DBMeasurementEntry.created_by == current_user.id
    ).count()
    
    sent_to_production = db.query(DBMeasurementEntry).filter(
        and_(
            DBMeasurementEntry.created_by == current_user.id,
            DBMeasurementEntry.status == "sent_to_production"
        )
    ).count()
    
    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completed_tasks": completed_tasks,
        "total_measurements": total_measurements,
        "sent_to_production": sent_to_production
    }

