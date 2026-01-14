from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Any, List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field

from app.schemas.user import (
    User, UserCreate, UserProfileUpdate,
    Department, DepartmentCreate,
    ProductionSupervisor, ProductionSupervisorCreate, ProductionSupervisorUpdate
)
from app.db.models.user import (
    User as DBUser, Measurement, Party, ProductionPaper,
    Department as DBDepartment,
    ProductionSupervisor as DBProductionSupervisor
)
from app.api.deps import get_db, get_admin
from app.core import security

router = APIRouter()

# Request/Response Models
class SerialPrefixAssign(BaseModel):
    prefix: str = Field(..., description="Single uppercase letter (A-Z)", min_length=1, max_length=1)

# User Management Endpoints
@router.get("/users", response_model=List[User])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all users (admin only)"""
    users = db.query(DBUser).offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Get a specific user by ID (admin only)"""
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/users/{user_id}/assign-serial-prefix", response_model=User, status_code=status.HTTP_200_OK)
def assign_serial_prefix(
    user_id: int,
    prefix_data: SerialPrefixAssign,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Assign serial number prefix to a Measurement Captain or Production Manager user (admin only)
    
    Accepts prefix in request body: {"prefix": "A"}
    """
    import re
    prefix = prefix_data.prefix.upper()
    
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate user is a Measurement Captain or Production Manager
    if user.role not in ['measurement_captain', 'production_manager']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serial number prefix can only be assigned to Measurement Captain or Production Manager users"
        )
    
    # Validate prefix format: single uppercase letter A-Z
    if not re.match(r'^[A-Z]$', prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prefix must be a single uppercase letter (A-Z)"
        )
    
    # Check if prefix is already assigned to another Measurement Captain or Production Manager user
    existing_user = db.query(DBUser).filter(
        and_(
            DBUser.serial_number_prefix == prefix,
            DBUser.id != user_id,
            DBUser.role.in_(['measurement_captain', 'production_manager'])
        )
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prefix '{prefix}' is already assigned to user '{existing_user.username}'. Each prefix must be unique."
        )
    
    # Assign prefix and reset counter
    user.serial_number_prefix = prefix
    user.serial_number_counter = 0  # Reset counter when assigning/changing prefix
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Create a new user (admin only)"""
    # Check if email already exists
    db_user = db.query(DBUser).filter(DBUser.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists."
        )
    
    # Check if username already exists
    db_user = db.query(DBUser).filter(DBUser.username == user_in.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The username is already taken."
        )
    
    # Hash the password
    hashed_password = security.get_password_hash(user_in.password)
    
    # Create new user
    db_user = DBUser(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password,
        role=user_in.role,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.put("/users/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Update a user (admin only)"""
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Check if email is being updated and if it's already taken
    if 'email' in update_data and update_data['email'] != user.email:
        existing_user = db.query(DBUser).filter(DBUser.email == update_data['email']).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists."
            )
    
    # Check if username is being updated and if it's already taken
    if 'username' in update_data and update_data['username'] != user.username:
        existing_user = db.query(DBUser).filter(DBUser.username == update_data['username']).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The username is already taken."
            )
    
    # Update user fields
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Response:
    """Delete a user (admin only)"""
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.put("/users/{user_id}/toggle-active", response_model=User)
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Toggle user active status (admin only)"""
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deactivating yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return user

# Analytics Endpoints
@router.get("/analytics/overview")
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Get analytics overview (admin only)"""
    # Total counts
    total_users = db.query(func.count(DBUser.id)).scalar()
    total_measurements = db.query(func.count(Measurement.id)).scalar()
    total_parties = db.query(func.count(Party.id)).scalar()
    total_production_papers = db.query(func.count(ProductionPaper.id)).scalar()
    
    # Active users
    active_users = db.query(func.count(DBUser.id)).filter(DBUser.is_active == True).scalar()
    
    # Users by role
    users_by_role = db.query(
        DBUser.role,
        func.count(DBUser.id).label('count')
    ).group_by(DBUser.role).all()
    role_distribution = {role: count for role, count in users_by_role}
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_users = db.query(func.count(DBUser.id)).filter(
        DBUser.created_at >= thirty_days_ago
    ).scalar()
    recent_measurements = db.query(func.count(Measurement.id)).filter(
        Measurement.created_at >= thirty_days_ago
    ).scalar()
    recent_parties = db.query(func.count(Party.id)).filter(
        Party.created_at >= thirty_days_ago
    ).scalar()
    recent_production_papers = db.query(func.count(ProductionPaper.id)).filter(
        ProductionPaper.created_at >= thirty_days_ago
    ).scalar()
    
    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "total_measurements": total_measurements or 0,
        "total_parties": total_parties or 0,
        "total_production_papers": total_production_papers or 0,
        "role_distribution": role_distribution,
        "recent_activity": {
            "users": recent_users or 0,
            "measurements": recent_measurements or 0,
            "parties": recent_parties or 0,
            "production_papers": recent_production_papers or 0,
        }
    }

