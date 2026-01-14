from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


# Vehicle Schemas
class VehicleBase(BaseModel):
    vehicle_no: str
    vehicle_type: str  # Truck, Tempo, Container
    capacity_tonnes: Optional[float] = None
    capacity_cubic_meters: Optional[float] = None
    is_available: bool = True
    current_location: Optional[str] = None
    gps_enabled: bool = False
    insurance_expiry: Optional[date] = None
    registration_expiry: Optional[date] = None
    remarks: Optional[str] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vehicle_type: Optional[str] = None
    capacity_tonnes: Optional[float] = None
    capacity_cubic_meters: Optional[float] = None
    is_available: Optional[bool] = None
    current_location: Optional[str] = None
    gps_enabled: Optional[bool] = None
    insurance_expiry: Optional[date] = None
    registration_expiry: Optional[date] = None
    remarks: Optional[str] = None


class Vehicle(VehicleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Driver Schemas
class DriverBase(BaseModel):
    name: str
    mobile: str
    license_number: str
    license_expiry: Optional[date] = None
    address: Optional[str] = None
    is_active: bool = True
    remarks: Optional[str] = None


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    license_number: Optional[str] = None
    license_expiry: Optional[date] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None
    remarks: Optional[str] = None


class Driver(DriverBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Logistics Assignment Schemas
class LogisticsAssignmentBase(BaseModel):
    dispatch_id: int
    vehicle_id: int
    driver_id: int
    planned_delivery_date: date
    route_area: Optional[str] = None
    assignment_notes: Optional[str] = None


class LogisticsAssignmentCreate(LogisticsAssignmentBase):
    pass


class LogisticsAssignmentUpdate(BaseModel):
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None
    planned_delivery_date: Optional[date] = None
    route_area: Optional[str] = None
    assignment_notes: Optional[str] = None
    status: Optional[str] = None


class LogisticsAssignment(LogisticsAssignmentBase):
    id: int
    dispatch_number: str
    vehicle_no: str
    driver_name: str
    driver_mobile: str
    status: str
    assigned_by: int
    assigned_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Delivery Issue Schemas
class DeliveryIssueBase(BaseModel):
    dispatch_id: int
    issue_type: str  # delivery_delay, damage, shortage, wrong_address, vehicle_breakdown
    title: str
    description: str
    severity: str = "medium"  # low, medium, high, critical
    issue_photo_url: Optional[str] = None


class DeliveryIssueCreate(DeliveryIssueBase):
    pass


class DeliveryIssueUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
    reviewed_by: Optional[int] = None


class DeliveryIssue(DeliveryIssueBase):
    id: int
    dispatch_number: str
    status: str
    resolution_notes: Optional[str] = None
    reported_by: int
    reviewed_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

