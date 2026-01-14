from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import text, inspect
from typing import List, Any
import json
import re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime

from app.schemas.user import Measurement, MeasurementCreate, MeasurementUpdate, MeasurementDeleteRequest, Party, PartyCreate, ProductionPaper, ProductionPaperCreate, ProductionPaperDeleteRequest, PartyOrderDetailsUpdate, PartyClientRequirementsUpdate, PartyHistoryEntry
from app.db.models.user import Measurement as DBMeasurement, Party as DBParty, ProductionPaper as DBProductionPaper, User as DBUser, PartyHistory as DBPartyHistory, ProductionSchedule as DBProductionSchedule
from app.api.deps import get_db, get_production_manager, get_production_manager_or_scheduler, get_measurement_captain, get_production_manager_or_raw_material_checker, get_production_access
from sqlalchemy.orm import joinedload

router = APIRouter()

# --- HOTFIX: Force DB Column Check on Module Load ---
try:
    from app.auto_migrate import fix_missing_columns
    print("Executing HOTFIX DB Migration from production endpoint...")
    fix_missing_columns()
except Exception as e:
    print(f"HOTFIX Migration failed: {e}")
# ----------------------------------------------------

@router.get("/fix-db-schema")
def trigger_db_fix(current_user = Depends(get_production_manager)):
    """Manually trigger DB schema fix"""
    results = []
    try:
        from app.db.database import engine
        from sqlalchemy import text, inspect
        
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('production_papers')}
        required = [
            "total_quantity", "wall_type", "rebate", "sub_frame", 
            "construction", "cover_moulding", "frontside_laminate", 
            "backside_laminate", "grade", "side_frame", "filler", 
            "foam_bottom", "frp_coating", "frontside_design", "backside_design", "core"
        ]
        
        with engine.connect() as conn:
            for col in required:
                if col not in columns:
                    conn.execute(text(f"ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS {col} VARCHAR"))
                    results.append(f"Added {col}")
                else:
                    results.append(f"Exists: {col}")
            conn.commit()
            
        return {"status": "success", "details": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def convert_party_to_dict(party: DBParty, db: Session = None) -> dict:
    """Convert a DBParty object to a dictionary with parsed JSON fields"""
    party_dict = {
        'id': party.id,
        'party_type': party.party_type,
        'name': party.name,
        'display_name': party.display_name,
        'customer_code': party.customer_code,
        'business_type': party.business_type,
        'office_address_line1': party.office_address_line1,
        'office_address_line2': party.office_address_line2,
        'office_area': party.office_area,
        'office_city': party.office_city,
        'office_state': party.office_state,
        'office_pin_code': party.office_pin_code,
        'office_country': party.office_country,
        'gst_registration_type': party.gst_registration_type,
        'gstin_number': party.gstin_number,
        'pan_number': party.pan_number,
        'state_code': party.state_code,
        'msme_udyam_number': party.msme_udyam_number,
        'customer_category': party.customer_category,
        'industry_type': party.industry_type,
        'estimated_monthly_volume': party.estimated_monthly_volume,
        'estimated_yearly_volume': party.estimated_yearly_volume,
        'price_category': party.price_category,
        'assigned_sales_executive': party.assigned_sales_executive,
        'marketing_source': party.marketing_source,
        'payment_terms': party.payment_terms,
        'credit_limit': party.credit_limit,
        'credit_days': party.credit_days,
        'security_cheque_pdc': party.security_cheque_pdc,
        'preferred_delivery_location': party.preferred_delivery_location,
        'unloading_responsibility': party.unloading_responsibility,
        'working_hours_at_site': party.working_hours_at_site,
        'special_instructions': party.special_instructions,
        'customer_status': party.customer_status,
        'approval_status': party.approval_status,
        'contact_person': party.contact_person,
        'email': party.email,
        'phone': party.phone,
        'address': party.address,
        'created_by': party.created_by,
        'created_at': party.created_at,
        'updated_at': party.updated_at,
    }
    
    # Get creator's username if database session is provided
    if db and party.created_by:
        creator = db.query(DBUser).filter(DBUser.id == party.created_by).first()
        if creator:
            party_dict['created_by_username'] = creator.username
        else:
            party_dict['created_by_username'] = None
    elif hasattr(party, 'created_by_user') and party.created_by_user:
        # If relationship is already loaded
        party_dict['created_by_username'] = party.created_by_user.username
    else:
        party_dict['created_by_username'] = None
    
    # Parse JSON fields safely
    if party.contact_persons:
        if isinstance(party.contact_persons, str):
            try:
                party_dict['contact_persons'] = json.loads(party.contact_persons)
            except (json.JSONDecodeError, TypeError):
                party_dict['contact_persons'] = []
        else:
            party_dict['contact_persons'] = party.contact_persons
    else:
        party_dict['contact_persons'] = []
        
    if party.site_addresses:
        if isinstance(party.site_addresses, str):
            try:
                parsed = json.loads(party.site_addresses)
                # Ensure it's a list, not a dict
                if isinstance(parsed, dict):
                    party_dict['site_addresses'] = []
                elif isinstance(parsed, list):
                    party_dict['site_addresses'] = parsed
                else:
                    party_dict['site_addresses'] = []
            except (json.JSONDecodeError, TypeError):
                party_dict['site_addresses'] = []
        else:
            # If already parsed, ensure it's a list
            if isinstance(party.site_addresses, dict):
                party_dict['site_addresses'] = []
            elif isinstance(party.site_addresses, list):
                party_dict['site_addresses'] = party.site_addresses
            else:
                party_dict['site_addresses'] = []
    else:
        party_dict['site_addresses'] = []
        
    if party.product_preferences:
        if isinstance(party.product_preferences, str):
            try:
                party_dict['product_preferences'] = json.loads(party.product_preferences)
            except (json.JSONDecodeError, TypeError):
                party_dict['product_preferences'] = None
        else:
            party_dict['product_preferences'] = party.product_preferences
    else:
        party_dict['product_preferences'] = None
        
    if party.documents:
        if isinstance(party.documents, str):
            try:
                parsed_docs = json.loads(party.documents)
                # Normalize documents to match Document schema
                if isinstance(parsed_docs, list):
                    normalized_docs = []
                    for doc in parsed_docs:
                        if isinstance(doc, dict):
                            # Handle old format with document_type, content, content_type
                            if 'document_type' in doc:
                                doc = {**doc, 'type': doc.pop('document_type')}
                            # Convert content to url (data URL) if needed
                            if 'content' in doc and 'url' not in doc:
                                content_type = doc.get('content_type', 'application/octet-stream')
                                doc['url'] = f"data:{content_type};base64,{doc['content']}"
                                # Remove old fields if they exist
                                doc.pop('content', None)
                                doc.pop('content_type', None)
                            # Ensure type field exists (required by schema)
                            if 'type' not in doc:
                                doc['type'] = doc.get('document_type', 'Other')
                            normalized_docs.append(doc)
                        else:
                            normalized_docs.append(doc)
                    party_dict['documents'] = normalized_docs
                else:
                    party_dict['documents'] = []
            except (json.JSONDecodeError, TypeError):
                party_dict['documents'] = []
        else:
            # Normalize if it's already a list
            if isinstance(party.documents, list):
                normalized_docs = []
                for doc in party.documents:
                    if isinstance(doc, dict):
                        if 'document_type' in doc:
                            doc = {**doc, 'type': doc.pop('document_type')}
                        if 'content' in doc and 'url' not in doc:
                            content_type = doc.get('content_type', 'application/octet-stream')
                            doc['url'] = f"data:{content_type};base64,{doc['content']}"
                            doc.pop('content', None)
                            doc.pop('content_type', None)
                        if 'type' not in doc:
                            doc['type'] = doc.get('document_type', 'Other')
                        normalized_docs.append(doc)
                    else:
                        normalized_docs.append(doc)
                party_dict['documents'] = normalized_docs
            else:
                party_dict['documents'] = []
    else:
        party_dict['documents'] = []
    
    # Parse frame_requirements and door_requirements
    if hasattr(party, 'frame_requirements') and party.frame_requirements:
        if isinstance(party.frame_requirements, str):
            try:
                party_dict['frame_requirements'] = json.loads(party.frame_requirements)
            except (json.JSONDecodeError, TypeError):
                party_dict['frame_requirements'] = []
        else:
            party_dict['frame_requirements'] = party.frame_requirements
    else:
        party_dict['frame_requirements'] = []
    
    if hasattr(party, 'door_requirements') and party.door_requirements:
        if isinstance(party.door_requirements, str):
            try:
                party_dict['door_requirements'] = json.loads(party.door_requirements)
            except (json.JSONDecodeError, TypeError):
                party_dict['door_requirements'] = []
        else:
            party_dict['door_requirements'] = party.door_requirements
    else:
        party_dict['door_requirements'] = []
    
    return party_dict


def generate_next_measurement_number(db: Session) -> str:
    """Generate the next measurement number in format MP00001, MP00002, etc."""
    # Get all measurements with MP prefix and extract their numbers
    measurements = db.query(DBMeasurement.measurement_number).filter(
        DBMeasurement.measurement_number.like('MP%')
    ).all()
    
    max_num = 0
    for measurement in measurements:
        # Extract the number part from measurement number (e.g., MP00001 -> 1)
        match = re.match(r'MP(\d+)', measurement.measurement_number)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    # Generate next number
    next_num = max_num + 1
    return f"MP{next_num:05d}"


# Measurements endpoints
@router.get("/measurements/next-number")
def get_next_measurement_number(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_access)
) -> Any:
    """Get the next auto-generated measurement number"""
    next_number = generate_next_measurement_number(db)
    return {"measurement_number": next_number}


@router.get("/measurements/next-serial-number")
def get_next_serial_number(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_access)
) -> Any:
    """Get the next user-specific serial number for measurement item rows (e.g., A00001, A00002, etc.)
    
    Available for: production_manager, measurement_captain, production_scheduler, raw_material_checker, admin
    """
    # Check if user has serial number prefix assigned
    if not current_user.serial_number_prefix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serial number prefix not assigned. Please contact an administrator to assign a prefix (A, B, C, etc.)."
        )
    
    # Get current counter
    counter = current_user.serial_number_counter or 0
    
    # Increment counter
    counter += 1
    
    # Wrap around at 99999
    if counter > 99999:
        counter = 1
    
    # Update user's counter in database
    current_user.serial_number_counter = counter
    db.commit()
    db.refresh(current_user)
    
    # Format: A00001, A00002, ..., A99999
    serial_number = f"{current_user.serial_number_prefix}{counter:05d}"
    
    return {"serial_number": serial_number}


