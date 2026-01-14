from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from typing import Any, List, Optional
from datetime import datetime, date, timedelta
import json

from app.schemas.carpenter import (
    CarpenterCaptain, CarpenterCaptainCreate,
    WorkAllocation, WorkAllocationCreate,
    FrameFixing, FrameFixingCreate,
    DoorFixing, DoorFixingCreate,
    CarpenterAttendance, CarpenterAttendanceCreate,
    CarpenterIssue, CarpenterIssueCreate,
    WorkCompletion, WorkCompletionCreate,
    CarpenterDashboardStats
)
from app.db.models.carpenter import (
    CarpenterCaptain as DBCarpenterCaptain,
    WorkAllocation as DBWorkAllocation,
    CarpenterFrameFixing as DBFrameFixing,
    CarpenterDoorFixing as DBDoorFixing,
    CarpenterAttendance as DBCarpenterAttendance,
    CarpenterIssue as DBCarpenterIssue,
    WorkCompletion as DBWorkCompletion
)
from app.db.models.site_supervisor import Site, Flat
from app.api.deps import get_db, get_carpenter_captain, get_site_supervisor, get_current_user
from app.db.models.user import User as DBUser

router = APIRouter()


def get_captain_by_user_id(db: Session, user_id: int) -> Optional[DBCarpenterCaptain]:
    """Get carpenter captain by user ID"""
    return db.query(DBCarpenterCaptain).filter(DBCarpenterCaptain.user_id == user_id).first()


