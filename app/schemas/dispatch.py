from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


# Dispatch Item Schemas
class DispatchItemBase(BaseModel):
    product_type: str  # Door, Frame
    product_description: str
    quantity: int
    packaging_type: Optional[str] = None
    weight: Optional[float] = None
    volume: Optional[float] = None
    remarks: Optional[str] = None


class DispatchItemCreate(DispatchItemBase):
    pass


class DispatchItem(DispatchItemBase):
    id: int
    dispatch_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Dispatch Schemas
class DispatchBase(BaseModel):
    dispatch_request_no: Optional[str] = None
    production_paper_id: int
    production_paper_number: str
    billing_request_id: Optional[int] = None
    delivery_challan_id: Optional[int] = None
    tax_invoice_id: Optional[int] = None
    party_id: int
    party_name: str
    delivery_address: str
    dispatch_date: date
    expected_delivery_date: Optional[date] = None
    vehicle_type: str  # Company, Transporter
    vehicle_no: str
    driver_name: Optional[str] = None
    driver_mobile: Optional[str] = None
    items: List[DispatchItemBase]
    remarks: Optional[str] = None


class DispatchCreate(DispatchBase):
    pass


class DispatchUpdate(BaseModel):
    vehicle_type: Optional[str] = None
    vehicle_no: Optional[str] = None
    driver_name: Optional[str] = None
    driver_mobile: Optional[str] = None
    dispatch_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    remarks: Optional[str] = None
    status: Optional[str] = None


class Dispatch(DispatchBase):
    id: int
    dispatch_number: str
    dc_number: Optional[str] = None
    invoice_number: Optional[str] = None
    status: str
    qc_approved: bool
    billing_approved: bool
    created_by: int
    approved_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    dispatch_items: List[DispatchItem] = []

    class Config:
        from_attributes = True


# Gate Pass Schemas
class GatePassBase(BaseModel):
    dispatch_id: int
    vehicle_no: str
    driver_name: Optional[str] = None
    driver_mobile: Optional[str] = None


class GatePassCreate(GatePassBase):
    pass


class GatePass(GatePassBase):
    id: int
    gate_pass_number: str
    dispatch_number: str
    item_summary: str  # JSON string
    verified: bool
    verified_by: Optional[int] = None
    time_out: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GatePassVerify(BaseModel):
    verified: bool = True
    time_out: Optional[datetime] = None


# Delivery Tracking Schemas
class DeliveryTrackingBase(BaseModel):
    dispatch_id: int
    status: str = "dispatched"  # dispatched, in_transit, delivered, delayed
    delivered_date: Optional[datetime] = None
    receiver_name: Optional[str] = None
    receiver_mobile: Optional[str] = None
    pod_photo_url: Optional[str] = None
    pod_signature_url: Optional[str] = None
    shortage_remarks: Optional[str] = None
    damage_remarks: Optional[str] = None
    delay_reason: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None


class DeliveryTrackingCreate(DeliveryTrackingBase):
    pass


class DeliveryTrackingUpdate(BaseModel):
    status: Optional[str] = None
    delivered_date: Optional[datetime] = None
    receiver_name: Optional[str] = None
    receiver_mobile: Optional[str] = None
    pod_photo_url: Optional[str] = None
    pod_signature_url: Optional[str] = None
    shortage_remarks: Optional[str] = None
    damage_remarks: Optional[str] = None
    delay_reason: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None


class DeliveryTracking(DeliveryTrackingBase):
    id: int
    dispatch_number: str
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Ready for Dispatch Response
class ReadyForDispatch(BaseModel):
    production_paper_id: int
    production_paper_number: str
    party_id: int
    party_name: str
    delivery_address: str
    qc_approved: bool
    billing_request_id: Optional[int] = None
    dc_number: Optional[str] = None
    invoice_number: Optional[str] = None
    billing_approved: bool
    items: List[Dict[str, Any]]  # Product items from production paper

    class Config:
        from_attributes = True