@router.post("/measurements", response_model=Measurement, status_code=status.HTTP_201_CREATED)
def create_measurement(
    *,
    db: Session = Depends(get_db),
    measurement_in: MeasurementCreate,
    current_user = Depends(get_production_manager_or_scheduler)
) -> Any:
    """Create a new measurement"""
    try:
        measurement_data = measurement_in.model_dump()
        
        # Map category to measurement_type if category is provided (for MeasurementEntry compatibility)
        if 'category' in measurement_data and measurement_data.get('category') and not measurement_data.get('measurement_type'):
            category_map = {
                'Sample Frame': 'frame_sample',
                'Sample Shutter': 'shutter_sample',
                'Regular Frame': 'regular_frame',
                'Regular Shutter': 'regular_shutter'
            }
            if measurement_data['category'] in category_map:
                measurement_data['measurement_type'] = category_map[measurement_data['category']]
        # Remove category from data as it's not a database field
        measurement_data.pop('category', None)
        
        # Validate items
        if 'items' in measurement_data:
            if not measurement_data['items'] or len(measurement_data['items']) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one measurement item is required"
                )
        
        # Auto-generate measurement number if not provided
        if not measurement_data.get('measurement_number'):
            measurement_data['measurement_number'] = generate_next_measurement_number(db)
        
        # Set approval_status based on user role
        # measurement_captain creates with pending_approval, production users create with approved
        if current_user.role == 'measurement_captain':
            measurement_data['approval_status'] = 'pending_approval'
        elif 'approval_status' not in measurement_data or not measurement_data.get('approval_status'):
            measurement_data['approval_status'] = 'approved'
        
        # Convert items list to JSON string
        if 'items' in measurement_data and isinstance(measurement_data['items'], list):
            measurement_data['items'] = json.dumps(measurement_data['items'])
        
        # Convert metadata dict to JSON string if provided
        if 'metadata' in measurement_data and measurement_data.get('metadata'):
            if isinstance(measurement_data['metadata'], dict):
                measurement_data['metadata_json'] = json.dumps(measurement_data['metadata'])
            del measurement_data['metadata']  # Remove 'metadata' key, use 'metadata_json' instead
        
        db_measurement = DBMeasurement(
            **measurement_data,
            created_by=current_user.id
        )
        db.add(db_measurement)
        db.commit()
        db.refresh(db_measurement)
        
        # Convert items back to list for response (only if it's a string)
        items_data = db_measurement.items
        if items_data:
            if isinstance(items_data, str):
                try:
                    items_data = json.loads(items_data)
                except (json.JSONDecodeError, TypeError):
                    items_data = []
        # If it's already a list/dict, keep it as is
        
        # Convert metadata back to dict for response
        metadata_data = None
        if db_measurement.metadata_json:
            if isinstance(db_measurement.metadata_json, str):
                try:
                    metadata_data = json.loads(db_measurement.metadata_json)
                except (json.JSONDecodeError, TypeError):
                    metadata_data = {}
            else:
                metadata_data = db_measurement.metadata_json
        
        # Get username from created_by_user relationship
        username = None
        if hasattr(db_measurement, 'created_by_user') and db_measurement.created_by_user:
            username = db_measurement.created_by_user.username
        else:
            # Fallback: query user directly
            from app.db.models.user import User as DBUser
            user = db.query(DBUser).filter(DBUser.id == db_measurement.created_by).first()
            if user:
                username = user.username
        
        # Create response with all fields including new ones
        measurement_dict = {
            'id': db_measurement.id,
            'measurement_type': db_measurement.measurement_type,
            'measurement_number': db_measurement.measurement_number,
            'party_id': db_measurement.party_id,
            'party_name': db_measurement.party_name,
            'thickness': db_measurement.thickness,
            'measurement_date': db_measurement.measurement_date,
            'site_location': db_measurement.site_location,
            'items': items_data,
            'notes': db_measurement.notes,
            'approval_status': db_measurement.approval_status,
            'external_foam_patti': db_measurement.external_foam_patti,
            'measurement_time': db_measurement.measurement_time,
            'task_id': db_measurement.task_id,
            'status': db_measurement.status,
            'metadata': metadata_data,
            'rejection_reason': db_measurement.rejection_reason,
            'approved_by': db_measurement.approved_by,
            'approved_at': db_measurement.approved_at,
            'created_by': db_measurement.created_by,
            'created_at': db_measurement.created_at,
            'updated_at': db_measurement.updated_at,
            'created_by_username': username,
        }
        
        return Measurement(**measurement_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create measurement: {str(e)}"
        )


@router.get("/measurements", response_model=List[Measurement])
def get_measurements(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_access),  # Allow production_manager, scheduler, measurement_captain, and raw_material_checker to access
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False
) -> Any:
    """Get all measurements"""
    # Use joinedload to eagerly load the created_by_user relationship for better performance
    query = db.query(DBMeasurement).options(joinedload(DBMeasurement.created_by_user))
    
    # If user is measurement_captain, only show measurements they created
    if current_user.role == 'measurement_captain':
        query = query.filter(DBMeasurement.created_by == current_user.id)
    
    if not include_deleted:
        # Filter out deleted measurements
        query = query.filter(DBMeasurement.is_deleted == False)
    measurements = query.offset(skip).limit(limit).all()
    
    # Convert items JSON string to list for each measurement
    result = []
    for measurement in measurements:
        # Parse items JSON
        if measurement.items:
            if isinstance(measurement.items, str):
                try:
                    measurement.items = json.loads(measurement.items)
                except (json.JSONDecodeError, TypeError):
                    measurement.items = []
        
        # Get username from created_by_user relationship (eagerly loaded)
        username = None
        if measurement.created_by_user:
            username = measurement.created_by_user.username
        
        # Parse metadata JSON if exists
        metadata_data = None
        if measurement.metadata_json:
            if isinstance(measurement.metadata_json, str):
                try:
                    metadata_data = json.loads(measurement.metadata_json)
                except (json.JSONDecodeError, TypeError):
                    metadata_data = {}
            else:
                metadata_data = measurement.metadata_json
        
        # Create measurement dict and add username
        measurement_dict = {
            'id': measurement.id,
            'measurement_type': measurement.measurement_type,
            'measurement_number': measurement.measurement_number,
            'party_id': measurement.party_id,
            'party_name': measurement.party_name,
            'thickness': measurement.thickness,
            'measurement_date': measurement.measurement_date,
            'site_location': measurement.site_location,
            'items': measurement.items,
            'notes': measurement.notes,
            'approval_status': measurement.approval_status,
            'external_foam_patti': measurement.external_foam_patti,
            'measurement_time': measurement.measurement_time,
            'task_id': measurement.task_id,
            'status': measurement.status,
            'metadata': metadata_data,
            'rejection_reason': measurement.rejection_reason,
            'approved_by': measurement.approved_by,
            'approved_at': measurement.approved_at,
            'is_deleted': measurement.is_deleted,
            'deleted_at': measurement.deleted_at,
            'created_by': measurement.created_by,
            'created_at': measurement.created_at,
            'updated_at': measurement.updated_at,
            'created_by_username': username,
        }
        result.append(Measurement(**measurement_dict))
    
    return result


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(
    *,
    db: Session = Depends(get_db),
    measurement_id: int,
    delete_request: MeasurementDeleteRequest,
    current_user = Depends(get_production_manager)
):
    """Soft delete a measurement with deletion reason"""
    measurement = db.query(DBMeasurement).filter(DBMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found"
        )
    
    if measurement.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measurement is already deleted"
        )
    
    # Soft delete with reason
    measurement.is_deleted = True
    measurement.deleted_at = func.now()
    measurement.deletion_reason = delete_request.deletion_reason
    db.commit()


