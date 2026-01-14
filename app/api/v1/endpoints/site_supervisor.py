from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from typing import Any, List, Optional
from datetime import datetime, date, timedelta
import json

from app.schemas.site_supervisor import (
    Site, SiteCreate, SiteUpdate,
    Flat, FlatCreate, FlatUpdate,
    SiteMeasurement, SiteMeasurementCreate, SiteMeasurementUpdate,
    FrameFixing, FrameFixingCreate, FrameFixingUpdate,
    DoorFixing, DoorFixingCreate, DoorFixingUpdate,
    DailySiteProgress, DailySiteProgressCreate, DailySiteProgressUpdate,
    SiteIssue, SiteIssueCreate, SiteIssueUpdate,
    SitePhoto, SitePhotoCreate, SitePhotoUpdate,
    SiteDashboardStats
)
from app.db.models.site_supervisor import (
    Site as DBSite, Flat as DBFlat, SiteMeasurement as DBSiteMeasurement,
    FrameFixing as DBFrameFixing, DoorFixing as DBDoorFixing,
    DailySiteProgress as DBDailySiteProgress, SiteIssue as DBSiteIssue,
    SitePhoto as DBSitePhoto
)
from app.db.models.sales import SiteProject
from app.api.deps import get_db, get_site_supervisor
from app.db.models.user import User as DBUser

router = APIRouter()


# ==================== DASHBOARD ====================

