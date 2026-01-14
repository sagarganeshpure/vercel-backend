from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
import json
import re

from app.schemas.user import (
    Product, ProductCreate, ProductUpdate, ProductionTracking, ProductionTrackingCreate,
    ManufacturingStage, ManufacturingStageCreate, ManufacturingStageUpdate,
    Design, DesignCreate, DesignUpdate
)
from app.db.models.user import (
    Product as DBProduct, ProductionTracking as DBProductionTracking, 
    ProductionPaper as DBProductionPaper, ManufacturingStage as DBManufacturingStage,
    Design as DBDesign
)
from app.api.deps import get_db, get_production_manager

router = APIRouter()


def generate_next_product_code(db: Session, category: str) -> str:
    """Generate the next product code based on category"""
    # Use D for Door, F for Frame
    prefix = "D" if category == "Door" else "F"
    
    # Query products that start with the prefix (D or F) followed by digits
    # Also check for old format (DOOR, FRAME)
    old_prefix = "DOOR" if category == "Door" else "FRAME"
    
    # Get all products with either new or old format
    products = db.query(DBProduct).filter(
        (DBProduct.product_code.like(f'{prefix}%')) | 
        (DBProduct.product_code.like(f'{old_prefix}%'))
    ).all()
    
    max_num = 0
    for product in products:
        # Try new format first (D01, F01, etc.)
        match = re.match(rf'^{prefix}(\d+)$', product.product_code)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
        else:
            # Try old format (DOOR00001, FRAME00001, etc.)
            match = re.match(rf'^{old_prefix}(\d+)$', product.product_code)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    
    next_num = max_num + 1
    
    # Format as D01, D02, F01, F02, etc. (2 digits)
    return f"{prefix}{next_num:02d}"