@router.get("/measurements/{measurement_id}", response_model=Measurement)
def get_measurement(
    *,
    db: Session = Depends(get_db),
    measurement_id: int,
    current_user = Depends(get_production_access)  # Allow production_manager, scheduler, measurement_captain, and raw_material_checker to access
) -> Any:
    """Get a specific measurement"""
    # Use joinedload to eagerly load the created_by_user relationship
    query = db.query(DBMeasurement).options(joinedload(DBMeasurement.created_by_user)).filter(DBMeasurement.id == measurement_id)
    
    # If user is measurement_captain, only allow access to measurements they created
    if current_user.role == 'measurement_captain':
        query = query.filter(DBMeasurement.created_by == current_user.id)
    
    measurement = query.first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    # Convert items JSON string to list
    items_data = measurement.items
    if items_data:
        if isinstance(items_data, str):
            try:
                items_data = json.loads(items_data)
            except (json.JSONDecodeError, TypeError):
                items_data = []
        # If it's already a list/dict, keep it as is
    
    # Get username from created_by_user relationship
    username = None
    if measurement.created_by_user:
        username = measurement.created_by_user.username
    
    # Parse metadata JSON if exists
    metadata_data = None
    if hasattr(measurement, 'metadata_json') and measurement.metadata_json:
        if isinstance(measurement.metadata_json, str):
            try:
                metadata_data = json.loads(measurement.metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata_data = {}
        else:
            metadata_data = measurement.metadata_json
    
    # Create measurement dict with username and all fields
    measurement_dict = {
        'id': measurement.id,
        'measurement_type': measurement.measurement_type,
        'measurement_number': measurement.measurement_number,
        'party_id': measurement.party_id,
        'party_name': measurement.party_name,
        'thickness': measurement.thickness,
        'measurement_date': measurement.measurement_date,
        'site_location': measurement.site_location,
        'items': items_data,
        'notes': measurement.notes,
        'approval_status': getattr(measurement, 'approval_status', 'approved'),
        'external_foam_patti': getattr(measurement, 'external_foam_patti', None),
        'measurement_time': getattr(measurement, 'measurement_time', None),
        'task_id': getattr(measurement, 'task_id', None),
        'status': getattr(measurement, 'status', 'draft'),
        'metadata': metadata_data,
        'rejection_reason': getattr(measurement, 'rejection_reason', None),
        'approved_by': getattr(measurement, 'approved_by', None),
        'approved_at': getattr(measurement, 'approved_at', None),
        'is_deleted': getattr(measurement, 'is_deleted', False),
        'deleted_at': getattr(measurement, 'deleted_at', None),
        'created_by': measurement.created_by,
        'created_at': measurement.created_at,
        'updated_at': measurement.updated_at,
        'created_by_username': username,
    }
    
    return Measurement(**measurement_dict)


def is_measurement_used_in_production_papers(measurement_id: int, db: Session) -> bool:
    """Check if a measurement is used in any production paper"""
    # Check direct reference: production_papers.measurement_id
    direct_ref = db.query(DBProductionPaper).filter(
        DBProductionPaper.measurement_id == measurement_id,
        DBProductionPaper.is_deleted == False
    ).first()
    
    if direct_ref:
        return True
    
    # Check indirect reference: parse selected_measurement_items JSON
    all_papers = db.query(DBProductionPaper).filter(
        DBProductionPaper.is_deleted == False,
        DBProductionPaper.selected_measurement_items.isnot(None)
    ).all()
    
    for paper in all_papers:
        if not paper.selected_measurement_items:
            continue
        
        try:
            selected_items = json.loads(paper.selected_measurement_items) if isinstance(paper.selected_measurement_items, str) else paper.selected_measurement_items
            if not isinstance(selected_items, list):
                continue
            
            # Check if any item references this measurement
            for item in selected_items:
                if isinstance(item, dict) and item.get('measurement_id') == measurement_id:
                    return True
                # Also check old format where measurement_id might be in the paper itself
                if paper.measurement_id == measurement_id:
                    return True
        except (json.JSONDecodeError, TypeError):
            continue
    
    return False


@router.put("/measurements/{measurement_id}", response_model=Measurement)
def update_measurement(
    *,
    db: Session = Depends(get_db),
    measurement_id: int,
    measurement_update: MeasurementUpdate,
    current_user = Depends(get_production_manager_or_scheduler)
) -> Any:
    """Update a measurement (items and notes only)"""
    # Get measurement
    measurement = db.query(DBMeasurement).filter(DBMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found"
        )
    
    # Check if measurement is used in production papers
    if is_measurement_used_in_production_papers(measurement_id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit measurement that is already used in production papers"
        )
    
    # Validate items if provided
    if measurement_update.items is not None:
        if not measurement_update.items or len(measurement_update.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one measurement item is required"
            )
        # Convert items to JSON string
        measurement.items = json.dumps(measurement_update.items)
    
    # Update notes if provided
    if measurement_update.notes is not None:
        measurement.notes = measurement_update.notes
    
    # Update edit tracking fields if edit_remark is provided
    if measurement_update.edit_remark is not None:
        measurement.last_edit_remark = measurement_update.edit_remark
        measurement.last_edited_by = current_user.id
        measurement.last_edited_at = func.now()
    
    # Update timestamp
    measurement.updated_at = func.now()
    
    db.commit()
    db.refresh(measurement)
    
    # Convert items JSON string back to list for response
    items_data = measurement.items
    if items_data:
        if isinstance(items_data, str):
            try:
                items_data = json.loads(items_data)
            except (json.JSONDecodeError, TypeError):
                items_data = []
    
    # Get username from created_by_user relationship
    username = None
    if measurement.created_by_user:
        username = measurement.created_by_user.username
    
    # Parse metadata JSON if exists
    metadata_data = None
    if hasattr(measurement, 'metadata_json') and measurement.metadata_json:
        if isinstance(measurement.metadata_json, str):
            try:
                metadata_data = json.loads(measurement.metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata_data = {}
        else:
            metadata_data = measurement.metadata_json
    
    # Create measurement dict with username and all fields
    measurement_dict = {
        'id': measurement.id,
        'measurement_type': measurement.measurement_type,
        'measurement_number': measurement.measurement_number,
        'party_id': measurement.party_id,
        'party_name': measurement.party_name,
        'thickness': measurement.thickness,
        'measurement_date': measurement.measurement_date,
        'site_location': measurement.site_location,
        'items': items_data,
        'notes': measurement.notes,
        'approval_status': getattr(measurement, 'approval_status', 'approved'),
        'external_foam_patti': getattr(measurement, 'external_foam_patti', None),
        'measurement_time': getattr(measurement, 'measurement_time', None),
        'task_id': getattr(measurement, 'task_id', None),
        'status': getattr(measurement, 'status', 'draft'),
        'metadata': metadata_data,
        'rejection_reason': getattr(measurement, 'rejection_reason', None),
        'approved_by': getattr(measurement, 'approved_by', None),
        'approved_at': getattr(measurement, 'approved_at', None),
        'is_deleted': getattr(measurement, 'is_deleted', False),
        'deleted_at': getattr(measurement, 'deleted_at', None),
        'created_by': measurement.created_by,
        'created_at': measurement.created_at,
        'updated_at': measurement.updated_at,
        'created_by_username': username,
    }
    
    return Measurement(**measurement_dict)


@router.post("/measurements/{measurement_id}/approve", status_code=status.HTTP_200_OK, response_model=Measurement)
def approve_measurement(
    *,
    db: Session = Depends(get_db),
    measurement_id: int,
    current_user = Depends(get_production_manager)
) -> Any:
    """Approve a pending measurement from measurement captain"""
    measurement = db.query(DBMeasurement).filter(DBMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found"
        )
    
    if measurement.approval_status != 'pending_approval':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Measurement is not pending approval. Current status: {measurement.approval_status}"
        )
    
    from datetime import datetime
    
    measurement.approval_status = 'approved'
    measurement.approved_by = current_user.id
    measurement.approved_at = datetime.now()
    measurement.rejection_reason = None  # Clear any previous rejection reason
    db.commit()
    db.refresh(measurement)
    
    # Convert items back to list for response
    items_data = measurement.items
    if items_data:
        if isinstance(items_data, str):
            try:
                items_data = json.loads(items_data)
            except (json.JSONDecodeError, TypeError):
                items_data = []
    
    # Parse metadata JSON if exists
    metadata_data = None
    if hasattr(measurement, 'metadata') and measurement.metadata_json:
        if isinstance(measurement.metadata_json, str):
            try:
                metadata_data = json.loads(measurement.metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata_data = {}
        else:
            metadata_data = measurement.metadata_json
    
    # Get username
    username = None
    if measurement.created_by_user:
        username = measurement.created_by_user.username
    else:
        from app.db.models.user import User as DBUser
        user = db.query(DBUser).filter(DBUser.id == measurement.created_by).first()
        if user:
            username = user.username
    
    measurement_dict = {
        'id': measurement.id,
        'measurement_type': measurement.measurement_type,
        'measurement_number': measurement.measurement_number,
        'party_id': measurement.party_id,
        'party_name': measurement.party_name,
        'thickness': measurement.thickness,
        'measurement_date': measurement.measurement_date,
        'site_location': measurement.site_location,
        'items': items_data,
        'notes': measurement.notes,
        'approval_status': measurement.approval_status,
        'external_foam_patti': getattr(measurement, 'external_foam_patti', None),
        'measurement_time': getattr(measurement, 'measurement_time', None),
        'task_id': getattr(measurement, 'task_id', None),
        'status': getattr(measurement, 'status', 'draft'),
        'metadata': metadata_data,
        'rejection_reason': getattr(measurement, 'rejection_reason', None),
        'approved_by': getattr(measurement, 'approved_by', None),
        'approved_at': getattr(measurement, 'approved_at', None),
        'is_deleted': measurement.is_deleted,
        'deleted_at': measurement.deleted_at,
        'created_by': measurement.created_by,
        'created_at': measurement.created_at,
        'updated_at': measurement.updated_at,
        'created_by_username': username,
    }
    
    return Measurement(**measurement_dict)


@router.get("/measurements/pending", response_model=List[Measurement])
def get_pending_measurements(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_manager),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all pending approval measurements"""
    measurements = db.query(DBMeasurement).options(
        joinedload(DBMeasurement.created_by_user)
    ).filter(
        DBMeasurement.approval_status == 'pending_approval',
        DBMeasurement.is_deleted == False
    ).order_by(DBMeasurement.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for measurement in measurements:
        # Parse items JSON
        items_data = measurement.items
        if items_data:
            if isinstance(items_data, str):
                try:
                    items_data = json.loads(items_data)
                except (json.JSONDecodeError, TypeError):
                    items_data = []
        
        # Parse metadata JSON if exists
        metadata_data = None
        if hasattr(measurement, 'metadata') and measurement.metadata_json:
            if isinstance(measurement.metadata_json, str):
                try:
                    metadata_data = json.loads(measurement.metadata_json)
                except (json.JSONDecodeError, TypeError):
                    metadata_data = {}
            else:
                metadata_data = measurement.metadata_json
        
        username = measurement.created_by_user.username if measurement.created_by_user else None
        
        measurement_dict = {
            'id': measurement.id,
            'measurement_type': measurement.measurement_type,
            'measurement_number': measurement.measurement_number,
            'party_id': measurement.party_id,
            'party_name': measurement.party_name,
            'thickness': measurement.thickness,
            'measurement_date': measurement.measurement_date,
            'site_location': measurement.site_location,
            'items': items_data,
            'notes': measurement.notes,
            'approval_status': measurement.approval_status,
            'external_foam_patti': getattr(measurement, 'external_foam_patti', None),
            'measurement_time': getattr(measurement, 'measurement_time', None),
            'task_id': getattr(measurement, 'task_id', None),
            'status': getattr(measurement, 'status', 'draft'),
            'metadata': metadata_data,
            'rejection_reason': getattr(measurement, 'rejection_reason', None),
            'approved_by': getattr(measurement, 'approved_by', None),
            'approved_at': getattr(measurement, 'approved_at', None),
            'created_by': measurement.created_by,
            'created_at': measurement.created_at,
            'updated_at': measurement.updated_at,
            'created_by_username': username,
        }
        result.append(Measurement(**measurement_dict))
    
    return result


@router.post("/measurements/{measurement_id}/reject", status_code=status.HTTP_200_OK, response_model=Measurement)
def reject_measurement(
    *,
    db: Session = Depends(get_db),
    measurement_id: int,
    rejection_reason: str,
    current_user = Depends(get_production_manager)
) -> Any:
    """Reject a pending measurement with reason"""
    from datetime import datetime
    
    measurement = db.query(DBMeasurement).options(
        joinedload(DBMeasurement.created_by_user)
    ).filter(DBMeasurement.id == measurement_id).first()
    
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    if measurement.approval_status != 'pending_approval':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Measurement is not pending approval. Current status: {measurement.approval_status}"
        )
    
    # Update approval status
    measurement.approval_status = 'rejected'
    measurement.approved_by = current_user.id
    measurement.approved_at = datetime.now()
    measurement.rejection_reason = rejection_reason
    
    db.commit()
    db.refresh(measurement)
    
    # Convert items JSON string to list
    items_data = measurement.items
    if items_data:
        if isinstance(items_data, str):
            try:
                items_data = json.loads(items_data)
            except (json.JSONDecodeError, TypeError):
                items_data = []
    
    # Parse metadata JSON if exists
    metadata_data = None
    if hasattr(measurement, 'metadata') and measurement.metadata_json:
        if isinstance(measurement.metadata_json, str):
            try:
                metadata_data = json.loads(measurement.metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata_data = {}
        else:
            metadata_data = measurement.metadata_json
    
    username = measurement.created_by_user.username if measurement.created_by_user else None
    
    measurement_dict = {
        'id': measurement.id,
        'measurement_type': measurement.measurement_type,
        'measurement_number': measurement.measurement_number,
        'party_id': measurement.party_id,
        'party_name': measurement.party_name,
        'thickness': measurement.thickness,
        'measurement_date': measurement.measurement_date,
        'site_location': measurement.site_location,
        'items': items_data,
        'notes': measurement.notes,
        'approval_status': measurement.approval_status,
        'external_foam_patti': getattr(measurement, 'external_foam_patti', None),
        'measurement_time': getattr(measurement, 'measurement_time', None),
        'task_id': getattr(measurement, 'task_id', None),
        'status': getattr(measurement, 'status', 'draft'),
        'metadata': metadata_data,
        'rejection_reason': getattr(measurement, 'rejection_reason', None),
        'approved_by': getattr(measurement, 'approved_by', None),
        'approved_at': getattr(measurement, 'approved_at', None),
        'created_by': measurement.created_by,
        'created_at': measurement.created_at,
        'updated_at': measurement.updated_at,
        'created_by_username': username,
    }
    
    return Measurement(**measurement_dict)


@router.post("/measurements/{measurement_id}/recover", status_code=status.HTTP_200_OK)
def recover_measurement(
    *,
    db: Session = Depends(get_db),
    measurement_id: int,
    current_user = Depends(get_production_manager)
) -> Any:
    """Recover a soft-deleted measurement"""
    measurement = db.query(DBMeasurement).filter(DBMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found"
        )
    
    if not measurement.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measurement is not deleted"
        )
    
    # Recover
    measurement.is_deleted = False
    measurement.deleted_at = None
    db.commit()
    db.refresh(measurement)
    
    return {"message": "Measurement recovered successfully", "id": measurement.id}


# Parties endpoints
@router.post("/parties", response_model=Party, status_code=status.HTTP_201_CREATED)
def create_party(
    *,
    db: Session = Depends(get_db),
    party_in: PartyCreate,
    current_user = Depends(get_production_manager_or_scheduler)  # Allow measurement_captain to create parties
) -> Any:
    """Create a new party"""
    # Check if party name already exists
    existing_party = db.query(DBParty).filter(DBParty.name == party_in.name).first()
    if existing_party:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Party with this name already exists"
        )
    
    # Convert JSON fields to strings for storage
    party_data = party_in.model_dump()
    
    # Serialize JSON fields
    if 'contact_persons' in party_data and party_data['contact_persons']:
        party_data['contact_persons'] = json.dumps(party_data['contact_persons'])
    if 'site_addresses' in party_data and party_data['site_addresses']:
        party_data['site_addresses'] = json.dumps(party_data['site_addresses'])
    if 'product_preferences' in party_data and party_data['product_preferences']:
        party_data['product_preferences'] = json.dumps(party_data['product_preferences'])
    if 'documents' in party_data and party_data['documents']:
        party_data['documents'] = json.dumps(party_data['documents'])
    if 'frame_requirements' in party_data and party_data['frame_requirements']:
        # Convert to array if it's a single object, then serialize
        frame_req = party_data['frame_requirements']
        if not isinstance(frame_req, str):
            if not isinstance(frame_req, list):
                frame_req = [frame_req]
            party_data['frame_requirements'] = json.dumps(frame_req)
    if 'door_requirements' in party_data and party_data['door_requirements']:
        # Convert to array if it's a single object, then serialize
        door_req = party_data['door_requirements']
        if not isinstance(door_req, str):
            if not isinstance(door_req, list):
                door_req = [door_req]
            party_data['door_requirements'] = json.dumps(door_req)
    
    # Generate customer code if not provided
    if not party_data.get('customer_code'):
        # Simple auto-generation: Use first 3 letters of party type + sequential number
        party_type_prefix = party_data.get('party_type', 'CUS')[:3].upper()
        last_party = db.query(DBParty).order_by(DBParty.id.desc()).first()
        next_num = (last_party.id + 1) if last_party else 1
        party_data['customer_code'] = f"{party_type_prefix}{next_num:04d}"
    
    # Set approval_status based on user role
    # measurement_captain creates with pending_approval, production users create with approved
    if current_user.role == 'measurement_captain':
        party_data['approval_status'] = 'pending_approval'
    elif 'approval_status' not in party_data or not party_data.get('approval_status') or party_data.get('approval_status') == 'Draft':
        party_data['approval_status'] = 'approved'
    
    db_party = DBParty(
        **party_data,
        created_by=current_user.id
    )
    db.add(db_party)
    db.commit()
    db.refresh(db_party)
    
    # Convert party to dictionary with parsed JSON fields for response
    party_dict = convert_party_to_dict(db_party)
    return Party(**party_dict)


@router.get("/parties", response_model=List[Party])
def get_parties(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_access),  # Allow production_manager, scheduler, measurement_captain, and raw_material_checker to access parties
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all parties"""
    parties = db.query(DBParty).offset(skip).limit(limit).all()
    
    # Convert parties to dictionaries and parse JSON fields
    result = []
    for party in parties:
        try:
            party_dict = convert_party_to_dict(party, db)
            result.append(Party(**party_dict))
        except Exception as e:
            # Log the error but continue with other parties
            print(f"Error converting party {party.id}: {str(e)}")
            continue
    
    return result


@router.get("/parties/{party_id}", response_model=Party)
def get_party(
    *,
    db: Session = Depends(get_db),
    party_id: int,
    current_user = Depends(get_production_access)  # Allow production_manager, scheduler, measurement_captain, and raw_material_checker to access parties
) -> Any:
    """Get a specific party"""
    party = db.query(DBParty).filter(DBParty.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Convert party to dictionary with parsed JSON fields
    party_dict = convert_party_to_dict(party, db)
    return Party(**party_dict)


@router.post("/parties/{party_id}/approve", response_model=Party)
def approve_party(
    *,
    db: Session = Depends(get_db),
    party_id: int,
    current_user = Depends(get_production_manager)  # Only production_manager can approve
) -> Any:
    """Approve a party (Production Manager only)"""
    party = db.query(DBParty).filter(DBParty.id == party_id).first()
    if not party:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Party not found"
        )
    
    if party.approval_status != 'pending_approval':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party is not pending approval. Current status: {party.approval_status}"
        )
    
    party.approval_status = 'approved'
    db.commit()
    db.refresh(party)
    
    # Convert party to dictionary with parsed JSON fields
    party_dict = convert_party_to_dict(party, db)
    return Party(**party_dict)


@router.put("/parties/{party_id}/order-details", response_model=Party)
def update_party_order_details(
    *,
    db: Session = Depends(get_db),
    party_id: int,
    order_details: PartyOrderDetailsUpdate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Update party order details and track changes in history"""
    party = db.query(DBParty).filter(DBParty.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Fields that can be updated
    order_detail_fields = [
        'payment_terms', 'credit_limit', 'credit_days', 'security_cheque_pdc',
        'preferred_delivery_location', 'unloading_responsibility',
        'working_hours_at_site', 'special_instructions'
    ]
    
    # Track changes and update fields
    update_data = order_details.model_dump(exclude_unset=True, exclude={'change_reason'})
    change_reason = order_details.change_reason
    
    for field_name, new_value in update_data.items():
        if field_name not in order_detail_fields:
            continue
            
        old_value = getattr(party, field_name, None)
        
        # Convert to string for comparison and storage
        old_value_str = str(old_value) if old_value is not None else None
        new_value_str = str(new_value) if new_value is not None else None
        
        # Only track if value actually changed
        if old_value_str != new_value_str:
            # Create history entry
            history_entry = DBPartyHistory(
                party_id=party.id,
                field_name=field_name,
                old_value=old_value_str,
                new_value=new_value_str,
                changed_by=current_user.id,
                change_reason=change_reason
            )
            db.add(history_entry)
            
            # Update the party field
            setattr(party, field_name, new_value)
    
    db.commit()
    db.refresh(party)
    
    # Convert party to dictionary with parsed JSON fields
    party_dict = convert_party_to_dict(party, db)
    return Party(**party_dict)


@router.put("/parties/{party_id}", response_model=Party)
def update_party(
    *,
    db: Session = Depends(get_db),
    party_id: int,
    party_update: PartyClientRequirementsUpdate,
    current_user = Depends(get_production_manager_or_scheduler)
) -> Any:
    """Update party client requirements (frame and door requirements)"""
    party = db.query(DBParty).filter(DBParty.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Update frame_requirements, door_requirements, special_instructions, customer_status, and documents
    update_data = party_update.model_dump(exclude_unset=True)
    
    # Track changes and create history entries
    fields_to_track = ['frame_requirements', 'door_requirements', 'special_instructions', 'customer_status', 'documents']
    
    for field_name in fields_to_track:
        if field_name in update_data:
            old_value = getattr(party, field_name, None)
            new_value = update_data[field_name]
            
            # Convert to string for comparison and storage
            # Handle None, empty strings, and JSON strings properly
            if old_value is None:
                old_value_str = None
            elif isinstance(old_value, str):
                old_value_str = old_value if old_value.strip() else None
            else:
                old_value_str = str(old_value)
            
            if new_value is None:
                new_value_str = None
            elif isinstance(new_value, str):
                new_value_str = new_value if new_value.strip() else None
            else:
                new_value_str = str(new_value)
            
            # Only track if value actually changed
            if old_value_str != new_value_str:
                # Create history entry
                history_entry = DBPartyHistory(
                    party_id=party.id,
                    field_name=field_name,
                    old_value=old_value_str,
                    new_value=new_value_str,
                    changed_by=current_user.id,
                    change_reason=f"Updated {field_name.replace('_', ' ').title()}"
                )
                db.add(history_entry)
                
                # Update the party field
                setattr(party, field_name, new_value)
    
    db.commit()
    db.refresh(party)
    
    # Convert party to dictionary with parsed JSON fields
    party_dict = convert_party_to_dict(party, db)
    return Party(**party_dict)


@router.get("/parties/{party_id}/client-requirements-status")
def get_client_requirements_status(
    *,
    db: Session = Depends(get_db),
    party_id: int,
    current_user = Depends(get_production_access)
) -> Any:
    """Get status of which client requirements have production papers"""
    party = db.query(DBParty).filter(DBParty.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Get all production papers for this party that reference client requirements
    production_papers = db.query(DBProductionPaper).filter(
        DBProductionPaper.client_requirement_party_id == party_id,
        DBProductionPaper.is_deleted == False
    ).all()
    
    # Build a dictionary of processed requirements with paper details
    # Format: {(requirement_type, requirement_index): [paper1, paper2, ...]}
    processed_requirements = {}
    for paper in production_papers:
        if paper.client_requirement_type and paper.client_requirement_index is not None:
            key = (paper.client_requirement_type, paper.client_requirement_index)
            if key not in processed_requirements:
                processed_requirements[key] = []
            processed_requirements[key].append({
                'id': paper.id,
                'paper_number': paper.paper_number,
                'status': paper.status
            })
    
    # Parse party's requirements to get the count
    frame_requirements = []
    door_requirements = []
    
    if party.frame_requirements:
        try:
            frame_requirements = json.loads(party.frame_requirements) if isinstance(party.frame_requirements, str) else party.frame_requirements
            if not isinstance(frame_requirements, list):
                frame_requirements = []
        except (json.JSONDecodeError, TypeError):
            frame_requirements = []
    
    if party.door_requirements:
        try:
            door_requirements = json.loads(party.door_requirements) if isinstance(party.door_requirements, str) else party.door_requirements
            if not isinstance(door_requirements, list):
                door_requirements = []
        except (json.JSONDecodeError, TypeError):
            door_requirements = []
    
    # Build response with status for each requirement
    result = {
        "party_id": party_id,
        "frame_requirements_status": [
            {
                "index": i,
                "has_production_paper": ("frame", i) in processed_requirements,
                "production_papers": processed_requirements.get(("frame", i), [])
            }
            for i in range(len(frame_requirements))
        ],
        "door_requirements_status": [
            {
                "index": i,
                "has_production_paper": ("door", i) in processed_requirements,
                "production_papers": processed_requirements.get(("door", i), [])
            }
            for i in range(len(door_requirements))
        ]
    }
    
    return result


@router.get("/parties/{party_id}/history", response_model=List[PartyHistoryEntry])
def get_party_history(
    *,
    db: Session = Depends(get_db),
    party_id: int,
    current_user = Depends(get_production_manager_or_scheduler)
) -> Any:
    """Get history of changes for a party"""
    # Verify party exists
    party = db.query(DBParty).filter(DBParty.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Get history entries
    history_entries = db.query(DBPartyHistory).filter(
        DBPartyHistory.party_id == party_id
    ).order_by(DBPartyHistory.changed_at.desc()).all()
    
    # Convert to response format with usernames
    result = []
    for entry in history_entries:
        # Get username
        user = db.query(DBUser).filter(DBUser.id == entry.changed_by).first()
        username = user.username if user else None
        
        entry_dict = {
            'id': entry.id,
            'party_id': entry.party_id,
            'field_name': entry.field_name,
            'old_value': entry.old_value,
            'new_value': entry.new_value,
            'changed_by': entry.changed_by,
            'changed_by_username': username,
            'changed_at': entry.changed_at,
            'change_reason': entry.change_reason
        }
        result.append(PartyHistoryEntry(**entry_dict))
    
    return result


# Production Papers endpoints
@router.post("/production-papers", response_model=ProductionPaper, status_code=status.HTTP_201_CREATED)
def create_production_paper(
    *,
    db: Session = Depends(get_db),
    paper_in: ProductionPaperCreate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Create a new production paper"""
    try:
        # Auto-generate paper number based on product category
        # S0001-S9999 for Shutter, F0001-F9999 for Frame
        if not paper_in.product_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product category is required to generate paper number"
            )
        
        # Determine prefix based on product category
        if paper_in.product_category == "Shutter":
            prefix = "S"
        elif paper_in.product_category == "Frame":
            prefix = "F"
        else:
            # Default to P for other categories
            prefix = "P"
        
        # Find the last paper number with the same prefix
        import re
        all_papers = db.query(DBProductionPaper).filter(
            DBProductionPaper.paper_number.like(f"{prefix}%")
        ).order_by(DBProductionPaper.id.desc()).all()
        
        max_num = 0
        for paper in all_papers:
            if paper.paper_number:
                match = re.match(rf'^{prefix}(\d+)$', paper.paper_number)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        
        # Generate next number (1-9999, then reset to 1)
        next_num = max_num + 1
        if next_num > 9999:
            next_num = 1
        
        paper_number = f"{prefix}{next_num:04d}"
        
        # Check if paper number already exists (safety check)
        existing_paper = db.query(DBProductionPaper).filter(DBProductionPaper.paper_number == paper_number).first()
        if existing_paper:
            # If exists, try next number
            next_num += 1
            if next_num > 9999:
                next_num = 1
            paper_number = f"{prefix}{next_num:04d}"
        
        # Prepare data for creation (exclude paper_number from input, always auto-generate)
        paper_data = paper_in.model_dump(exclude_unset=True, exclude={'paper_number'})
        paper_data['paper_number'] = paper_number
        
        # Validate measurement_id if provided
        measurement = None
        if paper_in.measurement_id:
            measurement = db.query(DBMeasurement).filter(DBMeasurement.id == paper_in.measurement_id).first()
            if not measurement:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Measurement with ID {paper_in.measurement_id} does not exist"
                )
            # Set party_name from measurement if not already set
            if not paper_data.get('party_name') and measurement.party_name:
                paper_data['party_name'] = measurement.party_name
            
            # Validate and handle selected_measurement_items
            if paper_in.selected_measurement_items is not None:
                # Check if it's array of objects (multiple measurements) or array of indices (single measurement)
                if isinstance(paper_in.selected_measurement_items, list) and len(paper_in.selected_measurement_items) > 0:
                    first_item = paper_in.selected_measurement_items[0]
                    # If it's an object with measurement_id, it's multiple measurements format
                    if isinstance(first_item, dict) and 'measurement_id' in first_item:
                        # Validate each item
                        for item in paper_in.selected_measurement_items:
                            if not isinstance(item, dict) or 'measurement_id' not in item or 'item_index' not in item:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="Invalid format for selected_measurement_items. Expected objects with measurement_id, item_index, and item_type"
                                )
                            # Validate measurement exists and item_index is valid
                            meas = db.query(DBMeasurement).filter(DBMeasurement.id == item['measurement_id']).first()
                            if not meas:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Measurement with ID {item['measurement_id']} does not exist"
                                )
                            # Parse measurement items
                            meas_items = meas.items
                            if isinstance(meas_items, str):
                                try:
                                    meas_items = json.loads(meas_items)
                                except (json.JSONDecodeError, TypeError):
                                    meas_items = []
                            if not isinstance(meas_items, list):
                                meas_items = []
                            if item['item_index'] < 0 or item['item_index'] >= len(meas_items):
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Invalid item_index {item['item_index']} for measurement {item['measurement_id']}. Measurement has {len(meas_items)} items"
                                )
                        # Store as JSON string
                        paper_data['selected_measurement_items'] = json.dumps(paper_in.selected_measurement_items)
                    else:
                        # It's array of indices for single measurement
                        items_data = measurement.items
                        if isinstance(items_data, str):
                            try:
                                items_data = json.loads(items_data)
                            except (json.JSONDecodeError, TypeError):
                                items_data = []
                        
                        if not isinstance(items_data, list):
                            items_data = []
                        
                        # Validate indices are within bounds
                        max_index = len(items_data) - 1
                        invalid_indices = [idx for idx in paper_in.selected_measurement_items if not isinstance(idx, int) or idx < 0 or idx > max_index]
                        if invalid_indices:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Invalid item indices: {invalid_indices}. Measurement has {len(items_data)} items (indices 0-{max_index})"
                            )
                        
                        # Convert list to JSON string for storage
                        paper_data['selected_measurement_items'] = json.dumps(paper_in.selected_measurement_items)
                else:
                    # Empty list, set to None
                    paper_data['selected_measurement_items'] = None
            else:
                # If no items selected, set to None
                paper_data['selected_measurement_items'] = None
        else:
            # If no measurement_id, clear selected_measurement_items
            paper_data['selected_measurement_items'] = None
        
        # Validate party_id if provided
        if paper_in.party_id:
            party = db.query(DBParty).filter(DBParty.id == paper_in.party_id).first()
            if not party:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Party with ID {paper_in.party_id} does not exist"
                )
            # Set party_name from party if not already set
            if not paper_data.get('party_name'):
                paper_data['party_name'] = party.name
        
        # Handle client requirement reference
        if paper_in.client_requirement_type and paper_in.client_requirement_index is not None:
            # Validate that party_id is set (required for client requirement reference)
            if not paper_in.party_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="party_id is required when client_requirement_type and client_requirement_index are provided"
                )
            
            # Validate requirement type
            if paper_in.client_requirement_type not in ['frame', 'door']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="client_requirement_type must be 'frame' or 'door'"
                )
            
            # Validate requirement index by checking the party's requirements
            party = db.query(DBParty).filter(DBParty.id == paper_in.party_id).first()
            if party:
                requirements_field = 'frame_requirements' if paper_in.client_requirement_type == 'frame' else 'door_requirements'
                requirements_json = getattr(party, requirements_field, None)
                
                if requirements_json:
                    try:
                        requirements = json.loads(requirements_json) if isinstance(requirements_json, str) else requirements_json
                        if not isinstance(requirements, list):
                            requirements = []
                    except (json.JSONDecodeError, TypeError):
                        requirements = []
                    
                    if paper_in.client_requirement_index < 0 or paper_in.client_requirement_index >= len(requirements):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid client_requirement_index {paper_in.client_requirement_index}. Party has {len(requirements)} {paper_in.client_requirement_type} requirements (indices 0-{len(requirements)-1})"
                        )
            
            # Set client requirement reference
            paper_data['client_requirement_party_id'] = paper_in.party_id
            paper_data['client_requirement_type'] = paper_in.client_requirement_type
            paper_data['client_requirement_index'] = paper_in.client_requirement_index
        
        db_paper = DBProductionPaper(
            **paper_data,
            created_by=current_user.id
        )
        db.add(db_paper)
        db.commit()
        db.refresh(db_paper)
        
        # Convert selected_measurement_items from JSON string to list for response
        selected_items = None
        if db_paper.selected_measurement_items:
            try:
                selected_items = json.loads(db_paper.selected_measurement_items)
            except (json.JSONDecodeError, TypeError):
                selected_items = None
        
        # Create response dict with parsed fields
        # Use getattr to safely access fields that may not exist in the model yet
        paper_dict = {
            'id': db_paper.id,
            'paper_number': db_paper.paper_number,
            'party_id': db_paper.party_id,
            'party_name': db_paper.party_name,
            'measurement_id': db_paper.measurement_id,
            'project_site_name': db_paper.project_site_name,
            'order_type': db_paper.order_type,
            'product_category': db_paper.product_category,
            'product_type': db_paper.product_type,
            'product_sub_type': db_paper.product_sub_type,
            'expected_dispatch_date': db_paper.expected_dispatch_date,
            'production_start_date': db_paper.production_start_date,
            'status': db_paper.status,
            'title': db_paper.title,
            'description': db_paper.description,
            'remarks': db_paper.remarks,
            'site_name': db_paper.site_name,
            'site_location': db_paper.site_location,
            'area': db_paper.area,
            'concept': db_paper.concept,
            'thickness': db_paper.thickness,
            'design': db_paper.design,
            'frontside_design': getattr(db_paper, 'frontside_design', None),
            'backside_design': getattr(db_paper, 'backside_design', None),
            'gel_colour': db_paper.gel_colour,
            'laminate': db_paper.laminate,
            'remark': db_paper.remark,
            'selected_measurement_items': selected_items,
            # Frame-specific fields
            'total_quantity': getattr(db_paper, 'total_quantity', None),
            'wall_type': getattr(db_paper, 'wall_type', None),
            'rebate': getattr(db_paper, 'rebate', None),
            'sub_frame': getattr(db_paper, 'sub_frame', None),
            'construction': getattr(db_paper, 'construction', None),
            'cover_moulding': getattr(db_paper, 'cover_moulding', None),
            # Shutter-specific fields
            'frontside_laminate': getattr(db_paper, 'frontside_laminate', None),
            'backside_laminate': getattr(db_paper, 'backside_laminate', None),
            'grade': getattr(db_paper, 'grade', None),
            'side_frame': getattr(db_paper, 'side_frame', None),
            'filler': getattr(db_paper, 'filler', None),
            'foam_bottom': getattr(db_paper, 'foam_bottom', None),
            'frp_coating': getattr(db_paper, 'frp_coating', None),
            'created_by': db_paper.created_by,
            'created_at': db_paper.created_at,
            'updated_at': db_paper.updated_at,
        }
        
        return ProductionPaper(**paper_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create production paper: {str(e)}"
        )

