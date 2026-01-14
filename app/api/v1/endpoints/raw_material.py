from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Any
from datetime import datetime
import json
import re

from app.schemas.user import (
    Supplier, SupplierCreate,
    RawMaterialCheck, RawMaterialCheckCreate,
    Order, OrderCreate,
    ProductSupplierMapping, ProductSupplierMappingCreate,
    RawMaterialCategory, RawMaterialCategoryCreate, RawMaterialCategoryUpdate
)
from app.db.models.raw_material import (
    Supplier as DBSupplier,
    RawMaterialCheck as DBRawMaterialCheck,
    Order as DBOrder,
    ProductSupplierMapping as DBProductSupplierMapping,
    RawMaterialCategory as DBRawMaterialCategory
)
from app.api.deps import get_db, get_raw_material_checker

router = APIRouter()


def generate_next_check_number(db: Session) -> str:
    """Generate the next raw material check number in format RMC001, RMC002, etc."""
    checks = db.query(DBRawMaterialCheck.check_number).filter(
        DBRawMaterialCheck.check_number.like('RMC%')
    ).all()
    
    max_num = 0
    for check in checks:
        match = re.match(r'RMC(\d+)', check.check_number)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    next_num = max_num + 1
    return f"RMC{next_num:03d}"


def generate_next_order_number(db: Session) -> str:
    """Generate the next order number in format ORD001, ORD002, etc."""
    orders = db.query(DBOrder.order_number).filter(
        DBOrder.order_number.like('ORD%')
    ).all()
    
    max_num = 0
    for order in orders:
        match = re.match(r'ORD(\d+)', order.order_number)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    next_num = max_num + 1
    return f"ORD{next_num:03d}"


def generate_next_supplier_code(db: Session) -> str:
    """Generate the next supplier code in format SUP001, SUP002, etc."""
    suppliers = db.query(DBSupplier.code).filter(
        DBSupplier.code.like('SUP%')
    ).all()
    
    max_num = 0
    for supplier in suppliers:
        if supplier.code:
            match = re.match(r'SUP(\d+)', supplier.code)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    
    next_num = max_num + 1
    return f"SUP{next_num:03d}"