# Product endpoints
@router.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(
    *,
    db: Session = Depends(get_db),
    product_in: ProductCreate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Create a new product"""
    try:
        product_data = product_in.model_dump(exclude_unset=True)
        
        # Auto-generate product code if not provided
        if not product_data.get('product_code'):
            product_data['product_code'] = generate_next_product_code(db, product_data.get('product_category', 'Door'))
        
        # Serialize JSON fields
        if 'specifications' in product_data and product_data['specifications']:
            if isinstance(product_data['specifications'], (dict, list)):
                product_data['specifications'] = json.dumps(product_data['specifications'])
            elif isinstance(product_data['specifications'], str):
                # Already a string, validate it's valid JSON
                try:
                    json.loads(product_data['specifications'])
                except (json.JSONDecodeError, TypeError):
                    product_data['specifications'] = json.dumps({})
        
        if 'manufacturing_process' in product_data and product_data['manufacturing_process']:
            if isinstance(product_data['manufacturing_process'], list):
                # Convert list of ManufacturingProcessStep objects to JSON
                process_list = []
                for step in product_data['manufacturing_process']:
                    if isinstance(step, dict):
                        # Ensure duration_unit is set, default to 'hours' if not present
                        if 'duration_unit' not in step:
                            step['duration_unit'] = 'hours'
                        process_list.append(step)
                    else:
                        # Handle old format (string)
                        process_list.append({'step_name': step, 'time_hours': None, 'duration_unit': 'hours', 'sequence': len(process_list) + 1})
                product_data['manufacturing_process'] = json.dumps(process_list)
            elif isinstance(product_data['manufacturing_process'], str):
                # Already a string, validate it's valid JSON
                try:
                    json.loads(product_data['manufacturing_process'])
                except (json.JSONDecodeError, TypeError):
                    product_data['manufacturing_process'] = json.dumps([])
        
        db_product = DBProduct(
            **product_data,
            created_by=current_user.id
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        # Convert JSON strings back to objects for response
        product_dict = {
            'id': db_product.id,
            'product_code': db_product.product_code,
            'product_category': db_product.product_category,
            'product_type': db_product.product_type,
            'sub_type': db_product.sub_type,
            'variant': db_product.variant,
            'description': db_product.description,
            'is_active': db_product.is_active,
            'created_by': db_product.created_by,
            'created_at': db_product.created_at,
            'updated_at': db_product.updated_at,
        }
        
        # Parse JSON fields
        if db_product.specifications:
            if isinstance(db_product.specifications, str):
                try:
                    product_dict['specifications'] = json.loads(db_product.specifications)
                except (json.JSONDecodeError, TypeError):
                    product_dict['specifications'] = {}
            else:
                product_dict['specifications'] = db_product.specifications
        else:
            product_dict['specifications'] = {}
        
        if db_product.manufacturing_process:
            if isinstance(db_product.manufacturing_process, str):
                try:
                    parsed = json.loads(db_product.manufacturing_process)
                    # Handle both old format (array of strings) and new format (array of objects)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        if isinstance(parsed[0], str):
                            # Old format: convert to new format
                            product_dict['manufacturing_process'] = [
                                {'step_name': step, 'time_hours': None, 'duration_unit': 'hours', 'sequence': idx + 1}
                                for idx, step in enumerate(parsed)
                            ]
                        else:
                            # New format: already objects
                            product_dict['manufacturing_process'] = parsed
                    else:
                        product_dict['manufacturing_process'] = []
                except (json.JSONDecodeError, TypeError):
                    product_dict['manufacturing_process'] = []
            else:
                product_dict['manufacturing_process'] = db_product.manufacturing_process
        else:
            product_dict['manufacturing_process'] = []
        
        return Product(**product_dict)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        )


@router.get("/products", response_model=List[Product])
def get_products(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_manager),
    skip: int = 0,
    limit: int = 100,
    category: str = None
) -> Any:
    """Get all products, optionally filtered by category"""
    query = db.query(DBProduct)
    if category:
        query = query.filter(DBProduct.product_category == category)
    
    products = query.offset(skip).limit(limit).all()
    
    # Convert JSON strings to objects
    result = []
    for product in products:
        product_dict = {
            'id': product.id,
            'product_code': product.product_code,
            'product_category': product.product_category,
            'product_type': product.product_type,
            'sub_type': product.sub_type,
            'variant': product.variant,
            'description': product.description,
            'is_active': product.is_active,
            'created_by': product.created_by,
            'created_at': product.created_at,
            'updated_at': product.updated_at,
        }
        
        if product.specifications:
            if isinstance(product.specifications, str):
                try:
                    product_dict['specifications'] = json.loads(product.specifications)
                except (json.JSONDecodeError, TypeError):
                    product_dict['specifications'] = {}
            else:
                product_dict['specifications'] = product.specifications
        else:
            product_dict['specifications'] = {}
            
        if product.manufacturing_process:
            if isinstance(product.manufacturing_process, str):
                try:
                    parsed = json.loads(product.manufacturing_process)
                    # Handle both old format (array of strings) and new format (array of objects)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        if isinstance(parsed[0], str):
                            # Old format: convert to new format
                            product_dict['manufacturing_process'] = [
                                {'step_name': step, 'time_hours': None, 'duration_unit': 'hours', 'sequence': idx + 1}
                                for idx, step in enumerate(parsed)
                            ]
                        else:
                            # New format: already objects
                            product_dict['manufacturing_process'] = parsed
                    else:
                        product_dict['manufacturing_process'] = []
                except (json.JSONDecodeError, TypeError):
                    product_dict['manufacturing_process'] = []
            else:
                product_dict['manufacturing_process'] = product.manufacturing_process
        else:
            product_dict['manufacturing_process'] = []
        
        result.append(Product(**product_dict))
    
    return result


@router.get("/products/{product_id}", response_model=Product)
def get_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    current_user = Depends(get_production_manager)
) -> Any:
    """Get a specific product"""
    product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Convert JSON strings to objects
    product_dict = {
        'id': product.id,
        'product_code': product.product_code,
        'product_category': product.product_category,
        'product_type': product.product_type,
        'sub_type': product.sub_type,
        'variant': product.variant,
        'description': product.description,
        'is_active': product.is_active,
        'created_by': product.created_by,
        'created_at': product.created_at,
        'updated_at': product.updated_at,
    }
    
    if product.specifications:
        if isinstance(product.specifications, str):
            try:
                product_dict['specifications'] = json.loads(product.specifications)
            except (json.JSONDecodeError, TypeError):
                product_dict['specifications'] = {}
        else:
            product_dict['specifications'] = product.specifications
    else:
        product_dict['specifications'] = {}
        
        if product.manufacturing_process:
            if isinstance(product.manufacturing_process, str):
                try:
                    parsed = json.loads(product.manufacturing_process)
                    # Handle both old format (array of strings) and new format (array of objects)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        if isinstance(parsed[0], str):
                            # Old format: convert to new format
                            product_dict['manufacturing_process'] = [
                                {'step_name': step, 'time_hours': None, 'duration_unit': 'hours', 'sequence': idx + 1}
                                for idx, step in enumerate(parsed)
                            ]
                        else:
                            # New format: already objects
                            product_dict['manufacturing_process'] = parsed
                    else:
                        product_dict['manufacturing_process'] = []
                except (json.JSONDecodeError, TypeError):
                    product_dict['manufacturing_process'] = []
            else:
                product_dict['manufacturing_process'] = product.manufacturing_process
        else:
            product_dict['manufacturing_process'] = []
    
    return Product(**product_dict)


@router.put("/products/{product_id}", response_model=Product)
def update_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    product_update: ProductUpdate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Update a product"""
    product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        update_data = product_update.model_dump(exclude_unset=True)
        
        # Serialize JSON fields
        if 'specifications' in update_data and update_data['specifications']:
            if isinstance(update_data['specifications'], (dict, list)):
                update_data['specifications'] = json.dumps(update_data['specifications'])
            elif isinstance(update_data['specifications'], str):
                try:
                    json.loads(update_data['specifications'])
                except (json.JSONDecodeError, TypeError):
                    update_data['specifications'] = json.dumps({})
        
        if 'manufacturing_process' in update_data and update_data['manufacturing_process']:
            if isinstance(update_data['manufacturing_process'], list):
                process_list = []
                for step in update_data['manufacturing_process']:
                    if isinstance(step, dict):
                        if 'duration_unit' not in step:
                            step['duration_unit'] = 'hours'
                        process_list.append(step)
                    else:
                        process_list.append({'step_name': step, 'time_hours': None, 'duration_unit': 'hours', 'sequence': len(process_list) + 1})
                update_data['manufacturing_process'] = json.dumps(process_list)
            elif isinstance(update_data['manufacturing_process'], str):
                try:
                    json.loads(update_data['manufacturing_process'])
                except (json.JSONDecodeError, TypeError):
                    update_data['manufacturing_process'] = json.dumps([])
        
        # Update product fields
        for field, value in update_data.items():
            setattr(product, field, value)
        
        db.commit()
        db.refresh(product)
        
        # Convert JSON strings back to objects for response
        product_dict = {
            'id': product.id,
            'product_code': product.product_code,
            'product_category': product.product_category,
            'product_type': product.product_type,
            'sub_type': product.sub_type,
            'variant': product.variant,
            'description': product.description,
            'is_active': product.is_active,
            'created_by': product.created_by,
            'created_at': product.created_at,
            'updated_at': product.updated_at,
        }
        
        if product.specifications:
            if isinstance(product.specifications, str):
                try:
                    product_dict['specifications'] = json.loads(product.specifications)
                except (json.JSONDecodeError, TypeError):
                    product_dict['specifications'] = {}
            else:
                product_dict['specifications'] = product.specifications
        else:
            product_dict['specifications'] = {}
        
        if product.manufacturing_process:
            if isinstance(product.manufacturing_process, str):
                try:
                    parsed = json.loads(product.manufacturing_process)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        if isinstance(parsed[0], str):
                            product_dict['manufacturing_process'] = [
                                {'step_name': step, 'time_hours': None, 'duration_unit': 'hours', 'sequence': idx + 1}
                                for idx, step in enumerate(parsed)
                            ]
                        else:
                            product_dict['manufacturing_process'] = parsed
                    else:
                        product_dict['manufacturing_process'] = []
                except (json.JSONDecodeError, TypeError):
                    product_dict['manufacturing_process'] = []
            else:
                product_dict['manufacturing_process'] = product.manufacturing_process
        else:
            product_dict['manufacturing_process'] = []
        
        return Product(**product_dict)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update product: {str(e)}"
        )