@router.get("/analytics/users")
def get_user_analytics(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin),
    days: int = 30
) -> Any:
    """Get user analytics over time (admin only)"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Users created over time
    users_by_date = db.query(
        func.date(DBUser.created_at).label('date'),
        func.count(DBUser.id).label('count')
    ).filter(
        DBUser.created_at >= cutoff_date
    ).group_by(func.date(DBUser.created_at)).order_by('date').all()
    
    return {
        "users_by_date": [
            {"date": str(date), "count": count}
            for date, count in users_by_date
        ]
    }

@router.get("/analytics/activity")
def get_activity_analytics(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin),
    days: int = 30
) -> Any:
    """Get activity analytics (admin only)"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Measurements by date
    measurements_by_date = db.query(
        func.date(Measurement.created_at).label('date'),
        func.count(Measurement.id).label('count')
    ).filter(
        Measurement.created_at >= cutoff_date
    ).group_by(func.date(Measurement.created_at)).order_by('date').all()
    
    # Parties by date
    parties_by_date = db.query(
        func.date(Party.created_at).label('date'),
        func.count(Party.id).label('count')
    ).filter(
        Party.created_at >= cutoff_date
    ).group_by(func.date(Party.created_at)).order_by('date').all()
    
    # Production papers by date
    papers_by_date = db.query(
        func.date(ProductionPaper.created_at).label('date'),
        func.count(ProductionPaper.id).label('count')
    ).filter(
        ProductionPaper.created_at >= cutoff_date
    ).group_by(func.date(ProductionPaper.created_at)).order_by('date').all()
    
    return {
        "measurements_by_date": [
            {"date": str(date), "count": count}
            for date, count in measurements_by_date
        ],
        "parties_by_date": [
            {"date": str(date), "count": count}
            for date, count in parties_by_date
        ],
        "production_papers_by_date": [
            {"date": str(date), "count": count}
            for date, count in papers_by_date
        ]
    }


# Department Management Endpoints
@router.get("/departments", response_model=List[Department])
def get_all_departments(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all departments (admin only)"""
    departments = db.query(DBDepartment).offset(skip).limit(limit).all()
    return departments


@router.post("/departments", response_model=Department, status_code=status.HTTP_201_CREATED)
def create_department(
    department_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Create a new department (admin only)"""
    # Check if name already exists
    existing = db.query(DBDepartment).filter(DBDepartment.name == department_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name already exists"
        )
    
    department = DBDepartment(**department_in.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    
    return department


@router.put("/departments/{department_id}", response_model=Department)
def update_department(
    department_id: int,
    department_update: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Update a department (admin only)"""
    department = db.query(DBDepartment).filter(DBDepartment.id == department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Check if name is being updated and if it's already taken
    if department_update.name != department.name:
        existing = db.query(DBDepartment).filter(DBDepartment.name == department_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department with this name already exists"
            )
    
    update_data = department_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)
    
    db.commit()
    db.refresh(department)
    
    return department


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Response:
    """Delete a department (admin only)"""
    department = db.query(DBDepartment).filter(DBDepartment.id == department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Check if department has active supervisors
    active_supervisors = db.query(DBProductionSupervisor).filter(
        and_(
            DBProductionSupervisor.department_id == department_id,
            DBProductionSupervisor.is_active == True
        )
    ).count()
    
    if active_supervisors > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete department with active supervisors"
        )
    
    db.delete(department)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Production Supervisor Management Endpoints
@router.get("/supervisors", response_model=List[ProductionSupervisor])
def get_all_supervisors(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all supervisors (admin only)"""
    supervisors = db.query(DBProductionSupervisor).offset(skip).limit(limit).all()
    return supervisors


@router.post("/supervisors", response_model=ProductionSupervisor, status_code=status.HTTP_201_CREATED)
def create_supervisor(
    supervisor_in: ProductionSupervisorCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Create a new supervisor (admin only)"""
    # Check if user exists
    user = db.query(DBUser).filter(DBUser.id == supervisor_in.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user already has supervisor profile
    existing = db.query(DBProductionSupervisor).filter(
        DBProductionSupervisor.user_id == supervisor_in.user_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a supervisor profile"
        )
    
    # Check if department exists
    department = db.query(DBDepartment).filter(DBDepartment.id == supervisor_in.department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Update user role to production_supervisor if not already
    if user.role != "production_supervisor" and user.role != "admin":
        user.role = "production_supervisor"
    
    supervisor = DBProductionSupervisor(**supervisor_in.model_dump())
    db.add(supervisor)
    db.commit()
    db.refresh(supervisor)
    
    return supervisor


@router.put("/supervisors/{supervisor_id}", response_model=ProductionSupervisor)
def update_supervisor(
    supervisor_id: int,
    supervisor_update: ProductionSupervisorUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Update a supervisor (admin only)"""
    supervisor = db.query(DBProductionSupervisor).filter(
        DBProductionSupervisor.id == supervisor_id
    ).first()
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor not found"
        )
    
    update_data = supervisor_update.model_dump(exclude_unset=True)
    
    # Check if department is being updated
    if "department_id" in update_data:
        department = db.query(DBDepartment).filter(
            DBDepartment.id == update_data["department_id"]
        ).first()
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
    
    for field, value in update_data.items():
        setattr(supervisor, field, value)
    
    db.commit()
    db.refresh(supervisor)
    
    return supervisor


@router.delete("/supervisors/{supervisor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supervisor(
    supervisor_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Response:
    """Delete a supervisor (admin only)"""
    supervisor = db.query(DBProductionSupervisor).filter(
        DBProductionSupervisor.id == supervisor_id
    ).first()
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor not found"
        )
    
    db.delete(supervisor)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/supervisors/{supervisor_id}/toggle-active", response_model=ProductionSupervisor)
def toggle_supervisor_active(
    supervisor_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_admin)
) -> Any:
    """Toggle supervisor active status (admin only)"""
    supervisor = db.query(DBProductionSupervisor).filter(
        DBProductionSupervisor.id == supervisor_id
    ).first()
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supervisor not found"
        )
    
    supervisor.is_active = not supervisor.is_active
    db.commit()
    db.refresh(supervisor)
    
    return supervisor