# Dashboard
@router.get("/dashboard/stats", response_model=CarpenterDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Get dashboard statistics for carpenter captain"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        # Return zero stats if captain not assigned yet
        return CarpenterDashboardStats(
            doors_fixed_today=0,
            frames_fixed_today=0,
            carpenters_present=0,
            issues_open=0,
            pending_flats=0,
            today_work_list=[]
        )
    
    today = date.today()
    
    # Doors fixed today
    doors_fixed_today = db.query(func.count(DBDoorFixing.id)).filter(
        and_(
            DBDoorFixing.captain_id == captain.id,
            DBDoorFixing.fixing_date == today,
            DBDoorFixing.fixing_status == "Completed"
        )
    ).scalar() or 0
    
    # Frames fixed today
    frames_fixed_today = db.query(func.count(DBFrameFixing.id)).filter(
        and_(
            DBFrameFixing.captain_id == captain.id,
            DBFrameFixing.fixing_date == today,
            DBFrameFixing.fixing_status == "Completed"
        )
    ).scalar() or 0
    
    # Carpenters present today
    carpenters_present = db.query(func.count(func.distinct(DBCarpenterAttendance.carpenter_name))).filter(
        and_(
            DBCarpenterAttendance.captain_id == captain.id,
            DBCarpenterAttendance.attendance_date == today,
            DBCarpenterAttendance.present == True
        )
    ).scalar() or 0
    
    # Issues open
    issues_open = db.query(func.count(DBCarpenterIssue.id)).filter(
        and_(
            DBCarpenterIssue.captain_id == captain.id,
            DBCarpenterIssue.status == "Open"
        )
    ).scalar() or 0
    
    # Pending flats (flats with incomplete fixing)
    pending_flats = db.query(func.count(func.distinct(Flat.id))).join(
        Site, Flat.site_id == Site.id
    ).filter(
        and_(
            Site.id == captain.site_id,
            or_(
                Flat.frame_fixed == False,
                Flat.door_fixed == False
            )
        )
    ).scalar() or 0
    
    # Today's work list
    today_work_list = []
    work_allocations = db.query(DBWorkAllocation).filter(
        and_(
            DBWorkAllocation.captain_id == captain.id,
            DBWorkAllocation.allocation_date == today
        )
    ).all()
    
    for allocation in work_allocations:
        flat_nums = json.loads(allocation.flat_numbers) if isinstance(allocation.flat_numbers, str) else allocation.flat_numbers
        for flat_num in flat_nums[:5]:  # Limit to first 5
            today_work_list.append({
                "flat_no": flat_num,
                "work_type": allocation.work_type,
                "status": allocation.status
            })
    
    return CarpenterDashboardStats(
        doors_fixed_today=doors_fixed_today,
        frames_fixed_today=frames_fixed_today,
        carpenters_present=carpenters_present,
        issues_open=issues_open,
        pending_flats=pending_flats,
        today_work_list=today_work_list
    )


# Assigned Site & Wing
@router.get("/assigned-site")
def get_assigned_site(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Get assigned site and wing for captain"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        return {
            "site": null,
            "flats": [],
            "message": "You have not been assigned to any site yet. Please contact your administrator."
        }
    
    site = db.query(Site).filter(Site.id == captain.site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    wings = json.loads(site.wings) if site.wings else []
    assigned_wings = json.loads(captain.wing) if captain.wing and isinstance(captain.wing, str) else (captain.wing if captain.wing else [])
    
    # Get flats for assigned wings
    flats = db.query(Flat).filter(
        and_(
            Flat.site_id == captain.site_id,
            Flat.wing.in_(assigned_wings) if assigned_wings else True
        )
    ).all()
    
    return {
        "site": {
            "id": site.id,
            "project_name": site.project_name,
            "location": site.location,
            "wings": wings,
            "assigned_wings": assigned_wings,
            "total_floors": site.total_floors,
            "total_flats": site.total_flats
        },
        "flats": [
            {
                "id": flat.id,
                "flat_number": flat.flat_number,
                "wing": flat.wing,
                "floor": flat.floor,
                "frame_fixed": flat.frame_fixed,
                "door_fixed": flat.door_fixed
            }
            for flat in flats
        ]
    }


# Work Allocation
@router.post("/work-allocation", response_model=WorkAllocation, status_code=status.HTTP_201_CREATED)
def create_work_allocation(
    *,
    db: Session = Depends(get_db),
    allocation_in: WorkAllocationCreate,
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Create daily work allocation"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpenter captain assignment not found"
        )
    
    allocation_data = allocation_in.model_dump()
    allocation_data["captain_id"] = captain.id
    allocation_data["flat_numbers"] = json.dumps(allocation_data["flat_numbers"])
    if allocation_data.get("assigned_carpenters"):
        allocation_data["assigned_carpenters"] = json.dumps(allocation_data["assigned_carpenters"])
    
    allocation = DBWorkAllocation(**allocation_data)
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    
    # Parse flat_numbers back to list for response
    allocation.flat_numbers = json.loads(allocation.flat_numbers) if isinstance(allocation.flat_numbers, str) else allocation.flat_numbers
    if allocation.assigned_carpenters:
        allocation.assigned_carpenters = json.loads(allocation.assigned_carpenters) if isinstance(allocation.assigned_carpenters, str) else allocation.assigned_carpenters
    
    return allocation


@router.get("/work-allocation", response_model=List[WorkAllocation])
def list_work_allocations(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
) -> Any:
    """List work allocations"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        # Return empty list if captain not assigned yet
        return []
    
    query = db.query(DBWorkAllocation).filter(DBWorkAllocation.captain_id == captain.id)
    
    if start_date:
        query = query.filter(DBWorkAllocation.allocation_date >= start_date)
    if end_date:
        query = query.filter(DBWorkAllocation.allocation_date <= end_date)
    
    allocations = query.order_by(DBWorkAllocation.allocation_date.desc()).all()
    
    # Parse JSON fields
    for allocation in allocations:
        allocation.flat_numbers = json.loads(allocation.flat_numbers) if isinstance(allocation.flat_numbers, str) else allocation.flat_numbers
        if allocation.assigned_carpenters:
            allocation.assigned_carpenters = json.loads(allocation.assigned_carpenters) if isinstance(allocation.assigned_carpenters, str) else allocation.assigned_carpenters
    
    return allocations


# Frame Fixing
@router.post("/frame-fixing", response_model=FrameFixing, status_code=status.HTTP_201_CREATED)
def create_frame_fixing(
    *,
    db: Session = Depends(get_db),
    fixing_in: FrameFixingCreate,
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Create frame fixing record"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpenter captain assignment not found"
        )
    
    fixing_data = fixing_in.model_dump()
    fixing_data["captain_id"] = captain.id
    
    fixing = DBFrameFixing(**fixing_data)
    db.add(fixing)
    
    # Update flat status if completed
    if fixing_in.fixing_status == "Completed":
        flat = db.query(Flat).filter(Flat.id == fixing_in.flat_id).first()
        if flat:
            flat.frame_fixed = True
    
    db.commit()
    db.refresh(fixing)
    return fixing


@router.get("/frame-fixing", response_model=List[FrameFixing])
def list_frame_fixings(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain),
    flat_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None)
) -> Any:
    """List frame fixing records"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        # Return empty list if captain not assigned yet
        return []
    
    query = db.query(DBFrameFixing).filter(DBFrameFixing.captain_id == captain.id)
    
    if flat_id:
        query = query.filter(DBFrameFixing.flat_id == flat_id)
    if status:
        query = query.filter(DBFrameFixing.fixing_status == status)
    
    return query.order_by(DBFrameFixing.fixing_date.desc()).all()


# Door Fixing
@router.post("/door-fixing", response_model=DoorFixing, status_code=status.HTTP_201_CREATED)
def create_door_fixing(
    *,
    db: Session = Depends(get_db),
    fixing_in: DoorFixingCreate,
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Create door fixing record"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpenter captain assignment not found"
        )
    
    fixing_data = fixing_in.model_dump()
    fixing_data["captain_id"] = captain.id
    
    fixing = DBDoorFixing(**fixing_data)
    db.add(fixing)
    
    # Update flat status if completed
    if fixing_in.fixing_status == "Completed":
        flat = db.query(Flat).filter(Flat.id == fixing_in.flat_id).first()
        if flat:
            flat.door_fixed = True
    
    db.commit()
    db.refresh(fixing)
    return fixing


@router.get("/door-fixing", response_model=List[DoorFixing])
def list_door_fixings(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain),
    flat_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None)
) -> Any:
    """List door fixing records"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        # Return empty list if captain not assigned yet
        return []
    
    query = db.query(DBDoorFixing).filter(DBDoorFixing.captain_id == captain.id)
    
    if flat_id:
        query = query.filter(DBDoorFixing.flat_id == flat_id)
    if status:
        query = query.filter(DBDoorFixing.fixing_status == status)
    
    return query.order_by(DBDoorFixing.fixing_date.desc()).all()


# Carpenter Attendance
@router.post("/attendance", response_model=CarpenterAttendance, status_code=status.HTTP_201_CREATED)
def create_attendance(
    *,
    db: Session = Depends(get_db),
    attendance_in: CarpenterAttendanceCreate,
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Create carpenter attendance record"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpenter captain assignment not found"
        )
    
    attendance_data = attendance_in.model_dump()
    attendance_data["captain_id"] = captain.id
    
    attendance = DBCarpenterAttendance(**attendance_data)
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.get("/attendance", response_model=List[CarpenterAttendance])
def list_attendance(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain),
    attendance_date: Optional[date] = Query(None)
) -> Any:
    """List carpenter attendance records"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        # Return empty list if captain not assigned yet
        return []
    
    query = db.query(DBCarpenterAttendance).filter(DBCarpenterAttendance.captain_id == captain.id)
    
    if attendance_date:
        query = query.filter(DBCarpenterAttendance.attendance_date == attendance_date)
    
    return query.order_by(DBCarpenterAttendance.attendance_date.desc()).all()