# Manufacturing Stage endpoints
@router.post("/stages", response_model=ManufacturingStage, status_code=status.HTTP_201_CREATED)
def create_stage(
    *,
    db: Session = Depends(get_db),
    stage_in: ManufacturingStageCreate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Create a new manufacturing stage"""
    try:
        # Check if stage with same name already exists
        existing = db.query(DBManufacturingStage).filter(
            DBManufacturingStage.stage_name == stage_in.stage_name
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stage with name '{stage_in.stage_name}' already exists"
            )
        
        db_stage = DBManufacturingStage(
            **stage_in.model_dump(exclude_unset=True),
            created_by=current_user.id
        )
        db.add(db_stage)
        db.commit()
        db.refresh(db_stage)
        return ManufacturingStage(
            id=db_stage.id,
            stage_name=db_stage.stage_name,
            description=db_stage.description,
            is_active=db_stage.is_active,
            created_by=db_stage.created_by,
            created_at=db_stage.created_at,
            updated_at=db_stage.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create stage: {str(e)}"
        )


@router.get("/stages", response_model=List[ManufacturingStage])
def get_stages(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_manager),
    active_only: bool = True
) -> Any:
    """Get all manufacturing stages"""
    query = db.query(DBManufacturingStage)
    if active_only:
        query = query.filter(DBManufacturingStage.is_active == True)
    
    stages = query.order_by(DBManufacturingStage.stage_name).all()
    return [
        ManufacturingStage(
            id=stage.id,
            stage_name=stage.stage_name,
            description=stage.description,
            is_active=stage.is_active,
            created_by=stage.created_by,
            created_at=stage.created_at,
            updated_at=stage.updated_at
        )
        for stage in stages
    ]


@router.put("/stages/{stage_id}", response_model=ManufacturingStage)
def update_stage(
    *,
    db: Session = Depends(get_db),
    stage_id: int,
    stage_in: ManufacturingStageUpdate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Update a manufacturing stage"""
    stage = db.query(DBManufacturingStage).filter(DBManufacturingStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    update_data = stage_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stage, field, value)
    
    db.commit()
    db.refresh(stage)
    return ManufacturingStage(
        id=stage.id,
        stage_name=stage.stage_name,
        description=stage.description,
        is_active=stage.is_active,
        created_by=stage.created_by,
        created_at=stage.created_at,
        updated_at=stage.updated_at
    )


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stage(
    *,
    db: Session = Depends(get_db),
    stage_id: int,
    current_user = Depends(get_production_manager)
):
    """Delete a manufacturing stage"""
    stage = db.query(DBManufacturingStage).filter(DBManufacturingStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    db.delete(stage)
    db.commit()


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    current_user = Depends(get_production_manager)
):
    """Delete a product"""
    product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        db.delete(product)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product: {str(e)}"
        )