# Supplier endpoints
@router.post("/suppliers", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_in: SupplierCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Create a new supplier"""
    existing_supplier = db.query(DBSupplier).filter(DBSupplier.name == supplier_in.name).first()
    if existing_supplier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier with this name already exists"
        )
    
    supplier_data = supplier_in.model_dump()
    
    # Auto-generate supplier code if not provided
    if not supplier_data.get('code'):
        supplier_data['code'] = generate_next_supplier_code(db)
    
    db_supplier = DBSupplier(**supplier_data)
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.get("/suppliers", response_model=List[Supplier])
def get_suppliers(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all suppliers"""
    suppliers = db.query(DBSupplier).offset(skip).limit(limit).all()
    return suppliers


@router.get("/suppliers/{supplier_id}", response_model=Supplier)
def get_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Get a specific supplier"""
    supplier = db.query(DBSupplier).filter(DBSupplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/suppliers/{supplier_id}", response_model=Supplier)
def update_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
    supplier_in: SupplierCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Update a supplier"""
    db_supplier = db.query(DBSupplier).filter(DBSupplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    for field, value in supplier_in.model_dump().items():
        setattr(db_supplier, field, value)
    
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
    current_user = Depends(get_raw_material_checker)
):
    """Delete a supplier"""
    db_supplier = db.query(DBSupplier).filter(DBSupplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    db.delete(db_supplier)
    db.commit()
    # No return statement for 204 status code


# Raw Material Category endpoints
def generate_next_category_code(db: Session) -> str:
    """Generate the next category code in format CAT001, CAT002, etc."""
    categories = db.query(DBRawMaterialCategory.code).filter(
        DBRawMaterialCategory.code.like('CAT%')
    ).all()
    
    max_num = 0
    for category in categories:
        if category.code:
            match = re.match(r'CAT(\d+)', category.code)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    
    next_num = max_num + 1
    return f"CAT{next_num:03d}"


@router.post("/categories", response_model=RawMaterialCategory, status_code=status.HTTP_201_CREATED)
def create_category(
    *,
    db: Session = Depends(get_db),
    category_in: RawMaterialCategoryCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Create a new raw material category"""
    # Check if category name already exists
    existing = db.query(DBRawMaterialCategory).filter(DBRawMaterialCategory.name == category_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category_data = category_in.model_dump()
    
    # Auto-generate code if not provided
    if not category_data.get('code'):
        category_data['code'] = generate_next_category_code(db)
    else:
        # Check if code already exists
        existing_code = db.query(DBRawMaterialCategory).filter(DBRawMaterialCategory.code == category_data['code']).first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this code already exists"
            )
    
    db_category = DBRawMaterialCategory(**category_data, created_by=current_user.id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/categories", response_model=List[RawMaterialCategory])
def get_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker),
    active_only: bool = False
) -> Any:
    """Get all raw material categories"""
    query = db.query(DBRawMaterialCategory)
    
    if active_only:
        query = query.filter(DBRawMaterialCategory.is_active == True)
    
    categories = query.order_by(DBRawMaterialCategory.name).all()
    return categories


@router.get("/categories/{category_id}", response_model=RawMaterialCategory)
def get_category(
    *,
    db: Session = Depends(get_db),
    category_id: int,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Get a single raw material category"""
    category = db.query(DBRawMaterialCategory).filter(DBRawMaterialCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/categories/{category_id}", response_model=RawMaterialCategory)
def update_category(
    *,
    db: Session = Depends(get_db),
    category_id: int,
    category_in: RawMaterialCategoryUpdate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Update a raw material category"""
    category = db.query(DBRawMaterialCategory).filter(DBRawMaterialCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_in.model_dump(exclude_unset=True)
    
    # Check if name is being updated and if it conflicts
    if 'name' in update_data and update_data['name'] != category.name:
        existing = db.query(DBRawMaterialCategory).filter(DBRawMaterialCategory.name == update_data['name']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )
    
    # Check if code is being updated and if it conflicts
    if 'code' in update_data and update_data['code'] != category.code:
        existing_code = db.query(DBRawMaterialCategory).filter(DBRawMaterialCategory.code == update_data['code']).first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this code already exists"
            )
    
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    *,
    db: Session = Depends(get_db),
    category_id: int,
    current_user = Depends(get_raw_material_checker)
):
    """Delete a raw material category"""
    category = db.query(DBRawMaterialCategory).filter(DBRawMaterialCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category is in use
    checks_count = db.query(DBRawMaterialCheck).filter(DBRawMaterialCheck.category_id == category_id).count()
    orders_count = db.query(DBOrder).filter(DBOrder.category_id == category_id).count()
    
    if checks_count > 0 or orders_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category. It is used in {checks_count} check(s) and {orders_count} order(s). Consider deactivating it instead."
        )
    
    db.delete(category)
    db.commit()
    # No return statement for 204 status code


# Raw Material Check endpoints
@router.get("/raw-material-checks/next-number")
def get_next_check_number(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Get the next auto-generated check number"""
    next_number = generate_next_check_number(db)
    return {"check_number": next_number}


@router.post("/raw-material-checks", response_model=RawMaterialCheck, status_code=status.HTTP_201_CREATED)
def create_raw_material_check(
    *,
    db: Session = Depends(get_db),
    check_in: RawMaterialCheckCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Create a new raw material check"""
    check_data = check_in.model_dump()
    
    # Auto-generate check number if not provided
    if not check_data.get('check_number'):
        check_data['check_number'] = generate_next_check_number(db)
    
    db_check = DBRawMaterialCheck(
        **check_data,
        created_by=current_user.id
    )
    db.add(db_check)
    db.commit()
    db.refresh(db_check)
    return db_check


@router.get("/raw-material-checks", response_model=List[RawMaterialCheck])
def get_raw_material_checks(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker),
    status: str = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all raw material checks, optionally filtered by status"""
    query = db.query(DBRawMaterialCheck).options(joinedload(DBRawMaterialCheck.category))
    if status:
        query = query.filter(DBRawMaterialCheck.status == status)
    checks = query.offset(skip).limit(limit).all()
    return checks


@router.get("/raw-material-checks/{check_id}", response_model=RawMaterialCheck)
def get_raw_material_check(
    *,
    db: Session = Depends(get_db),
    check_id: int,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Get a specific raw material check"""
    check = db.query(DBRawMaterialCheck).options(joinedload(DBRawMaterialCheck.category)).filter(DBRawMaterialCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Raw material check not found")
    return check


@router.put("/raw-material-checks/{check_id}", response_model=RawMaterialCheck)
def update_raw_material_check(
    *,
    db: Session = Depends(get_db),
    check_id: int,
    check_in: RawMaterialCheckCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Update a raw material check"""
    db_check = db.query(DBRawMaterialCheck).filter(DBRawMaterialCheck.id == check_id).first()
    if not db_check:
        raise HTTPException(status_code=404, detail="Raw material check not found")
    
    for field, value in check_in.model_dump().items():
        setattr(db_check, field, value)
    
    db.commit()
    db.refresh(db_check)
    return db_check


@router.patch("/raw-material-checks/{check_id}/status")
def update_check_status(
    *,
    db: Session = Depends(get_db),
    check_id: int,
    new_status: str,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Update the status of a raw material check"""
    db_check = db.query(DBRawMaterialCheck).filter(DBRawMaterialCheck.id == check_id).first()
    if not db_check:
        raise HTTPException(status_code=404, detail="Raw material check not found")
    
    if new_status not in ["pending", "work_in_progress", "approved"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    db_check.status = new_status
    if new_status == "work_in_progress":
        db_check.checked_by = current_user.id
        db_check.checked_at = datetime.now()
    elif new_status == "approved":
        db_check.approved_by = current_user.id
        db_check.approved_at = datetime.now()
    
    db.commit()
    db.refresh(db_check)
    return db_check


# Order endpoints
@router.get("/orders/next-number")
def get_next_order_number(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Get the next auto-generated order number"""
    next_number = generate_next_order_number(db)
    return {"order_number": next_number}


@router.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(
    *,
    db: Session = Depends(get_db),
    order_in: OrderCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Create a new order"""
    order_data = order_in.model_dump()
    
    # Auto-generate order number if not provided
    if not order_data.get('order_number'):
        order_data['order_number'] = generate_next_order_number(db)
    
    # Calculate total amount if unit_price is provided
    if order_data.get('unit_price') and order_data.get('quantity'):
        order_data['total_amount'] = order_data['unit_price'] * order_data['quantity']
    
    db_order = DBOrder(
        **order_data,
        created_by=current_user.id
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@router.get("/orders", response_model=List[Order])
def get_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker),
    status: str = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all orders, optionally filtered by status"""
    query = db.query(DBOrder).options(joinedload(DBOrder.category))
    if status:
        query = query.filter(DBOrder.status == status)
    orders = query.offset(skip).limit(limit).all()
    return orders


@router.get("/orders/completed", response_model=List[Order])
def get_completed_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all completed orders"""
    orders = db.query(DBOrder).options(joinedload(DBOrder.category)).filter(DBOrder.status == "completed").offset(skip).limit(limit).all()
    return orders


@router.get("/orders/{order_id}", response_model=Order)
def get_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Get a specific order"""
    order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/orders/{order_id}", response_model=Order)
def update_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    order_in: OrderCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Update an order"""
    db_order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    for field, value in order_in.model_dump().items():
        setattr(db_order, field, value)
    
    # Recalculate total amount if unit_price or quantity changed
    if db_order.unit_price and db_order.quantity:
        db_order.total_amount = db_order.unit_price * db_order.quantity
    
    db.commit()
    db.refresh(db_order)
    return db_order


# Product-Supplier Mapping endpoints
@router.post("/product-supplier-mappings", response_model=ProductSupplierMapping, status_code=status.HTTP_201_CREATED)
def create_product_supplier_mapping(
    *,
    db: Session = Depends(get_db),
    mapping_in: ProductSupplierMappingCreate,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Create a new product-supplier mapping"""
    db_mapping = DBProductSupplierMapping(**mapping_in.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


@router.get("/product-supplier-mappings", response_model=List[ProductSupplierMapping])
def get_product_supplier_mappings(
    db: Session = Depends(get_db),
    current_user = Depends(get_raw_material_checker),
    product_name: str = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all product-supplier mappings, optionally filtered by product name"""
    query = db.query(DBProductSupplierMapping)
    if product_name:
        query = query.filter(DBProductSupplierMapping.product_name == product_name)
    mappings = query.offset(skip).limit(limit).all()
    return mappings


@router.get("/product-supplier-mappings/{mapping_id}", response_model=ProductSupplierMapping)
def get_product_supplier_mapping(
    *,
    db: Session = Depends(get_db),
    mapping_id: int,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Get a specific product-supplier mapping"""
    mapping = db.query(DBProductSupplierMapping).filter(DBProductSupplierMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Product-supplier mapping not found")
    return mapping


@router.delete("/product-supplier-mappings/{mapping_id}")
def delete_product_supplier_mapping(
    *,
    db: Session = Depends(get_db),
    mapping_id: int,
    current_user = Depends(get_raw_material_checker)
) -> Any:
    """Delete a product-supplier mapping"""
    mapping = db.query(DBProductSupplierMapping).filter(DBProductSupplierMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Product-supplier mapping not found")
    
    db.delete(mapping)
    db.commit()
    return {"message": "Product-supplier mapping deleted successfully"}