@router.get("/production-papers/next-number")
def get_next_paper_number(
    product_category: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_production_manager)
) -> Any:
    """Get the next auto-generated paper number based on product category"""
    try:
        # Determine prefix based on product category
        if product_category == "Shutter":
            prefix = "S"
        elif product_category == "Frame":
            prefix = "F"
        else:
            # Default to P if no category or unknown category
            prefix = "P"
        
        # Find the last paper number with the same prefix
        import re
        all_papers = db.query(DBProductionPaper).filter(
            DBProductionPaper.paper_number.like(f"{prefix}%")
        ).order_by(DBProductionPaper.id.desc()).all()
        
        max_num = 0
        for paper in all_papers:
            if paper.paper_number:
                match = re.match(rf'^{prefix}(\d+)$', paper.paper_number)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        
        # Generate next number (1-9999, then reset to 1)
        next_num = max_num + 1
        if next_num > 9999:
            next_num = 1
        
        paper_number = f"{prefix}{next_num:04d}"
        return {"next_paper_number": paper_number}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate next paper number: {str(e)}"
        )


@router.get("/production-papers", response_model=List[ProductionPaper])
def get_production_papers(
    db: Session = Depends(get_db),
    current_user = Depends(get_production_manager_or_raw_material_checker),
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False
) -> Any:
    """Get all production papers"""
    try:
        from sqlalchemy import select, inspect
        from sqlalchemy.exc import ProgrammingError, OperationalError
        from app.schemas.user import ProductionPaperParty, ProductionPaperMeasurement
        
        # Check if is_deleted column exists in the database
        try:
            inspector = inspect(db.bind)
            columns = [col['name'] for col in inspector.get_columns('production_papers')]
            has_is_deleted = 'is_deleted' in columns
        except Exception:
            # If we can't inspect, assume column doesn't exist
            has_is_deleted = False
        
        # Get all production papers first, filter by is_deleted if column exists
        query = db.query(DBProductionPaper)
        
        # Only filter by is_deleted if the column exists in database
        if has_is_deleted:
            if not include_deleted:
                query = query.filter(DBProductionPaper.is_deleted == False)
            else:
                query = query.filter(DBProductionPaper.is_deleted == True)
        
        # Try to execute the query, catch error if column doesn't exist
        try:
            papers = query.offset(skip).limit(limit).all()
        except Exception as e:
            # Check if error is due to missing column
            error_str = str(e).lower()
            if 'is_deleted' in error_str and ('does not exist' in error_str or 'undefinedcolumn' in error_str or 'infailedsqltransaction' in error_str):
                # Column doesn't exist in database, rollback transaction first
                db.rollback()
                import logging
                logging.warning(f"is_deleted column not found in database, using workaround: {str(e)}")
                # Use raw SQL to select only columns that exist (excluding is_deleted, deleted_at, deletion_reason)
                from sqlalchemy import text
                result = db.execute(text("""
                    SELECT id, paper_number, party_id, party_name, measurement_id, project_site_name,
                           order_type, product_category, product_type, product_sub_type,
                           expected_dispatch_date, production_start_date, status,
                           shutter_available, laminate_available, frame_material_available,
                           raw_material_check_date, title, description, remarks,
                           site_name, site_location, area, concept, thickness, design,
                           gel_colour, laminate, remark, selected_measurement_items,
                           created_by, created_at, updated_at
                    FROM production_papers
                    ORDER BY id DESC
                    LIMIT :limit OFFSET :offset
                """), {"limit": limit, "offset": skip})
                rows = result.fetchall()
                # Convert rows to model instances manually
                papers = []
                col_names = [col for col in result.keys()]
                for row in rows:
                    paper = DBProductionPaper()
                    for i, col_name in enumerate(col_names):
                        setattr(paper, col_name, row[i])
                    # Set soft delete fields to defaults since they don't exist
                    paper.is_deleted = False
                    paper.deleted_at = None
                    paper.deletion_reason = None
                    papers.append(paper)
            else:
                # Re-raise if it's a different error
                raise
        
        # Get unique party IDs and measurement IDs
        party_ids = [p.party_id for p in papers if p.party_id]
        measurement_ids = [p.measurement_id for p in papers if p.measurement_id]
        
        # Manually query parties and measurements with only the columns we need
        parties_dict = {}
        if party_ids:
            parties = db.query(DBParty.id, DBParty.name).filter(DBParty.id.in_(party_ids)).all()
            parties_dict = {p.id: p for p in parties}
        
        measurements_dict = {}
        if measurement_ids:
            measurements = db.query(
                DBMeasurement.id, 
                DBMeasurement.measurement_number, 
                DBMeasurement.party_name
            ).filter(DBMeasurement.id.in_(measurement_ids)).all()
            measurements_dict = {m.id: m for m in measurements}
        
        # Convert to Pydantic models with nested party and measurement data
        result = []
        for paper in papers:
            # Parse selected_measurement_items from JSON string to list
            selected_items = None
            if paper.selected_measurement_items:
                try:
                    selected_items = json.loads(paper.selected_measurement_items)
                except (json.JSONDecodeError, TypeError):
                    selected_items = None
            
            paper_data = {
                "id": paper.id,
                "paper_number": paper.paper_number,
                "party_id": paper.party_id,
                "party_name": paper.party_name,
                "measurement_id": paper.measurement_id,
                "project_site_name": paper.project_site_name,
                "order_type": paper.order_type,
                "product_category": paper.product_category,
                "product_type": paper.product_type,
                "product_sub_type": paper.product_sub_type,
                "expected_dispatch_date": paper.expected_dispatch_date,
                "production_start_date": paper.production_start_date,
                "status": paper.status,
                "title": paper.title,
                "description": paper.description,
                "remarks": paper.remarks,
                "site_name": paper.site_name,
                "site_location": paper.site_location,
                "area": paper.area,
                "concept": paper.concept,
                "thickness": paper.thickness,
                "design": paper.design,
                "frontside_design": getattr(paper, 'frontside_design', None),
                "backside_design": getattr(paper, 'backside_design', None),
                "gel_colour": paper.gel_colour,
                "laminate": paper.laminate,
                "remark": paper.remark,
                "selected_measurement_items": selected_items,
                # Frame-specific fields
                "total_quantity": getattr(paper, 'total_quantity', None),
                "wall_type": getattr(paper, 'wall_type', None),
                "rebate": getattr(paper, 'rebate', None),
                "sub_frame": getattr(paper, 'sub_frame', None),
                "construction": getattr(paper, 'construction', None),
                "cover_moulding": getattr(paper, 'cover_moulding', None),
                # Shutter-specific fields
                "frontside_laminate": getattr(paper, 'frontside_laminate', None),
                "backside_laminate": getattr(paper, 'backside_laminate', None),
                "grade": getattr(paper, 'grade', None),
                "side_frame": getattr(paper, 'side_frame', None),
                "filler": getattr(paper, 'filler', None),
                "foam_bottom": getattr(paper, 'foam_bottom', None),
                "frp_coating": getattr(paper, 'frp_coating', None),
                "created_by": paper.created_by,
                "created_at": paper.created_at,
                "updated_at": paper.updated_at,
                "is_deleted": getattr(paper, 'is_deleted', False),
                "deleted_at": getattr(paper, 'deleted_at', None),
                "deletion_reason": getattr(paper, 'deletion_reason', None),
            }
            
            # Add party data if exists
            if paper.party_id and paper.party_id in parties_dict:
                party = parties_dict[paper.party_id]
                paper_data["party"] = ProductionPaperParty(
                    id=party.id,
                    name=party.name
                )
            
            # Add measurement data if exists
            if paper.measurement_id and paper.measurement_id in measurements_dict:
                measurement = measurements_dict[paper.measurement_id]
                paper_data["measurement"] = ProductionPaperMeasurement(
                    id=measurement.id,
                    measurement_number=measurement.measurement_number,
                    party_name=measurement.party_name
                )
            
            result.append(ProductionPaper(**paper_data))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        logging.error(f"Error in get_production_papers: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load production papers: {str(e)}"
        )


