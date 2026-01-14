from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


# Site Schemas
class SiteBase(BaseModel):
    site_project_id: int
    builder_name: str
    project_name: str
    location: Optional[str] = None
    address: Optional[str] = None
    wings: Optional[List[str]] = None
    total_floors: Optional[int] = None
    total_flats: Optional[int] = None
    site_status: str = "Active"


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    wings: Optional[List[str]] = None
    total_floors: Optional[int] = None
    total_flats: Optional[int] = None
    site_status: Optional[str] = None


class Site(SiteBase):
    id: int
    site_code: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Flat Schemas
class FlatBase(BaseModel):
    site_id: int
    flat_number: str
    wing: str
    floor: int
    main_door_required: bool = False
    bedroom_door_required: bool = False
    bathroom_door_required: bool = False
    kitchen_door_required: bool = False
    frame_fixed: bool = False
    door_fixed: bool = False
    remarks: Optional[str] = None


class FlatCreate(FlatBase):
    pass


class FlatUpdate(BaseModel):
    main_door_required: Optional[bool] = None
    bedroom_door_required: Optional[bool] = None
    bathroom_door_required: Optional[bool] = None
    kitchen_door_required: Optional[bool] = None
    frame_fixed: Optional[bool] = None
    door_fixed: Optional[bool] = None
    remarks: Optional[str] = None


class Flat(FlatBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Site Measurement Schemas
class SiteMeasurementBase(BaseModel):
    flat_id: int
    site_id: int
    location: str
    width_mm: float
    height_mm: float
    wall_thickness: Optional[float] = None
    handing: Optional[str] = None
    door_type: str
    frame_type: Optional[str] = None
    special_note: Optional[str] = None
    status: str = "Pending"


class SiteMeasurementCreate(SiteMeasurementBase):
    pass


class SiteMeasurementUpdate(BaseModel):
    location: Optional[str] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    wall_thickness: Optional[float] = None
    handing: Optional[str] = None
    door_type: Optional[str] = None
    frame_type: Optional[str] = None
    special_note: Optional[str] = None
    status: Optional[str] = None


class SiteMeasurement(SiteMeasurementBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Frame Fixing Schemas
class FrameFixingBase(BaseModel):
    flat_id: int
    site_id: int
    frame_type: str
    fixing_status: str
    fixing_date: Optional[date] = None
    contractor: Optional[str] = None
    floor_readiness: bool = False
    issue: Optional[str] = None


class FrameFixingCreate(FrameFixingBase):
    pass


class FrameFixingUpdate(BaseModel):
    frame_type: Optional[str] = None
    fixing_status: Optional[str] = None
    fixing_date: Optional[date] = None
    contractor: Optional[str] = None
    floor_readiness: Optional[bool] = None
    issue: Optional[str] = None


class FrameFixing(FrameFixingBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Door Fixing Schemas
class DoorFixingBase(BaseModel):
    flat_id: int
    site_id: int
    door_type: str
    fixing_status: str
    reason: Optional[str] = None
    expected_resume_date: Optional[date] = None
    customer_instruction: Optional[str] = None


class DoorFixingCreate(DoorFixingBase):
    pass


class DoorFixingUpdate(BaseModel):
    door_type: Optional[str] = None
    fixing_status: Optional[str] = None
    reason: Optional[str] = None
    expected_resume_date: Optional[date] = None
    customer_instruction: Optional[str] = None


class DoorFixing(DoorFixingBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Daily Site Progress Schemas
class DailySiteProgressBase(BaseModel):
    site_id: int
    report_date: date
    wing: Optional[str] = None
    floors_covered: Optional[str] = None
    frames_fixed_today: int = 0
    doors_fixed_today: int = 0
    work_front_available: bool = True
    constraints: Optional[str] = None
    tomorrow_plan: Optional[str] = None


class DailySiteProgressCreate(DailySiteProgressBase):
    pass


class DailySiteProgressUpdate(BaseModel):
    report_date: Optional[date] = None
    wing: Optional[str] = None
    floors_covered: Optional[str] = None
    frames_fixed_today: Optional[int] = None
    doors_fixed_today: Optional[int] = None
    work_front_available: Optional[bool] = None
    constraints: Optional[str] = None
    tomorrow_plan: Optional[str] = None


class DailySiteProgress(DailySiteProgressBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Site Issue Schemas
class SiteIssueBase(BaseModel):
    site_id: int
    flat_id: Optional[int] = None
    issue_type: str
    title: str
    description: str
    wing: Optional[str] = None
    floor: Optional[int] = None
    status: str = "Open"
    resolution_notes: Optional[str] = None


class SiteIssueCreate(SiteIssueBase):
    pass


class SiteIssueUpdate(BaseModel):
    issue_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    wing: Optional[str] = None
    floor: Optional[int] = None
    status: Optional[str] = None
    resolution_notes: Optional[str] = None


class SiteIssue(SiteIssueBase):
    id: int
    created_by: int
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Site Photo Schemas
class SitePhotoBase(BaseModel):
    site_id: int
    flat_id: Optional[int] = None
    photo_type: str
    photo_url: str
    caption: Optional[str] = None


class SitePhotoCreate(SitePhotoBase):
    pass


class SitePhotoUpdate(BaseModel):
    photo_type: Optional[str] = None
    photo_url: Optional[str] = None
    caption: Optional[str] = None


class SitePhoto(SitePhotoBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Dashboard Stats Schema
class SiteDashboardStats(BaseModel):
    active_sites: int
    doors_pending_fixing: int
    frames_pending_fixing: int
    site_issues_open: int
    pending_photo_updates: int

