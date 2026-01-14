from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from typing import Any, List, Optional
from datetime import datetime, date, timedelta

from app.schemas.user import (
    ProductionTask, ProductionTaskUpdate, ProductionTaskCreate,
    ProductionIssue, ProductionIssueCreate, ProductionIssueUpdate,
    TaskProgress, TaskProgressCreate
)
from app.db.models.user import (
    User as DBUser, ProductionSchedule, ProductionTask as DBProductionTask,
    ProductionIssue as DBProductionIssue, TaskProgress as DBTaskProgress,
    ProductionSupervisor, Department, ProductionPaper
)
from app.api.deps import get_db, get_production_supervisor
import json

router = APIRouter()


def get_supervisor_profile(db: Session, user_id: int) -> Optional[ProductionSupervisor]:
    """Get supervisor profile for a user"""
    return db.query(ProductionSupervisor).filter(
        and_(
            ProductionSupervisor.user_id == user_id,
            ProductionSupervisor.is_active == True
        )
    ).first()


@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Get dashboard statistics for supervisor"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    department_id = supervisor.department_id
    
    # Count tasks by status
    urgent_pending = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.status == "Pending",
            DBProductionTask.order_type == "Urgent"
        )
    ).count()
    
    regular_pending = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.status == "Pending",
            DBProductionTask.order_type == "Regular"
        )
    ).count()
    
    sample_pending = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.status == "Pending",
            DBProductionTask.order_type == "Sample"
        )
    ).count()
    
    wip_count = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.status == "In Progress"
        )
    ).count()
    
    today = date.today()
    completed_today = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.status == "Completed",
            func.date(DBProductionTask.completed_at) == today
        )
    ).count()
    
    return {
        "urgent_pending": urgent_pending,
        "regular_pending": regular_pending,
        "sample_pending": sample_pending,
        "wip_count": wip_count,
        "completed_today": completed_today
    }