@router.get("/production-papers/{paper_id}", response_model=ProductionPaper)
def get_production_paper(
    *,
    db: Session = Depends(get_db),
    paper_id: int,
    current_user = Depends(get_production_manager_or_raw_material_checker)
) -> Any:
    """Get a specific production paper"""
    try:
        paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == paper_id).first()
    except Exception as e:
        # If error is due to missing is_deleted column, use raw SQL
        error_str = str(e).lower()
        if 'is_deleted' in error_str and ('does not exist' in error_str or 'undefinedcolumn' in error_str):
            db.rollback()
            from sqlalchemy import text
            result = db.execute(text("""
                SELECT id, paper_number, party_id, party_name, measurement_id, project_site_name,
                       order_type, product_category, product_type, product_sub_type,
                       expected_dispatch_date, production_start_date, status,
                       shutter_available, laminate_available, frame_material_available,
                       raw_material_check_date, title, description, remarks,
                       site_name, site_location, area, concept, thickness, design,
                       gel_colour, laminate, remark, selected_measurement_items,
                       created_by, created_at, updated_at
                FROM production_papers
                WHERE id = :paper_id
            """), {"paper_id": paper_id})
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Production paper not found")
            # Create paper object manually
            paper = DBProductionPaper()
            col_names = [col for col in result.keys()]
            for i, col_name in enumerate(col_names):
                setattr(paper, col_name, row[i])
            # Set soft delete fields to defaults
            paper.is_deleted = False
            paper.deleted_at = None
            paper.deletion_reason = None
        else:
            raise
    
    if not paper:
        raise HTTPException(status_code=404, detail="Production paper not found")
    
    # Load party and measurement relationships
    party_data = None
    if paper.party_id:
        party = db.query(DBParty.id, DBParty.name).filter(DBParty.id == paper.party_id).first()
        if party:
            party_data = {'id': party.id, 'name': party.name}
    
    measurement_data = None
    if paper.measurement_id:
        measurement = db.query(
            DBMeasurement.id,
            DBMeasurement.measurement_number,
            DBMeasurement.party_name
        ).filter(DBMeasurement.id == paper.measurement_id).first()
        if measurement:
            measurement_data = {
                'id': measurement.id,
                'measurement_number': measurement.measurement_number,
                'party_name': measurement.party_name
            }
    
    # Parse selected_measurement_items from JSON string to list
    selected_items = None
    if paper.selected_measurement_items:
        try:
            selected_items = json.loads(paper.selected_measurement_items)
        except (json.JSONDecodeError, TypeError):
            selected_items = None
    
    # Create response dict with parsed fields
    # Use getattr to safely access fields that may not exist in the model yet
    paper_dict = {
        'id': paper.id,
        'paper_number': paper.paper_number,
        'party_id': paper.party_id,
        'party_name': paper.party_name,
        'measurement_id': paper.measurement_id,
        'project_site_name': paper.project_site_name,
        'order_type': paper.order_type,
        'product_category': paper.product_category,
        'product_type': paper.product_type,
        'product_sub_type': paper.product_sub_type,
        'expected_dispatch_date': paper.expected_dispatch_date,
        'production_start_date': paper.production_start_date,
        'status': paper.status,
        'title': paper.title,
        'description': paper.description,
        'remarks': paper.remarks,
        'site_name': paper.site_name,
        'site_location': paper.site_location,
        'area': paper.area,
        'concept': paper.concept,
        'thickness': paper.thickness,
        'design': paper.design,
        'frontside_design': getattr(paper, 'frontside_design', None),
        'backside_design': getattr(paper, 'backside_design', None),
        'gel_colour': paper.gel_colour,
        'laminate': paper.laminate,
        'remark': paper.remark,
        'selected_measurement_items': selected_items,
        # Frame-specific fields
        'total_quantity': getattr(paper, 'total_quantity', None),
        'wall_type': getattr(paper, 'wall_type', None),
        'rebate': getattr(paper, 'rebate', None),
        'sub_frame': getattr(paper, 'sub_frame', None),
        'construction': getattr(paper, 'construction', None),
        'cover_moulding': getattr(paper, 'cover_moulding', None),
        # Shutter-specific fields
        'frontside_laminate': getattr(paper, 'frontside_laminate', None),
        'backside_laminate': getattr(paper, 'backside_laminate', None),
        'grade': getattr(paper, 'grade', None),
        'side_frame': getattr(paper, 'side_frame', None),
        'filler': getattr(paper, 'filler', None),
        'foam_bottom': getattr(paper, 'foam_bottom', None),
        'frp_coating': getattr(paper, 'frp_coating', None),
        'created_by': paper.created_by,
        'created_at': paper.created_at,
        'updated_at': paper.updated_at,
        'is_deleted': getattr(paper, 'is_deleted', False),
        'deleted_at': getattr(paper, 'deleted_at', None),
        'deletion_reason': getattr(paper, 'deletion_reason', None),
        # Include nested party and measurement data
        'party': party_data,
        'measurement': measurement_data,
    }
    
    return ProductionPaper(**paper_dict)