# Production Tracking endpoints
@router.post("/production-tracking", response_model=ProductionTracking, status_code=status.HTTP_201_CREATED)
def create_production_tracking(
    *,
    db: Session = Depends(get_db),
    tracking_in: ProductionTrackingCreate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Create a new production tracking entry"""
    tracking_data = tracking_in.model_dump()
    
    db_tracking = DBProductionTracking(
        **tracking_data,
        created_by=current_user.id
    )
    db.add(db_tracking)
    db.commit()
    db.refresh(db_tracking)
    
    return db_tracking


@router.get("/production-tracking", response_model=List[ProductionTracking])
def get_production_tracking(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_manager),
    production_paper_id: int = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get production tracking entries"""
    query = db.query(DBProductionTracking)
    if production_paper_id:
        query = query.filter(DBProductionTracking.production_paper_id == production_paper_id)
    
    tracking_entries = query.order_by(DBProductionTracking.stage_sequence).offset(skip).limit(limit).all()
    return tracking_entries


@router.put("/production-tracking/{tracking_id}", response_model=ProductionTracking)
def update_production_tracking(
    *,
    db: Session = Depends(get_db),
    tracking_id: int,
    tracking_in: ProductionTrackingCreate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Update a production tracking entry"""
    db_tracking = db.query(DBProductionTracking).filter(DBProductionTracking.id == tracking_id).first()
    if not db_tracking:
        raise HTTPException(status_code=404, detail="Production tracking entry not found")
    
    tracking_data = tracking_in.model_dump(exclude_unset=True)
    for field, value in tracking_data.items():
        setattr(db_tracking, field, value)
    
    db.commit()
    db.refresh(db_tracking)
    return db_tracking


@router.get("/production-tracking/paper/{paper_id}", response_model=List[ProductionTracking])
def get_tracking_by_paper(
    *,
    db: Session = Depends(get_db),
    paper_id: int,
    current_user = Depends(get_production_manager)
) -> Any:
    """Get all tracking entries for a specific production paper"""
    tracking_entries = db.query(DBProductionTracking).filter(
        DBProductionTracking.production_paper_id == paper_id
    ).order_by(DBProductionTracking.stage_sequence).all()
    return tracking_entries


# Design endpoints
@router.post("/designs", response_model=Design, status_code=status.HTTP_201_CREATED)
def create_design(
    *,
    db: Session = Depends(get_db),
    design_in: DesignCreate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Create a new design"""
    try:
        # Check if design_code already exists
        existing_code = db.query(DBDesign).filter(DBDesign.design_code == design_in.design_code).first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Design code already exists"
            )
        
        # Check if design_name already exists
        existing_name = db.query(DBDesign).filter(DBDesign.design_name == design_in.design_name).first()
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Design name already exists"
            )
        
        design_data = design_in.model_dump()
        design_data['product_category'] = design_data.get('product_category', 'Shutter')
        
        db_design = DBDesign(
            **design_data,
            created_by=current_user.id
        )
        db.add(db_design)
        db.commit()
        db.refresh(db_design)
        
        return db_design
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create design: {str(e)}"
        )