# Issues
@router.post("/issues", response_model=CarpenterIssue, status_code=status.HTTP_201_CREATED)
def create_issue(
    *,
    db: Session = Depends(get_db),
    issue_in: CarpenterIssueCreate,
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Create carpenter issue"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpenter captain assignment not found"
        )
    
    issue_data = issue_in.model_dump()
    issue_data["captain_id"] = captain.id
    
    issue = DBCarpenterIssue(**issue_data)
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/issues", response_model=List[CarpenterIssue])
def list_issues(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain),
    status: Optional[str] = Query(None)
) -> Any:
    """List carpenter issues"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        # Return empty list if captain not assigned yet
        return []
    
    query = db.query(DBCarpenterIssue).filter(DBCarpenterIssue.captain_id == captain.id)
    
    if status:
        query = query.filter(DBCarpenterIssue.status == status)
    
    return query.order_by(DBCarpenterIssue.reported_date.desc()).all()


# Work Completion
@router.post("/work-completion", response_model=WorkCompletion, status_code=status.HTTP_201_CREATED)
def create_work_completion(
    *,
    db: Session = Depends(get_db),
    completion_in: WorkCompletionCreate,
    current_user: DBUser = Depends(get_carpenter_captain)
) -> Any:
    """Create work completion summary"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpenter captain assignment not found"
        )
    
    completion_data = completion_in.model_dump()
    completion_data["captain_id"] = captain.id
    
    completion = DBWorkCompletion(**completion_data)
    db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion


@router.get("/work-completion", response_model=List[WorkCompletion])
def list_work_completions(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_carpenter_captain),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
) -> Any:
    """List work completion summaries"""
    captain = get_captain_by_user_id(db, current_user.id)
    if not captain:
        # Return empty list if captain not assigned yet
        return []
    
    query = db.query(DBWorkCompletion).filter(DBWorkCompletion.captain_id == captain.id)
    
    if start_date:
        query = query.filter(DBWorkCompletion.summary_date >= start_date)
    if end_date:
        query = query.filter(DBWorkCompletion.summary_date <= end_date)
    
    return query.order_by(DBWorkCompletion.summary_date.desc()).all()


# Supervisor Approval Endpoints
@router.post("/frame-fixing/{fixing_id}/approve")
def approve_frame_fixing(
    fixing_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Approve frame fixing (Site Supervisor only)"""
    fixing = db.query(DBFrameFixing).filter(DBFrameFixing.id == fixing_id).first()
    if not fixing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frame fixing record not found"
        )
    
    fixing.supervisor_approved = True
    fixing.approved_by = current_user.id
    fixing.approved_at = datetime.now()
    
    db.commit()
    return {"message": "Frame fixing approved successfully"}


@router.post("/door-fixing/{fixing_id}/approve")
def approve_door_fixing(
    fixing_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Approve door fixing (Site Supervisor only)"""
    fixing = db.query(DBDoorFixing).filter(DBDoorFixing.id == fixing_id).first()
    if not fixing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Door fixing record not found"
        )
    
    fixing.supervisor_approved = True
    fixing.approved_by = current_user.id
    fixing.approved_at = datetime.now()
    
    db.commit()
    return {"message": "Door fixing approved successfully"}


@router.post("/work-completion/{completion_id}/approve")
def approve_work_completion(
    completion_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Approve work completion (Site Supervisor only)"""
    completion = db.query(DBWorkCompletion).filter(DBWorkCompletion.id == completion_id).first()
    if not completion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work completion record not found"
        )
    
    completion.supervisor_approved = True
    completion.approved_by = current_user.id
    completion.approved_at = datetime.now()
    
    db.commit()
    return {"message": "Work completion approved successfully"}