def generate_production_paper_pdf(paper_data: dict, measurement_items: List[dict] = None) -> BytesIO:
    """Generate a professional PDF for a production paper"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=10*mm, leftMargin=10*mm,
                           topMargin=15*mm, bottomMargin=15*mm)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=3,
        fontName='Helvetica'
    )
    
    # Header Section
    header_text = f"{paper_data.get('party_name', 'N/A')} - {paper_data.get('site_name', 'N/A')} - {paper_data.get('site_location', 'N/A')} - {paper_data.get('paper_number', 'N/A')}"
    elements.append(Paragraph(header_text, title_style))
    elements.append(Spacer(1, 5*mm))
    
    # Product Info Row
    created_at = paper_data.get('created_at')
    date_str = created_at.strftime('%d/%m/%Y, %I:%M %p') if created_at else '-'
    product_info_data = [
        [paper_data.get('product_category', '-'), f"Date: {date_str}"]
    ]
    product_info_table = Table(product_info_data, colWidths=[100*mm, 90*mm])
    product_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(product_info_table)
    elements.append(Spacer(1, 5*mm))
    
    # Specifications Section
    specs_data = []
    product_category = paper_data.get('product_category', '')
    
    # Left column
    left_col = [
        ['Product Category *:', paper_data.get('product_category', '-')],
        ['Total Quantity:', paper_data.get('total_quantity', '-')],
        ['Concept:', paper_data.get('concept', '-')],
    ]
    
    # Right column
    right_col = [
        ['Order Type:', paper_data.get('order_type', '-')],
        ['Area:', paper_data.get('area', '-')],
    ]
    
    if product_category == 'Frame':
        left_col.extend([
            ['Wall Type:', paper_data.get('wall_type', '-')],
            ['Rebate:', paper_data.get('rebate', '-')],
            ['Sub Frame:', paper_data.get('sub_frame', '-')],
            ['Construction:', paper_data.get('construction', '-')],
            ['Cover Moulding:', paper_data.get('cover_moulding', '-')],
            ['Laminate:', paper_data.get('laminate', '-')],
        ])
    elif product_category == 'Shutter':
        left_col.extend([
            ['Thickness:', paper_data.get('thickness', '-')],
            ['Frontside Design:', paper_data.get('frontside_design', paper_data.get('design', '-'))],
            ['Backside Design:', paper_data.get('backside_design', '-')],
            ['Frontside Laminate:', paper_data.get('frontside_laminate', paper_data.get('laminate', '-'))],
            ['Backside Laminate:', paper_data.get('backside_laminate', '-')],
            ['Gel Colour:', paper_data.get('gel_colour', '-')],
            ['Grade:', paper_data.get('grade', '-')],
            ['Side Frame:', paper_data.get('side_frame', '-')],
            ['Filler:', paper_data.get('filler', '-')],
            ['FOAM Bottom:', paper_data.get('foam_bottom', '-')],
            ['FRP Coating:', paper_data.get('frp_coating', '-')],
        ])
    
    left_col.append(['Remark:', paper_data.get('remark', paper_data.get('remarks', '-'))])
    
    # Combine into two columns
    max_rows = max(len(left_col), len(right_col))
    for i in range(max_rows):
        row = []
        if i < len(left_col):
            row.extend(left_col[i])
        else:
            row.extend(['', ''])
        if i < len(right_col):
            row.extend(right_col[i])
        else:
            row.extend(['', ''])
        specs_data.append(row)
    
    specs_table = Table(specs_data, colWidths=[45*mm, 50*mm, 40*mm, 55*mm])
    specs_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(specs_table)
    elements.append(Spacer(1, 5*mm))
    
    # Measurement Items Table
    if measurement_items and len(measurement_items) > 0:
        # Table header
        measurement_type = paper_data.get('measurement', {}).get('measurement_type', '')
        header_col = 'FLAT' if 'shutter' in str(measurement_type).lower() else 'WALL'
        table_data = [['SR.NO', 'WIDTH', 'HEIGHT', header_col, 'AREA', 'QTY']]
        
        # Table rows
        for idx, item in enumerate(measurement_items):
            width = item.get('width') or item.get('w') or item.get('act_width') or '-'
            height = item.get('height') or item.get('h') or item.get('act_height') or '-'
            wall_flat = item.get('wall') or item.get('flat') or item.get('flat_no') or '-'
            area = item.get('area') or item.get('location') or item.get('location_of_fitting') or '-'
            qty = item.get('qty') or item.get('quantity') or 1
            
            # Convert mm to inches if needed
            if isinstance(width, (int, float)) or (isinstance(width, str) and width.replace('.', '').replace('-', '').isdigit()):
                if isinstance(width, str):
                    try:
                        width_num = float(width)
                    except ValueError:
                        width_num = None
                else:
                    width_num = width
                if width_num and width_num > 100:  # Likely in mm
                    width = f"{width_num * 0.0393701:.2f}\""
                elif width_num and '"' not in str(width):
                    width = f"{width}\""
            
            if isinstance(height, (int, float)) or (isinstance(height, str) and height.replace('.', '').replace('-', '').isdigit()):
                if isinstance(height, str):
                    try:
                        height_num = float(height)
                    except ValueError:
                        height_num = None
                else:
                    height_num = height
                if height_num and height_num > 100:  # Likely in mm
                    height = f"{height_num * 0.0393701:.2f}\""
                elif height_num and '"' not in str(height):
                    height = f"{height}\""
            
            table_data.append([
                str(item.get('sr_no', idx + 1)),
                str(width),
                str(height),
                str(wall_flat),
                str(area),
                str(qty)
            ])
        
        # Total row
        table_data.append(['TOTAL', '', '', '', '', f"{len(measurement_items)} {'SET' if len(measurement_items) == 1 else 'SETS'}"])
        
        items_table = Table(table_data, colWidths=[25*mm, 30*mm, 30*mm, 30*mm, 30*mm, 25*mm])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 5*mm))
        
        # Second Table: Detailed Measurement Information
        if measurement_items and len(measurement_items) > 0:
            product_category = paper_data.get('product_category', '').lower()
            
            # Helper function to get width in MM
            def get_width_mm(item):
                width = item.get('act_width') or item.get('width') or '-'
                if width == '-' or not width:
                    return '-'
                try:
                    width_num = float(width) if isinstance(width, (int, float)) else float(str(width).replace('"', ''))
                    # If it's a small number (< 100), assume inches and convert to mm
                    if width_num < 100:
                        width_num = width_num * 25.4
                    return str(int(round(width_num)))
                except:
                    return str(width)
            
            # Helper function to get height in MM
            def get_height_mm(item):
                height = item.get('act_height') or item.get('height') or '-'
                if height == '-' or not height:
                    return '-'
                try:
                    height_num = float(height) if isinstance(height, (int, float)) else float(str(height).replace('"', ''))
                    # If it's a small number (< 100), assume inches and convert to mm
                    if height_num < 100:
                        height_num = height_num * 25.4
                    return str(int(round(height_num)))
                except:
                    return str(height)
            
            # Helper function to get width in inches
            def get_width_inch(item):
                width = item.get('act_width') or item.get('width') or '-'
                if width == '-' or not width:
                    return '-'
                try:
                    width_num = float(width) if isinstance(width, (int, float)) else float(str(width).replace('"', ''))
                    # If it's > 100, assume mm and convert to inches
                    if width_num > 100:
                        width_num = width_num * 0.0393701
                    return f"{width_num:.2f}\""
                except:
                    return str(width)
            
            # Helper function to get height in inches
            def get_height_inch(item):
                height = item.get('act_height') or item.get('height') or '-'
                if height == '-' or not height:
                    return '-'
                try:
                    height_num = float(height) if isinstance(height, (int, float)) else float(str(height).replace('"', ''))
                    # If it's > 100, assume mm and convert to inches
                    if height_num > 100:
                        height_num = height_num * 0.0393701
                    return f"{height_num:.2f}\""
                except:
                    return str(height)
            
            # Frame Table
            if product_category == 'frame':
                detailed_table_data = [['BLDG/Wings', 'Flat No', 'Area', 'ACT Width (MM)', 'ACT Height (MM)', 'WALL', 'Subframe Side']]
                
                for idx, item in enumerate(measurement_items):
                    bldg = str(item.get('bldg') or item.get('bldg_wing') or '-')
                    flat_no = str(item.get('flat_no') or item.get('flat') or '-')
                    area = str(item.get('area') or '-')
                    width_mm = get_width_mm(item)
                    height_mm = get_height_mm(item)
                    wall = str(item.get('wall') or '-')
                    subframe = str(item.get('subframe_side') or item.get('sub_frame') or '-')
                    
                    detailed_table_data.append([
                        bldg,
                        flat_no,
                        area,
                        width_mm,
                        height_mm,
                        wall,
                        subframe
                    ])
                
                # Create detailed table for Frame
                detailed_table = Table(detailed_table_data, colWidths=[20*mm, 20*mm, 15*mm, 25*mm, 25*mm, 20*mm, 25*mm])
                detailed_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                
                # Add title for second table
                elements.append(Spacer(1, 3*mm))
                elements.append(Paragraph("Selected Measurements Details", header_style))
                elements.append(Spacer(1, 2*mm))
                elements.append(detailed_table)
                elements.append(Spacer(1, 5*mm))
            
            # Shutter Table
            elif product_category == 'shutter' or product_category == 'door':
                detailed_table_data = [['Sr No', 'BLDG/Wings', 'Location', 'Flat No', 'Area', 'Width', 'Height', 'Act Width(mm)', 'Act Height (mm)', 'Act Width (inch)', 'Act Height (inch)', 'ro_width', 'ro_height']]
                
                for idx, item in enumerate(measurement_items):
                    sr_no = str(item.get('sr_no', idx + 1))
                    bldg = str(item.get('bldg') or item.get('bldg_wing') or '-')
                    location = str(item.get('location') or item.get('location_of_fitting') or '-')
                    flat_no = str(item.get('flat_no') or item.get('flat') or '-')
                    area = str(item.get('area') or '-')
                    width = str(item.get('w') or item.get('width') or '-')
                    height = str(item.get('h') or item.get('height') or '-')
                    act_width_mm = get_width_mm(item)
                    act_height_mm = get_height_mm(item)
                    act_width_inch = get_width_inch(item)
                    act_height_inch = get_height_inch(item)
                    ro_width = str(item.get('ro_width') or '-')
                    ro_height = str(item.get('ro_height') or '-')
                    
                    detailed_table_data.append([
                        sr_no,
                        bldg,
                        location,
                        flat_no,
                        area,
                        width,
                        height,
                        act_width_mm,
                        act_height_mm,
                        act_width_inch,
                        act_height_inch,
                        ro_width,
                        ro_height
                    ])
                
                # Create detailed table for Shutter
                detailed_table = Table(detailed_table_data, colWidths=[12*mm, 15*mm, 20*mm, 15*mm, 12*mm, 15*mm, 15*mm, 18*mm, 18*mm, 18*mm, 18*mm, 15*mm, 15*mm])
                detailed_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 7),
                    ('FONTSIZE', (0, 1), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                
                # Add title for second table
                elements.append(Spacer(1, 3*mm))
                elements.append(Paragraph("Selected Measurements Details", header_style))
                elements.append(Spacer(1, 2*mm))
                elements.append(detailed_table)
                elements.append(Spacer(1, 5*mm))
    
    # Footer
    footer_text = f"Generated on {datetime.now().strftime('%d/%m/%Y, %I:%M %p')}"
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


@router.get("/production-papers/{paper_id}/pdf")
def get_production_paper_pdf(
    *,
    db: Session = Depends(get_db),
    paper_id: int,
    current_user = Depends(get_production_manager_or_raw_material_checker)
) -> Response:
    """Generate and download PDF for a production paper"""
    try:
        # Get production paper
        paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Production paper not found")
        
        # Parse selected_measurement_items
        selected_items = None
        if paper.selected_measurement_items:
            try:
                selected_items = json.loads(paper.selected_measurement_items)
            except (json.JSONDecodeError, TypeError):
                selected_items = None
        
        # Prepare paper data
        paper_data = {
            'id': paper.id,
            'paper_number': paper.paper_number,
            'party_id': paper.party_id,
            'party_name': paper.party_name,
            'measurement_id': paper.measurement_id,
            'project_site_name': paper.project_site_name,
            'order_type': paper.order_type,
            'product_category': paper.product_category,
            'product_type': paper.product_type,
            'product_sub_type': paper.product_sub_type,
            'site_name': paper.site_name,
            'site_location': paper.site_location,
            'area': paper.area,
            'concept': paper.concept,
            'thickness': paper.thickness,
            'design': paper.design,
            'frontside_design': getattr(paper, 'frontside_design', None),
            'backside_design': getattr(paper, 'backside_design', None),
            'gel_colour': paper.gel_colour,
            'laminate': paper.laminate,
            'remark': paper.remark,
            'remarks': paper.remarks,
            'total_quantity': getattr(paper, 'total_quantity', None),
            'wall_type': getattr(paper, 'wall_type', None),
            'rebate': getattr(paper, 'rebate', None),
            'sub_frame': getattr(paper, 'sub_frame', None),
            'construction': getattr(paper, 'construction', None),
            'cover_moulding': getattr(paper, 'cover_moulding', None),
            'frontside_laminate': getattr(paper, 'frontside_laminate', None),
            'backside_laminate': getattr(paper, 'backside_laminate', None),
            'grade': getattr(paper, 'grade', None),
            'side_frame': getattr(paper, 'side_frame', None),
            'filler': getattr(paper, 'filler', None),
            'foam_bottom': getattr(paper, 'foam_bottom', None),
            'frp_coating': getattr(paper, 'frp_coating', None),
            'created_at': paper.created_at,
        }
        
        # Load measurement items
        measurement_items = []
        if selected_items and isinstance(selected_items, list) and len(selected_items) > 0:
            first_item = selected_items[0]
            
            if isinstance(first_item, dict) and 'measurement_id' in first_item:
                # Multiple measurements format
                measurement_ids = set(item['measurement_id'] for item in selected_items if isinstance(item, dict))
                measurements_map = {}
                measurements_metadata = {}
                
                for meas_id in measurement_ids:
                    try:
                        meas = db.query(DBMeasurement).filter(DBMeasurement.id == meas_id).first()
                        if meas:
                            items = []
                            if isinstance(meas.items, str):
                                try:
                                    items = json.loads(meas.items)
                                except (json.JSONDecodeError, TypeError):
                                    items = []
                            elif isinstance(meas.items, list):
                                items = meas.items
                            measurements_map[meas_id] = items
                            # Store measurement metadata
                            measurements_metadata[meas_id] = {
                                'measurement_number': meas.measurement_number,
                                'measurement_date': meas.measurement_date
                            }
                    except Exception as e:
                        print(f"Error loading measurement {meas_id}: {e}")
                
                # Extract selected items with metadata
                for item in selected_items:
                    if isinstance(item, dict) and 'measurement_id' in item and 'item_index' in item:
                        meas_id = item['measurement_id']
                        item_idx = item['item_index']
                        if meas_id in measurements_map and item_idx < len(measurements_map[meas_id]):
                            item_data = measurements_map[meas_id][item_idx].copy()
                            # Add measurement metadata to item
                            if meas_id in measurements_metadata:
                                item_data['_measurement_number'] = measurements_metadata[meas_id]['measurement_number']
                                item_data['_measurement_date'] = measurements_metadata[meas_id]['measurement_date']
                            measurement_items.append(item_data)
            elif isinstance(first_item, int) and paper.measurement_id:
                # Single measurement format - array of indices
                try:
                    meas = db.query(DBMeasurement).filter(DBMeasurement.id == paper.measurement_id).first()
                    if meas:
                        items = []
                        if isinstance(meas.items, str):
                            try:
                                items = json.loads(meas.items)
                            except (json.JSONDecodeError, TypeError):
                                items = []
                        elif isinstance(meas.items, list):
                            items = meas.items
                        
                        # Filter by selected indices and add measurement metadata
                        for idx in selected_items:
                            if isinstance(idx, int) and 0 <= idx < len(items):
                                item_data = items[idx].copy()
                                item_data['_measurement_number'] = meas.measurement_number
                                item_data['_measurement_date'] = meas.measurement_date
                                measurement_items.append(item_data)
                except Exception as e:
                    print(f"Error loading measurement items: {e}")
        elif paper.measurement_id:
            # No selected items, load all items
            try:
                meas = db.query(DBMeasurement).filter(DBMeasurement.id == paper.measurement_id).first()
                if meas:
                    items = []
                    if isinstance(meas.items, str):
                        try:
                            items = json.loads(meas.items)
                        except (json.JSONDecodeError, TypeError):
                            items = []
                    elif isinstance(meas.items, list):
                        items = meas.items
                    # Add measurement metadata to all items
                    for item in items:
                        if isinstance(item, dict):
                            item['_measurement_number'] = meas.measurement_number
                            item['_measurement_date'] = meas.measurement_date
                    measurement_items = items
            except Exception as e:
                print(f"Error loading measurement items: {e}")
        
        # Add measurement type to paper_data for table header
        if paper.measurement_id:
            meas = db.query(DBMeasurement).filter(DBMeasurement.id == paper.measurement_id).first()
            if meas:
                paper_data['measurement'] = {'measurement_type': meas.measurement_type}
        
        # Generate PDF
        pdf_buffer = generate_production_paper_pdf(paper_data, measurement_items)
        
        # Return PDF as response
        return Response(
            content=pdf_buffer.read(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ProductionPaper-{paper.paper_number}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.put("/production-papers/{paper_id}", response_model=ProductionPaper)
def update_production_paper(
    *,
    db: Session = Depends(get_db),
    paper_id: int,
    paper_in: ProductionPaperCreate,
    current_user = Depends(get_production_manager)
) -> Any:
    """Update a production paper"""
    db_paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Production paper not found")
    
    # Prepare update data
    update_data = paper_in.model_dump(exclude_unset=True)
    
    # Handle selected_measurement_items conversion
    if 'selected_measurement_items' in update_data:
        if update_data['selected_measurement_items'] is not None:
            # Validate and convert to JSON string if measurement_id exists
            if update_data.get('measurement_id'):
                measurement = db.query(DBMeasurement).filter(DBMeasurement.id == update_data['measurement_id']).first()
                if measurement:
                    # Parse measurement items
                    items_data = measurement.items
                    if isinstance(items_data, str):
                        try:
                            items_data = json.loads(items_data)
                        except (json.JSONDecodeError, TypeError):
                            items_data = []
                    
                    if not isinstance(items_data, list):
                        items_data = []
                    
                    # Validate indices are within bounds
                    max_index = len(items_data) - 1
                    invalid_indices = [idx for idx in update_data['selected_measurement_items'] if idx < 0 or idx > max_index]
                    if invalid_indices:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid item indices: {invalid_indices}. Measurement has {len(items_data)} items (indices 0-{max_index})"
                        )
            
            # Convert list to JSON string for storage
            update_data['selected_measurement_items'] = json.dumps(update_data['selected_measurement_items'])
        else:
            update_data['selected_measurement_items'] = None
    
    # Update fields
    for field, value in update_data.items():
        setattr(db_paper, field, value)
    
    db.commit()
    db.refresh(db_paper)
    
    # Parse selected_measurement_items from JSON string to list for response
    selected_items = None
    if db_paper.selected_measurement_items:
        try:
            selected_items = json.loads(db_paper.selected_measurement_items)
        except (json.JSONDecodeError, TypeError):
            selected_items = None
    
    # Create response dict with parsed fields
    paper_dict = {
        'id': db_paper.id,
        'paper_number': db_paper.paper_number,
        'party_id': db_paper.party_id,
        'party_name': db_paper.party_name,
        'measurement_id': db_paper.measurement_id,
        'project_site_name': db_paper.project_site_name,
        'order_type': db_paper.order_type,
        'product_category': db_paper.product_category,
        'product_type': db_paper.product_type,
        'product_sub_type': db_paper.product_sub_type,
        'expected_dispatch_date': db_paper.expected_dispatch_date,
        'production_start_date': db_paper.production_start_date,
        'status': db_paper.status,
        'title': db_paper.title,
        'description': db_paper.description,
        'remarks': db_paper.remarks,
        'site_name': db_paper.site_name,
        'site_location': db_paper.site_location,
        'area': db_paper.area,
        'concept': db_paper.concept,
        'thickness': db_paper.thickness,
        'design': db_paper.design,
        'gel_colour': db_paper.gel_colour,
        'laminate': db_paper.laminate,
        'remark': db_paper.remark,
        'selected_measurement_items': selected_items,
        'created_by': db_paper.created_by,
        'created_at': db_paper.created_at,
        'updated_at': db_paper.updated_at,
    }
    
    return ProductionPaper(**paper_dict)


@router.delete("/production-papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_paper(
    *,
    db: Session = Depends(get_db),
    paper_id: int,
    delete_request: ProductionPaperDeleteRequest = Body(None),
    current_user = Depends(get_production_manager)
):
    """Soft delete a production paper with deletion reason"""
    try:
        db_paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == paper_id).first()
    except Exception as e:
        # If error is due to missing is_deleted column, use raw SQL to check if paper exists
        error_str = str(e).lower()
        if 'is_deleted' in error_str and ('does not exist' in error_str or 'undefinedcolumn' in error_str):
            db.rollback()
            from sqlalchemy import text
            result = db.execute(text("SELECT id FROM production_papers WHERE id = :paper_id"), {"paper_id": paper_id})
            row = result.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Production paper not found"
                )
            # Since is_deleted column doesn't exist, we can't do soft delete
            # For now, return an error asking to run migration
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Soft delete columns not found in database. Please run database migration to add is_deleted, deleted_at, and deletion_reason columns to production_papers table."
            )
        else:
            raise
    
    if not db_paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production paper not found"
        )
    
    # Try to use soft delete - the columns should exist if migration was run
    # If they don't exist, we'll catch the error and provide a helpful message
    try:
        # Check if already deleted
        if getattr(db_paper, 'is_deleted', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Production paper is already deleted"
            )
        
        # Soft delete with reason
        db_paper.is_deleted = True
        db_paper.deleted_at = func.now()
        db_paper.deletion_reason = delete_request.deletion_reason if delete_request and delete_request.deletion_reason else None
        db.commit()
    except AttributeError as e:
        # Column doesn't exist in the model or database
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Soft delete columns not found in database. Please run database migration: python migrate_add_soft_delete_production_papers.py"
        )
    except Exception as e:
        # Other database errors
        db.rollback()
        error_str = str(e).lower()
        if 'is_deleted' in error_str and ('does not exist' in error_str or 'undefinedcolumn' in error_str):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Soft delete columns not found in database. Please run database migration: python migrate_add_soft_delete_production_papers.py"
            )
        raise
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/production-papers/{paper_id}/recover", status_code=status.HTTP_200_OK)
def recover_production_paper(
    *,
    db: Session = Depends(get_db),
    paper_id: int,
    current_user = Depends(get_production_manager)
) -> Any:
    """Recover a soft-deleted production paper"""
    db_paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production paper not found"
        )
    
    if not getattr(db_paper, 'is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Production paper is not deleted"
        )
    
    # Recover the paper
    db_paper.is_deleted = False
    db_paper.deleted_at = None
    db_paper.deletion_reason = None
    db.commit()
    
    return {"message": "Production paper recovered successfully", "id": db_paper.id}