@router.get("/dashboard/tasks")
def get_dashboard_tasks(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor),
    skip: int = 0,
    limit: int = 50
) -> Any:
    """Get tasks overview for dashboard"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    department_id = supervisor.department_id
    
    tasks = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.supervisor_type == supervisor.supervisor_type
        )
    ).offset(skip).limit(limit).all()
    
    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "production_paper_no": task.production_paper_no,
            "party_name": task.party_name,
            "product_type": task.product_type,
            "order_type": task.order_type,
            "stage": task.department.name if task.department else None,
            "quantity": task.quantity,
            "planned_date": task.planned_start_date.isoformat() if task.planned_start_date else None,
            "status": task.status
        })
    
    return result


@router.get("/tasks/new")
def get_new_tasks(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get newly assigned tasks (Pending status)"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    department_id = supervisor.department_id
    
    # Filter tasks by supervisor type
    tasks = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.status == "Pending",
            DBProductionTask.supervisor_type == supervisor.supervisor_type
        )
    ).offset(skip).limit(limit).all()
    
    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "production_paper_no": task.production_paper_no,
            "department": task.department.name if task.department else None,
            "product_type": task.product_type,
            "order_type": task.order_type,
            "quantity": task.quantity,
            "planned_start_date": task.planned_start_date.isoformat() if task.planned_start_date else None,
            "status": task.status
        })
    
    return result


@router.post("/tasks/{task_id}/accept")
def accept_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Accept a new task"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id,
            DBProductionTask.supervisor_type == supervisor.supervisor_type,
            DBProductionTask.status == "Pending"
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not available"
        )
    
    # Update task
    task.status = "Accepted"
    task.supervisor_id = supervisor.id
    task.accepted_at = datetime.now()
    task.start_time = datetime.now()
    
    # Calculate expected end time (if planned_end_date exists)
    if task.planned_end_date:
        task.expected_end_time = datetime.combine(task.planned_end_date, datetime.min.time())
    
    db.commit()
    db.refresh(task)
    
    return {"message": "Task accepted successfully", "task": task}


@router.post("/tasks/{task_id}/reject")
def reject_task(
    task_id: int,
    reason_data: dict,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Reject a task with reason"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id,
            DBProductionTask.status == "Pending"
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not available"
        )
    
    # Update task
    reason = reason_data.get("reason", "")
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required"
        )
    
    task.status = "Rejected"
    task.rejection_reason = reason
    task.supervisor_id = supervisor.id
    
    db.commit()
    db.refresh(task)
    
    return {"message": "Task rejected", "task": task}


@router.get("/tasks")
def get_all_tasks(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor),
    status_filter: Optional[str] = None,
    order_type: Optional[str] = None,
    product_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all tasks with filters"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    department_id = supervisor.department_id
    
    query = db.query(DBProductionTask).filter(
        DBProductionTask.department_id == department_id
    )
    
    if status_filter:
        query = query.filter(DBProductionTask.status == status_filter)
    if order_type:
        query = query.filter(DBProductionTask.order_type == order_type)
    if product_type:
        query = query.filter(DBProductionTask.product_type == product_type)
    
    tasks = query.offset(skip).limit(limit).all()
    
    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "production_paper_no": task.production_paper_no,
            "party_name": task.party_name,
            "product_type": task.product_type,
            "order_type": task.order_type,
            "quantity": task.quantity,
            "planned_start_date": task.planned_start_date.isoformat() if task.planned_start_date else None,
            "status": task.status,
            "quantity_completed": task.quantity_completed,
            "balance_quantity": task.balance_quantity
        })
    
    return result


@router.get("/tasks/wip")
def get_wip_tasks(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get work in progress tasks"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    department_id = supervisor.department_id
    
    tasks = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.supervisor_type == supervisor.supervisor_type,
            DBProductionTask.status == "In Progress"
        )
    ).offset(skip).limit(limit).all()
    
    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "production_paper_no": task.production_paper_no,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "expected_end_time": task.expected_end_time.isoformat() if task.expected_end_time else None,
            "quantity_completed": task.quantity_completed,
            "balance_quantity": task.balance_quantity,
            "rework_qty": task.rework_qty,
            "status": task.status
        })
    
    return result


@router.get("/tasks/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Get task details"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task


@router.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    task_update: ProductionTaskUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Update task progress"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    update_data = task_update.model_dump(exclude_unset=True)
    
    # Update quantity completed and balance
    if "quantity_completed" in update_data:
        task.quantity_completed = update_data["quantity_completed"]
        task.balance_quantity = task.quantity - task.quantity_completed
    
    # Update status
    if "status" in update_data:
        task.status = update_data["status"]
        if update_data["status"] == "In Progress" and not task.start_time:
            task.start_time = datetime.now()
        elif update_data["status"] == "Completed":
            task.completed_at = datetime.now()
            task.actual_end_time = datetime.now()
    
    # Update other fields
    for field, value in update_data.items():
        if field != "quantity_completed" and field != "status":
            setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    
    return task


@router.post("/tasks/{task_id}/pause")
def pause_task(
    task_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Pause a task with reason"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id,
            DBProductionTask.supervisor_type == supervisor.supervisor_type,
            DBProductionTask.status == "In Progress"
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not in progress"
        )
    
    task.status = "On Hold"
    task.on_hold_reason = reason
    task.paused_at = datetime.now()
    
    db.commit()
    db.refresh(task)
    
    return {"message": "Task paused", "task": task}


@router.post("/tasks/{task_id}/resume")
def resume_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Resume a paused task"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id,
            DBProductionTask.supervisor_type == supervisor.supervisor_type,
            DBProductionTask.status == "On Hold"
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not on hold"
        )
    
    task.status = "In Progress"
    task.resumed_at = datetime.now()
    
    db.commit()
    db.refresh(task)
    
    return {"message": "Task resumed", "task": task}


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Mark task stage as completed"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id,
            DBProductionTask.supervisor_type == supervisor.supervisor_type,
            DBProductionTask.status == "In Progress"
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not in progress"
        )
    
    task.status = "Completed"
    task.completed_at = datetime.now()
    task.actual_end_time = datetime.now()
    
    db.commit()
    db.refresh(task)
    
    return {"message": "Task completed", "task": task}


@router.post("/tasks/{task_id}/progress")
def update_progress(
    task_id: int,
    progress: TaskProgressCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Update task progress"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    task = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.id == task_id,
            DBProductionTask.department_id == supervisor.department_id
        )
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Create progress update
    progress_update = DBTaskProgress(
        task_id=task_id,
        quantity_completed=progress.quantity_completed,
        rework_qty=progress.rework_qty,
        notes=progress.notes,
        updated_by=current_user.id
    )
    db.add(progress_update)
    
    # Update task
    task.quantity_completed = progress.quantity_completed
    task.balance_quantity = task.quantity - progress.quantity_completed
    task.rework_qty = progress.rework_qty
    
    if task.status == "Accepted":
        task.status = "In Progress"
        if not task.start_time:
            task.start_time = datetime.now()
    
    db.commit()
    db.refresh(task)
    db.refresh(progress_update)
    
    return {"message": "Progress updated", "progress": progress_update}


@router.get("/tasks/completed")
def get_completed_tasks(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get completed tasks"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    department_id = supervisor.department_id
    
    tasks = db.query(DBProductionTask).filter(
        and_(
            DBProductionTask.department_id == department_id,
            DBProductionTask.supervisor_type == supervisor.supervisor_type,
            DBProductionTask.status == "Completed"
        )
    ).order_by(DBProductionTask.completed_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for task in tasks:
        time_taken = None
        if task.start_time and task.actual_end_time:
            time_taken = (task.actual_end_time - task.start_time).total_seconds() / 3600  # hours
        
        result.append({
            "id": task.id,
            "production_paper_no": task.production_paper_no,
            "completion_date": task.completed_at.isoformat() if task.completed_at else None,
            "actual_time_taken": time_taken,
            "quantity_completed": task.quantity_completed,
            "rework_count": task.rework_qty,
            "quality_status": task.quality_status
        })
    
    return result


@router.post("/issues", response_model=ProductionIssue, status_code=status.HTTP_201_CREATED)
def create_issue(
    issue_in: ProductionIssueCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Report a production issue"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    # Auto-assign based on issue type
    assigned_to = None
    if issue_in.issue_type == "Material Shortage":
        assigned_to = "Purchase / Store"
    elif issue_in.issue_type == "Machine Breakdown":
        assigned_to = "Maintenance Captain"
    elif issue_in.issue_type == "Quality Issue":
        assigned_to = "QC"
    elif issue_in.issue_type == "Design / Measurement Issue":
        assigned_to = "Engineering"
    
    issue = DBProductionIssue(
        **issue_in.model_dump(),
        reported_by=current_user.id,
        assigned_to=assigned_to,
        status="Open"
    )
    
    db.add(issue)
    
    # Update task status to On Hold if critical
    if issue_in.severity == "Critical":
        task = db.query(DBProductionTask).filter(DBProductionTask.id == issue_in.task_id).first()
        if task and task.status == "In Progress":
            task.status = "On Hold"
            task.on_hold_reason = f"Issue reported: {issue_in.issue_type}"
            task.paused_at = datetime.now()
    
    db.commit()
    db.refresh(issue)
    
    return issue


@router.get("/issues")
def get_issues(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all issues reported by supervisor"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    issues = db.query(DBProductionIssue).filter(
        DBProductionIssue.reported_by == current_user.id
    ).order_by(DBProductionIssue.reported_at.desc()).offset(skip).limit(limit).all()
    
    return issues


@router.get("/issues/{issue_id}")
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor)
) -> Any:
    """Get issue details"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    issue = db.query(DBProductionIssue).filter(
        and_(
            DBProductionIssue.id == issue_id,
            DBProductionIssue.reported_by == current_user.id
        )
    ).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    return issue