@router.get("/dashboard/stats", response_model=SiteDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Get dashboard statistics for site supervisor"""
    # Active sites
    active_sites = db.query(DBSite).filter(
        DBSite.site_status == "Active"
    ).count()
    
    # Doors pending fixing
    doors_pending = db.query(DBFlat).filter(
        and_(
            or_(
                DBFlat.main_door_required == True,
                DBFlat.bedroom_door_required == True,
                DBFlat.bathroom_door_required == True,
                DBFlat.kitchen_door_required == True
            ),
            DBFlat.door_fixed == False
        )
    ).count()
    
    # Frames pending fixing
    frames_pending = db.query(DBFlat).filter(
        DBFlat.frame_fixed == False
    ).count()
    
    # Open site issues
    site_issues_open = db.query(DBSiteIssue).filter(
        DBSiteIssue.status == "Open"
    ).count()
    
    # Pending photo updates (flats with fixing done but no photos)
    pending_photos = db.query(DBFlat).filter(
        and_(
            or_(
                DBFlat.frame_fixed == True,
                DBFlat.door_fixed == True
            ),
            ~DBFlat.photos.any()
        )
    ).count()
    
    return SiteDashboardStats(
        active_sites=active_sites,
        doors_pending_fixing=doors_pending,
        frames_pending_fixing=frames_pending,
        site_issues_open=site_issues_open,
        pending_photo_updates=pending_photos
    )


# ==================== SITES ====================

@router.get("/sites", response_model=List[Site])
def get_sites(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None
) -> Any:
    """Get all sites (read-only from sales module)"""
    query = db.query(DBSite)
    
    if status_filter:
        query = query.filter(DBSite.site_status == status_filter)
    
    sites = query.offset(skip).limit(limit).all()
    return sites


@router.get("/sites/{site_id}", response_model=Site)
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Get site details"""
    site = db.query(DBSite).filter(DBSite.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    return site


# ==================== FLATS ====================

@router.get("/sites/{site_id}/flats", response_model=List[Flat])
def get_flats(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    skip: int = 0,
    limit: int = 1000,
    wing: Optional[str] = None,
    floor: Optional[int] = None
) -> Any:
    """Get all flats for a site"""
    query = db.query(DBFlat).filter(DBFlat.site_id == site_id)
    
    if wing:
        query = query.filter(DBFlat.wing == wing)
    if floor:
        query = query.filter(DBFlat.floor == floor)
    
    flats = query.order_by(DBFlat.wing, DBFlat.floor, DBFlat.flat_number).offset(skip).limit(limit).all()
    return flats


@router.post("/sites/{site_id}/flats", response_model=Flat, status_code=status.HTTP_201_CREATED)
def create_flat(
    site_id: int,
    flat_in: FlatCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Create a new flat"""
    # Verify site exists
    site = db.query(DBSite).filter(DBSite.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Check if flat already exists
    existing = db.query(DBFlat).filter(
        and_(
            DBFlat.site_id == site_id,
            DBFlat.flat_number == flat_in.flat_number,
            DBFlat.wing == flat_in.wing
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flat already exists"
        )
    
    flat = DBFlat(**flat_in.model_dump(), site_id=site_id, created_by=current_user.id)
    db.add(flat)
    db.commit()
    db.refresh(flat)
    return flat


@router.put("/flats/{flat_id}", response_model=Flat)
def update_flat(
    flat_id: int,
    flat_update: FlatUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Update flat details"""
    flat = db.query(DBFlat).filter(DBFlat.id == flat_id).first()
    if not flat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flat not found"
        )
    
    update_data = flat_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flat, field, value)
    
    db.commit()
    db.refresh(flat)
    return flat


@router.get("/flats/{flat_id}", response_model=Flat)
def get_flat(
    flat_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Get flat details"""
    flat = db.query(DBFlat).filter(DBFlat.id == flat_id).first()
    if not flat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flat not found"
        )
    return flat


# ==================== MEASUREMENTS ====================

@router.post("/measurements", response_model=SiteMeasurement, status_code=status.HTTP_201_CREATED)
def create_measurement(
    measurement_in: SiteMeasurementCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Create a new measurement entry"""
    # Verify flat exists
    flat = db.query(DBFlat).filter(DBFlat.id == measurement_in.flat_id).first()
    if not flat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flat not found"
        )
    
    measurement = DBSiteMeasurement(
        **measurement_in.model_dump(),
        created_by=current_user.id
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return measurement


@router.get("/measurements", response_model=List[SiteMeasurement])
def get_measurements(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None,
    flat_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 1000
) -> Any:
    """Get all measurements"""
    query = db.query(DBSiteMeasurement)
    
    if site_id:
        query = query.filter(DBSiteMeasurement.site_id == site_id)
    if flat_id:
        query = query.filter(DBSiteMeasurement.flat_id == flat_id)
    
    measurements = query.order_by(DBSiteMeasurement.created_at.desc()).offset(skip).limit(limit).all()
    return measurements


@router.put("/measurements/{measurement_id}", response_model=SiteMeasurement)
def update_measurement(
    measurement_id: int,
    measurement_update: SiteMeasurementUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Update measurement"""
    measurement = db.query(DBSiteMeasurement).filter(DBSiteMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found"
        )
    
    update_data = measurement_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(measurement, field, value)
    
    db.commit()
    db.refresh(measurement)
    return measurement


# ==================== FRAME FIXING ====================

@router.post("/frame-fixings", response_model=FrameFixing, status_code=status.HTTP_201_CREATED)
def create_frame_fixing(
    fixing_in: FrameFixingCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Create frame fixing entry"""
    flat = db.query(DBFlat).filter(DBFlat.id == fixing_in.flat_id).first()
    if not flat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flat not found"
        )
    
    fixing = DBFrameFixing(
        **fixing_in.model_dump(),
        created_by=current_user.id
    )
    db.add(fixing)
    
    # Update flat frame_fixed status if completed
    if fixing_in.fixing_status == "Completed":
        flat.frame_fixed = True
    
    db.commit()
    db.refresh(fixing)
    return fixing


@router.get("/frame-fixings", response_model=List[FrameFixing])
def get_frame_fixings(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None,
    flat_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000
) -> Any:
    """Get all frame fixings"""
    query = db.query(DBFrameFixing)
    
    if site_id:
        query = query.filter(DBFrameFixing.site_id == site_id)
    if flat_id:
        query = query.filter(DBFrameFixing.flat_id == flat_id)
    if status_filter:
        query = query.filter(DBFrameFixing.fixing_status == status_filter)
    
    fixings = query.order_by(DBFrameFixing.created_at.desc()).offset(skip).limit(limit).all()
    return fixings


@router.put("/frame-fixings/{fixing_id}", response_model=FrameFixing)
def update_frame_fixing(
    fixing_id: int,
    fixing_update: FrameFixingUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Update frame fixing"""
    fixing = db.query(DBFrameFixing).filter(DBFrameFixing.id == fixing_id).first()
    if not fixing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frame fixing not found"
        )
    
    update_data = fixing_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fixing, field, value)
    
    # Update flat status if needed
    if "fixing_status" in update_data:
        flat = db.query(DBFlat).filter(DBFlat.id == fixing.flat_id).first()
        if flat:
            flat.frame_fixed = (update_data["fixing_status"] == "Completed")
    
    db.commit()
    db.refresh(fixing)
    return fixing


# ==================== DOOR FIXING ====================

@router.post("/door-fixings", response_model=DoorFixing, status_code=status.HTTP_201_CREATED)
def create_door_fixing(
    fixing_in: DoorFixingCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Create door fixing entry"""
    flat = db.query(DBFlat).filter(DBFlat.id == fixing_in.flat_id).first()
    if not flat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flat not found"
        )
    
    fixing = DBDoorFixing(
        **fixing_in.model_dump(),
        created_by=current_user.id
    )
    db.add(fixing)
    
    # Update flat door_fixed status if completed
    if fixing_in.fixing_status == "Completed":
        flat.door_fixed = True
    
    db.commit()
    db.refresh(fixing)
    return fixing


@router.get("/door-fixings", response_model=List[DoorFixing])
def get_door_fixings(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None,
    flat_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000
) -> Any:
    """Get all door fixings"""
    query = db.query(DBDoorFixing)
    
    if site_id:
        query = query.filter(DBDoorFixing.site_id == site_id)
    if flat_id:
        query = query.filter(DBDoorFixing.flat_id == flat_id)
    if status_filter:
        query = query.filter(DBDoorFixing.fixing_status == status_filter)
    
    fixings = query.order_by(DBDoorFixing.created_at.desc()).offset(skip).limit(limit).all()
    return fixings


@router.put("/door-fixings/{fixing_id}", response_model=DoorFixing)
def update_door_fixing(
    fixing_id: int,
    fixing_update: DoorFixingUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Update door fixing"""
    fixing = db.query(DBDoorFixing).filter(DBDoorFixing.id == fixing_id).first()
    if not fixing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Door fixing not found"
        )
    
    update_data = fixing_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fixing, field, value)
    
    # Update flat status if needed
    if "fixing_status" in update_data:
        flat = db.query(DBFlat).filter(DBFlat.id == fixing.flat_id).first()
        if flat:
            flat.door_fixed = (update_data["fixing_status"] == "Completed")
    
    db.commit()
    db.refresh(fixing)
    return fixing


# ==================== DAILY SITE PROGRESS ====================

@router.post("/daily-progress", response_model=DailySiteProgress, status_code=status.HTTP_201_CREATED)
def create_daily_progress(
    progress_in: DailySiteProgressCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Create daily site progress report"""
    site = db.query(DBSite).filter(DBSite.id == progress_in.site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Check if report already exists for this date
    existing = db.query(DBDailySiteProgress).filter(
        and_(
            DBDailySiteProgress.site_id == progress_in.site_id,
            DBDailySiteProgress.report_date == progress_in.report_date
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Daily progress report already exists for this date"
        )
    
    progress = DBDailySiteProgress(
        **progress_in.model_dump(),
        created_by=current_user.id
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


@router.get("/daily-progress", response_model=List[DailySiteProgress])
def get_daily_progress(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get daily progress reports"""
    query = db.query(DBDailySiteProgress)
    
    if site_id:
        query = query.filter(DBDailySiteProgress.site_id == site_id)
    if start_date:
        query = query.filter(DBDailySiteProgress.report_date >= start_date)
    if end_date:
        query = query.filter(DBDailySiteProgress.report_date <= end_date)
    
    reports = query.order_by(DBDailySiteProgress.report_date.desc()).offset(skip).limit(limit).all()
    return reports


@router.put("/daily-progress/{progress_id}", response_model=DailySiteProgress)
def update_daily_progress(
    progress_id: int,
    progress_update: DailySiteProgressUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Update daily progress report"""
    progress = db.query(DBDailySiteProgress).filter(DBDailySiteProgress.id == progress_id).first()
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily progress report not found"
        )
    
    update_data = progress_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(progress, field, value)
    
    db.commit()
    db.refresh(progress)
    return progress


# ==================== SITE ISSUES ====================

@router.post("/issues", response_model=SiteIssue, status_code=status.HTTP_201_CREATED)
def create_issue(
    issue_in: SiteIssueCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Create a site issue"""
    site = db.query(DBSite).filter(DBSite.id == issue_in.site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    issue = DBSiteIssue(
        **issue_in.model_dump(),
        created_by=current_user.id
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/issues", response_model=List[SiteIssue])
def get_issues(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None,
    flat_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000
) -> Any:
    """Get all site issues"""
    query = db.query(DBSiteIssue)
    
    if site_id:
        query = query.filter(DBSiteIssue.site_id == site_id)
    if flat_id:
        query = query.filter(DBSiteIssue.flat_id == flat_id)
    if status_filter:
        query = query.filter(DBSiteIssue.status == status_filter)
    
    issues = query.order_by(DBSiteIssue.created_at.desc()).offset(skip).limit(limit).all()
    return issues


@router.put("/issues/{issue_id}", response_model=SiteIssue)
def update_issue(
    issue_id: int,
    issue_update: SiteIssueUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Update site issue"""
    issue = db.query(DBSiteIssue).filter(DBSiteIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    update_data = issue_update.model_dump(exclude_unset=True)
    
    # If status is being changed to Closed/Resolved, set resolved_at and resolved_by
    if "status" in update_data:
        if update_data["status"] in ["Closed", "Resolved"] and issue.status not in ["Closed", "Resolved"]:
            issue.resolved_at = datetime.now()
            issue.resolved_by = current_user.id
    
    for field, value in update_data.items():
        if field != "status" or value not in ["Closed", "Resolved"]:
            setattr(issue, field, value)
    
    db.commit()
    db.refresh(issue)
    return issue


# ==================== SITE PHOTOS ====================

@router.post("/photos", response_model=SitePhoto, status_code=status.HTTP_201_CREATED)
def create_photo(
    photo_in: SitePhotoCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Create a site photo entry"""
    site = db.query(DBSite).filter(DBSite.id == photo_in.site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    photo = DBSitePhoto(
        **photo_in.model_dump(),
        created_by=current_user.id
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/photos", response_model=List[SitePhoto])
def get_photos(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None,
    flat_id: Optional[int] = None,
    photo_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000
) -> Any:
    """Get all site photos"""
    query = db.query(DBSitePhoto)
    
    if site_id:
        query = query.filter(DBSitePhoto.site_id == site_id)
    if flat_id:
        query = query.filter(DBSitePhoto.flat_id == flat_id)
    if photo_type:
        query = query.filter(DBSitePhoto.photo_type == photo_type)
    
    photos = query.order_by(DBSitePhoto.created_at.desc()).offset(skip).limit(limit).all()
    return photos


@router.put("/photos/{photo_id}", response_model=SitePhoto)
def update_photo(
    photo_id: int,
    photo_update: SitePhotoUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor)
) -> Any:
    """Update site photo"""
    photo = db.query(DBSitePhoto).filter(DBSitePhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    update_data = photo_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(photo, field, value)
    
    db.commit()
    db.refresh(photo)
    return photo


# ==================== REPORTS ====================

@router.get("/reports/flat-pending")
def get_flat_pending_report(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None
) -> Any:
    """Get flat-wise pending doors report"""
    query = db.query(DBFlat).filter(
        and_(
            or_(
                DBFlat.main_door_required == True,
                DBFlat.bedroom_door_required == True,
                DBFlat.bathroom_door_required == True,
                DBFlat.kitchen_door_required == True
            ),
            DBFlat.door_fixed == False
        )
    )
    
    if site_id:
        query = query.filter(DBFlat.site_id == site_id)
    
    flats = query.all()
    
    result = []
    for flat in flats:
        result.append({
            "flat_id": flat.id,
            "site_id": flat.site_id,
            "wing": flat.wing,
            "floor": flat.floor,
            "flat_number": flat.flat_number,
            "main_door": flat.main_door_required and not flat.door_fixed,
            "bedroom_door": flat.bedroom_door_required and not flat.door_fixed,
            "bathroom_door": flat.bathroom_door_required and not flat.door_fixed,
            "kitchen_door": flat.kitchen_door_required and not flat.door_fixed,
            "remarks": flat.remarks
        })
    
    return result


@router.get("/reports/fixing-gap")
def get_fixing_gap_report(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: Optional[int] = None
) -> Any:
    """Get frame vs door fixing gap report"""
    query = db.query(DBFlat)
    
    if site_id:
        query = query.filter(DBFlat.site_id == site_id)
    
    flats = query.all()
    
    frame_fixed_doors_pending = 0
    doors_fixed_frames_pending = 0
    both_pending = 0
    both_fixed = 0
    
    for flat in flats:
        if flat.frame_fixed and not flat.door_fixed:
            frame_fixed_doors_pending += 1
        elif flat.door_fixed and not flat.frame_fixed:
            doors_fixed_frames_pending += 1
        elif not flat.frame_fixed and not flat.door_fixed:
            both_pending += 1
        elif flat.frame_fixed and flat.door_fixed:
            both_fixed += 1
    
    return {
        "frame_fixed_doors_pending": frame_fixed_doors_pending,
        "doors_fixed_frames_pending": doors_fixed_frames_pending,
        "both_pending": both_pending,
        "both_fixed": both_fixed,
        "total_flats": len(flats)
    }


@router.get("/reports/wing-completion")
def get_wing_completion_report(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_site_supervisor),
    site_id: int = Query(..., description="Site ID")
) -> Any:
    """Get wing-wise completion percentage"""
    site = db.query(DBSite).filter(DBSite.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    wings = json.loads(site.wings) if site.wings else []
    result = []
    
    for wing in wings:
        flats = db.query(DBFlat).filter(
            and_(
                DBFlat.site_id == site_id,
                DBFlat.wing == wing
            )
        ).all()
        
        total = len(flats)
        frames_fixed = sum(1 for f in flats if f.frame_fixed)
        doors_fixed = sum(1 for f in flats if f.door_fixed)
        
        result.append({
            "wing": wing,
            "total_flats": total,
            "frames_fixed": frames_fixed,
            "doors_fixed": doors_fixed,
            "frame_completion_percent": round((frames_fixed / total * 100) if total > 0 else 0, 2),
            "door_completion_percent": round((doors_fixed / total * 100) if total > 0 else 0, 2)
        })
    
    return result