@router.get("/designs", response_model=List[Design])
def get_designs(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_production_manager),
    skip: int = 0,
    limit: int = 100,
    product_category: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Any:
    """Get all designs"""
    query = db.query(DBDesign)
    
    if product_category:
        query = query.filter(DBDesign.product_category == product_category)
    
    if is_active is not None:
        query = query.filter(DBDesign.is_active == is_active)
    
    designs = query.order_by(DBDesign.created_at.desc()).offset(skip).limit(limit).all()
    return designs


@router.get("/designs/{design_id}", response_model=Design)
def get_design(
    *,
    db: Session = Depends(get_db),
    design_id: int,
    current_user = Depends(get_production_manager)
) -> Any:
    """Get a specific design by ID"""
    design = db.query(DBDesign).filter(DBDesign.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return design


@router.put("/designs/{design_id}", response_model=Design)
def update_design(
    *,
    db: Session = Depends(get_db),
    design_id: int,
    design_in: DesignUpdate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Update a design"""
    db_design = db.query(DBDesign).filter(DBDesign.id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    design_data = design_in.model_dump(exclude_unset=True)
    
    # Check if design_code is being updated and if it already exists
    if 'design_code' in design_data and design_data['design_code'] != db_design.design_code:
        existing_code = db.query(DBDesign).filter(DBDesign.design_code == design_data['design_code']).first()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Design code already exists"
            )
    
    # Check if design_name is being updated and if it already exists
    if 'design_name' in design_data and design_data['design_name'] != db_design.design_name:
        existing_name = db.query(DBDesign).filter(DBDesign.design_name == design_data['design_name']).first()
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Design name already exists"
            )
    
    for field, value in design_data.items():
        setattr(db_design, field, value)
    
    db.commit()
    db.refresh(db_design)
    return db_design