@router.get("/reports/summary")
def get_report_summary(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_production_supervisor),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Any:
    """Get department performance summary"""
    supervisor = get_supervisor_profile(db, current_user.id)
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor profile not found"
        )
    
    department_id = supervisor.department_id
    
    # Build query
    query = db.query(DBProductionTask).filter(
        DBProductionTask.department_id == department_id
    )
    
    if start_date:
        query = query.filter(DBProductionTask.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(DBProductionTask.created_at <= datetime.combine(end_date, datetime.max.time()))
    
    tasks = query.all()
    
    total_assigned = len(tasks)
    total_completed = len([t for t in tasks if t.status == "Completed"])
    total_delayed = len([t for t in tasks if t.status in ["On Hold", "Pending"]])
    
    # Issue count by type
    issues_query = db.query(DBProductionIssue).filter(
        DBProductionIssue.department_id == department_id
    )
    if start_date:
        issues_query = issues_query.filter(DBProductionIssue.reported_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        issues_query = issues_query.filter(DBProductionIssue.reported_at <= datetime.combine(end_date, datetime.max.time()))
    
    issues = issues_query.all()
    issue_count_by_type = {}
    for issue in issues:
        issue_count_by_type[issue.issue_type] = issue_count_by_type.get(issue.issue_type, 0) + 1
    
    # Rework percentage
    total_rework = sum([t.rework_qty for t in tasks if t.rework_qty])
    total_quantity = sum([t.quantity for t in tasks])
    rework_percentage = (total_rework / total_quantity * 100) if total_quantity > 0 else 0
    
    return {
        "tasks_assigned": total_assigned,
        "tasks_completed": total_completed,
        "tasks_delayed": total_delayed,
        "completion_rate": (total_completed / total_assigned * 100) if total_assigned > 0 else 0,
        "delay_reasons": issue_count_by_type,
        "issue_count_by_type": issue_count_by_type,
        "rework_percentage": round(rework_percentage, 2),
        "supervisor_efficiency": round((total_completed / total_assigned * 100) if total_assigned > 0 else 0, 2)
    }

