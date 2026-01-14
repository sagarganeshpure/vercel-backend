from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


# Carpenter Captain Schemas
class CarpenterCaptainBase(BaseModel):
    user_id: int
    site_id: int
    wing: Optional[str] = None
    assigned_date: date
    status: str = "Active"


class CarpenterCaptainCreate(CarpenterCaptainBase):
    pass


class CarpenterCaptain(CarpenterCaptainBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Work Allocation Schemas
class WorkAllocationBase(BaseModel):
    site_id: int
    allocation_date: date
    flat_numbers: List[str]  # List of flat numbers
    work_type: str  # Frame Fixing, Door Fixing, Both
    assigned_carpenters: Optional[List[str]] = None
    target_quantity: Optional[int] = None
    status: str = "Pending"
    remarks: Optional[str] = None


class WorkAllocationCreate(WorkAllocationBase):
    pass


class WorkAllocation(WorkAllocationBase):
    id: int
    captain_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Frame Fixing Schemas
class FrameFixingBase(BaseModel):
    flat_id: int
    site_id: int
    frame_type: str  # Bedroom, Bathroom, Kitchen, Main Door
    fixing_status: str = "Pending"  # Pending, Completed, On Hold
    fixing_date: Optional[date] = None
    carpenter_name: Optional[str] = None
    issue: Optional[str] = None
    photo_url: Optional[str] = None


class FrameFixingCreate(FrameFixingBase):
    pass


class FrameFixing(FrameFixingBase):
    id: int
    captain_id: int
    supervisor_approved: bool = False
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Door Fixing Schemas
class DoorFixingBase(BaseModel):
    flat_id: int
    site_id: int
    door_type: str  # Main Door, Bedroom Door, Bathroom Door, Kitchen Door
    fixing_status: str = "Pending"  # Pending, Completed, On Hold
    fixing_date: Optional[date] = None
    carpenter_name: Optional[str] = None
    reason: Optional[str] = None
    customer_instruction: Optional[str] = None
    photo_url: Optional[str] = None


class DoorFixingCreate(DoorFixingBase):
    pass


class DoorFixing(DoorFixingBase):
    id: int
    captain_id: int
    supervisor_approved: bool = False
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Carpenter Attendance Schemas
class CarpenterAttendanceBase(BaseModel):
    site_id: int
    attendance_date: date
    carpenter_name: str
    present: bool = True
    work_hours: Optional[float] = None
    remarks: Optional[str] = None


class CarpenterAttendanceCreate(CarpenterAttendanceBase):
    pass


class CarpenterAttendance(CarpenterAttendanceBase):
    id: int
    captain_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Carpenter Issue Schemas
class CarpenterIssueBase(BaseModel):
    site_id: int
    flat_id: Optional[int] = None
    issue_type: str  # Window not fixed, Civil work pending, Material missing, Access blocked, Builder instruction change
    description: str
    status: str = "Open"  # Open, Resolved, Closed
    reported_date: date
    resolved_date: Optional[date] = None
    photo_url: Optional[str] = None


class CarpenterIssueCreate(CarpenterIssueBase):
    pass


class CarpenterIssue(CarpenterIssueBase):
    id: int
    captain_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Work Completion Schemas
class WorkCompletionBase(BaseModel):
    site_id: int
    summary_date: date
    carpenter_name: str
    doors_fixed: int = 0
    frames_fixed: int = 0


class WorkCompletionCreate(WorkCompletionBase):
    pass


class WorkCompletion(WorkCompletionBase):
    id: int
    captain_id: int
    supervisor_approved: bool = False
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    submitted_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Dashboard Stats Schema
class CarpenterDashboardStats(BaseModel):
    doors_fixed_today: int
    frames_fixed_today: int
    carpenters_present: int
    issues_open: int
    pending_flats: int
    today_work_list: List[dict] = []

