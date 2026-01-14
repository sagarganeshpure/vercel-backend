from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


# Billing Request Schemas
class BillingRequestItem(BaseModel):
    product_name: str
    door_frame_type: str
    quantity: int
    uom: str = "Nos"


class BillingRequestBase(BaseModel):
    dispatch_request_no: str
    production_paper_id: int
    production_paper_number: str
    party_id: int
    party_name: str
    party_gstin: Optional[str] = None
    site_name: Optional[str] = None
    delivery_address: str
    vehicle_no: Optional[str] = None
    driver_name: Optional[str] = None
    dispatch_date: Optional[date] = None
    items: List[BillingRequestItem]


class BillingRequestCreate(BillingRequestBase):
    pass


class BillingRequest(BillingRequestBase):
    id: int
    status: str
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Delivery Challan Schemas
class DCLineItem(BaseModel):
    product_name: str
    door_frame_type: str
    quantity: int
    uom: str = "Nos"
    remarks: Optional[str] = None


class DeliveryChallanBase(BaseModel):
    billing_request_id: int
    dispatch_request_no: str
    party_id: int
    party_name: str
    delivery_address: str
    vehicle_no: Optional[str] = None
    driver_name: Optional[str] = None
    dc_date: date
    line_items: List[DCLineItem]
    remarks: Optional[str] = None


class DeliveryChallanCreate(DeliveryChallanBase):
    pass


class DeliveryChallanUpdate(BaseModel):
    vehicle_no: Optional[str] = None
    driver_name: Optional[str] = None
    dc_date: Optional[date] = None
    remarks: Optional[str] = None
    status: Optional[str] = None


class DeliveryChallan(DeliveryChallanBase):
    id: int
    dc_number: str
    status: str
    created_by: int
    approved_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Tax Invoice Schemas
class InvoiceLineItem(BaseModel):
    product_description: str
    hsn_code: str
    quantity: int
    rate: Decimal
    discount: Optional[Decimal] = Decimal("0.00")
    taxable_value: Decimal
    cgst_rate: Optional[Decimal] = Decimal("0.00")
    sgst_rate: Optional[Decimal] = Decimal("0.00")
    igst_rate: Optional[Decimal] = Decimal("0.00")
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal


class TaxInvoiceBase(BaseModel):
    billing_request_id: int
    delivery_challan_id: Optional[int] = None
    dispatch_request_no: str
    party_id: int
    party_name: str
    party_gstin: Optional[str] = None
    place_of_supply: str
    state_code: Optional[str] = None
    invoice_date: date
    payment_terms: Optional[str] = None
    dc_reference: Optional[str] = None
    line_items: List[InvoiceLineItem]
    freight: Optional[Decimal] = Decimal("0.00")
    round_off: Optional[Decimal] = Decimal("0.00")
    remarks: Optional[str] = None


class TaxInvoiceCreate(TaxInvoiceBase):
    pass


class TaxInvoiceUpdate(BaseModel):
    payment_terms: Optional[str] = None
    freight: Optional[Decimal] = None
    round_off: Optional[Decimal] = None
    remarks: Optional[str] = None
    status: Optional[str] = None


class TaxInvoice(TaxInvoiceBase):
    id: int
    invoice_number: str
    subtotal: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    grand_total: Decimal
    status: str
    credit_limit_check: bool
    credit_limit_exceeded: bool
    outstanding_amount: Optional[Decimal] = None
    created_by: int
    approved_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Tally Sync Schemas
class TallySyncBase(BaseModel):
    tax_invoice_id: int
    sync_type: str  # export_invoice, import_payment, import_ledger
    sync_method: str  # xml_export, excel_import
    export_data: Optional[Dict[str, Any]] = None


class TallySyncCreate(TallySyncBase):
    pass


class TallySync(TallySyncBase):
    id: int
    sync_status: str
    import_data: Optional[Dict[str, Any]] = None
    tally_response: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    last_retry_at: Optional[datetime] = None
    synced_by: Optional[int] = None
    synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

