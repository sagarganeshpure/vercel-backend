from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal


# Vendor Schemas
class VendorBase(BaseModel):
    vendor_name: str
    display_name: Optional[str] = None
    vendor_type: str  # Plywood Vendor, Laminate/Veneer Vendor, Hardware Vendor, Chemical/Resin Vendor
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    country: Optional[str] = "India"
    gstin: Optional[str] = None
    pan_number: Optional[str] = None
    state_code: Optional[str] = None
    material_categories: Optional[List[str]] = None
    rate_contracts: Optional[List[Dict[str, Any]]] = None
    payment_terms: Optional[str] = None
    credit_days: Optional[int] = None
    credit_limit: Optional[Decimal] = None
    is_active: bool = True
    status: str = "Active"


class VendorCreate(VendorBase):
    pass


class Vendor(VendorBase):
    id: int
    vendor_code: str
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# BOM Schemas
class BOMBase(BaseModel):
    production_paper_id: int
    production_paper_number: str
    material_category: str
    material_name: str
    specification: Optional[str] = None
    quantity_required: float
    unit: str = "pcs"


class BOMCreate(BOMBase):
    pass


class BOM(BOMBase):
    id: int
    pr_created: bool
    pr_id: Optional[int] = None
    po_created: bool
    po_id: Optional[int] = None
    material_received: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Purchase Requisition Schemas
class PurchaseRequisitionBase(BaseModel):
    pr_number: Optional[str] = None
    source_type: str  # Production Paper, Minimum Stock Level, Manual
    production_paper_id: Optional[int] = None
    production_paper_number: Optional[str] = None
    material_category: str
    material_name: str
    specification: Optional[str] = None
    quantity_required: float
    unit: str = "pcs"
    required_date: date
    urgency: str = "Normal"  # Normal, Urgent


class PurchaseRequisitionCreate(PurchaseRequisitionBase):
    pass


class PurchaseRequisition(PurchaseRequisitionBase):
    id: int
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    po_created: bool
    po_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Purchase Order Line Item
class POLineItem(BaseModel):
    material_name: str
    specification: Optional[str] = None
    quantity: float
    rate: Decimal
    tax_percent: Decimal = Decimal("0")
    amount: Decimal


# Purchase Order Schemas
class PurchaseOrderBase(BaseModel):
    po_number: Optional[str] = None
    vendor_id: int
    vendor_name: Optional[str] = None
    pr_id: Optional[int] = None
    pr_number: Optional[str] = None
    production_paper_id: Optional[int] = None
    production_paper_number: Optional[str] = None
    po_date: date
    delivery_date: date
    payment_terms: Optional[str] = None
    line_items: List[POLineItem]
    remarks: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    pass


class PurchaseOrder(PurchaseOrderBase):
    id: int
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    sent_to_vendor_at: Optional[datetime] = None
    total_quantity: float
    received_quantity: float
    pending_quantity: float
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# GRN QC Parameters
class GRNQCParameters(BaseModel):
    size: Optional[str] = None
    thickness: Optional[str] = None
    shade: Optional[str] = None
    damage: Optional[str] = None


# GRN Schemas
class GRNBase(BaseModel):
    grn_number: Optional[str] = None
    po_id: int
    po_number: str
    vendor_id: int
    vendor_name: Optional[str] = None
    material_category: str
    material_name: str
    specification: Optional[str] = None
    ordered_quantity: float
    received_quantity: float
    rejected_quantity: float = 0
    shortage_quantity: float = 0
    accepted_quantity: float
    qc_status: str = "Pending"
    qc_parameters: Optional[GRNQCParameters] = None
    qc_remarks: Optional[str] = None


class GRNCreate(GRNBase):
    pass


class GRN(GRNBase):
    id: int
    status: str
    qc_checked_by: Optional[int] = None
    qc_checked_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    purchase_return_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Purchase Return Schemas
class PurchaseReturnBase(BaseModel):
    return_number: Optional[str] = None
    po_id: int
    po_number: str
    grn_id: Optional[int] = None
    grn_number: Optional[str] = None
    vendor_id: int
    vendor_name: Optional[str] = None
    material_category: str
    material_name: str
    specification: Optional[str] = None
    return_quantity: float
    unit: str
    return_reason: str  # Damaged, Wrong Specification, Excess Received
    return_description: Optional[str] = None


class PurchaseReturnCreate(PurchaseReturnBase):
    pass


class PurchaseReturn(PurchaseReturnBase):
    id: int
    status: str
    vendor_notified: bool
    vendor_notified_at: Optional[datetime] = None
    stock_updated: bool
    stock_updated_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Vendor Bill GST Breakup
class GSTBreakup(BaseModel):
    cgst: Optional[Decimal] = Decimal("0")
    sgst: Optional[Decimal] = Decimal("0")
    igst: Optional[Decimal] = Decimal("0")
    cess: Optional[Decimal] = Decimal("0")


# Vendor Bill Schemas
class VendorBillBase(BaseModel):
    bill_number: Optional[str] = None
    grn_id: int
    grn_number: str
    po_id: Optional[int] = None
    po_number: Optional[str] = None
    vendor_id: int
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    vendor_bill_no: str
    vendor_bill_date: date
    bill_amount: Decimal
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal
    gst_breakup: Optional[GSTBreakup] = None


class VendorBillCreate(VendorBillBase):
    pass


class VendorBill(VendorBillBase):
    id: int
    payment_status: str
    payment_approved_by: Optional[int] = None
    payment_approved_at: Optional[datetime] = None
    payment_details: Optional[List[Dict[str, Any]]] = None
    tally_synced: bool
    tally_sync_date: Optional[datetime] = None
    tally_voucher_no: Optional[str] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Dashboard KPI Response
class PurchaseDashboardKPIs(BaseModel):
    pr_pending_approval: int
    open_purchase_orders: int
    material_in_transit: int
    shortage_rejection: int
    payables_due: int
    payables_amount: Decimal

