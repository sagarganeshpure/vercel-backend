from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from datetime import datetime
import re

from app.schemas.user import (
    QualityCheck, QualityCheckCreate, QualityCheckUpdate,
    ReworkJob, ReworkJobCreate, ReworkJobUpdate,
    QCCertificate, QCCertificateCreate
)
from app.db.models.quality_check import (
    QualityCheck as DBQualityCheck,
    ReworkJob as DBReworkJob,
    QCCertificate as DBQCCertificate
)
from app.db.models.user import ProductionPaper as DBProductionPaper, ProductionTracking as DBProductionTracking
from app.api.deps import get_db, get_quality_checker

router = APIRouter()


def generate_next_qc_number(db: Session) -> str:
    """Generate the next QC number in format QC001, QC002, etc."""
    qcs = db.query(DBQualityCheck.qc_number).filter(
        DBQualityCheck.qc_number.like('QC%')
    ).all()
    
    max_num = 0
    for qc in qcs:
        if qc.qc_number:
            match = re.match(r'QC(\d+)', qc.qc_number)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    
    next_num = max_num + 1
    return f"QC{next_num:03d}"


def generate_next_rework_number(db: Session) -> str:
    """Generate the next rework number in format RW001, RW002, etc."""
    reworks = db.query(DBReworkJob.rework_number).filter(
        DBReworkJob.rework_number.like('RW%')
    ).all()
    
    max_num = 0
    for rework in reworks:
        if rework.rework_number:
            match = re.match(r'RW(\d+)', rework.rework_number)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    
    next_num = max_num + 1
    return f"RW{next_num:03d}"


def generate_next_certificate_number(db: Session) -> str:
    """Generate the next certificate number in format QCCERT001, QCCERT002, etc."""
    certs = db.query(DBQCCertificate.certificate_number).filter(
        DBQCCertificate.certificate_number.like('QCCERT%')
    ).all()
    
    max_num = 0
    for cert in certs:
        if cert.certificate_number:
            match = re.match(r'QCCERT(\d+)', cert.certificate_number)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    
    next_num = max_num + 1
    return f"QCCERT{next_num:03d}"


@router.get("/pending-for-qc", response_model=List[Any])
def get_pending_for_qc(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get production papers that are completed and pending QC"""
    # Get production papers with status "completed" or "in_production" where all stages are completed
    papers = db.query(DBProductionPaper).filter(
        DBProductionPaper.status.in_(["in_production", "completed"])
    ).offset(skip).limit(limit).all()
    
    result = []
    for paper in papers:
        # Check if all production tracking stages are completed
        tracking_stages = db.query(DBProductionTracking).filter(
            DBProductionTracking.production_paper_id == paper.id
        ).all()
        
        if not tracking_stages:
            continue
        
        all_completed = all(stage.status == "Completed" for stage in tracking_stages)
        
        # Check if QC already exists
        existing_qc = db.query(DBQualityCheck).filter(
            DBQualityCheck.production_paper_id == paper.id,
            DBQualityCheck.qc_status.in_(["pending", "approved"])
        ).first()
        
        if all_completed and not existing_qc:
            # Get supervisor info from latest tracking
            latest_tracking = max(tracking_stages, key=lambda x: x.end_date_time or datetime.min)
            
            result.append({
                "production_paper_id": paper.id,
                "production_paper_number": paper.paper_number,
                "party_name": paper.party_name,
                "product_type": paper.product_category,
                "product_variant": paper.product_sub_type,
                "quantity": 1,  # Default, should be calculated from measurement
                "order_type": paper.order_type,
                "production_completed_date": latest_tracking.end_date_time if latest_tracking.end_date_time else None,
                "supervisor_name": latest_tracking.supervisor_name,
                "status": "Pending QC"
            })
    
    return result


@router.get("/qc-queue", response_model=List[Any])
def get_qc_queue(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get QC queue - pending QC items"""
    query = db.query(DBQualityCheck)
    
    if status_filter:
        query = query.filter(DBQualityCheck.qc_status == status_filter)
    else:
        query = query.filter(DBQualityCheck.qc_status == "pending")
    
    qcs = query.offset(skip).limit(limit).all()
    
    result = []
    for qc in qcs:
        paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == qc.production_paper_id).first()
        result.append({
            "id": qc.id,
            "qc_number": qc.qc_number,
            "production_paper_number": qc.production_paper_number,
            "party_name": qc.party_name,
            "product_type": qc.product_type,
            "product_variant": qc.product_variant,
            "quantity": qc.total_quantity,
            "order_type": qc.order_type,
            "production_completed_date": qc.production_completed_date,
            "status": qc.qc_status
        })
    
    return result


@router.get("/qc-number/next")
def get_next_qc_number(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker)
) -> Any:
    """Get the next QC number"""
    next_number = generate_next_qc_number(db)
    return {"qc_number": next_number}


@router.post("/quality-checks", response_model=QualityCheck, status_code=status.HTTP_201_CREATED)
def create_quality_check(
    *,
    db: Session = Depends(get_db),
    qc_in: QualityCheckCreate,
    current_user = Depends(get_quality_checker)
) -> Any:
    """Create a new quality check"""
    # Verify production paper exists
    paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == qc_in.production_paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production paper not found"
        )
    
    qc_data = qc_in.model_dump()
    
    # Auto-generate QC number if not provided
    if not qc_data.get('qc_number'):
        qc_data['qc_number'] = generate_next_qc_number(db)
    
    # Set inspector info
    qc_data['inspector_id'] = current_user.id
    qc_data['inspector_name'] = current_user.username
    qc_data['inspection_date'] = datetime.now()
    
    # Get production paper details
    if not qc_data.get('production_paper_number'):
        qc_data['production_paper_number'] = paper.paper_number
    if not qc_data.get('party_name'):
        qc_data['party_name'] = paper.party_name
    if not qc_data.get('party_id'):
        qc_data['party_id'] = paper.party_id
    
    db_qc = DBQualityCheck(
        **qc_data,
        created_by=current_user.id
    )
    db.add(db_qc)
    db.commit()
    db.refresh(db_qc)
    
    return db_qc


@router.get("/quality-checks", response_model=List[QualityCheck])
def get_quality_checks(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all quality checks, optionally filtered by status"""
    query = db.query(DBQualityCheck)
    
    if status_filter:
        query = query.filter(DBQualityCheck.qc_status == status_filter)
    
    qcs = query.order_by(DBQualityCheck.created_at.desc()).offset(skip).limit(limit).all()
    return qcs


@router.get("/quality-checks/{qc_id}", response_model=QualityCheck)
def get_quality_check(
    qc_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker)
) -> Any:
    """Get a specific quality check"""
    qc = db.query(DBQualityCheck).filter(DBQualityCheck.id == qc_id).first()
    if not qc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality check not found"
        )
    return qc


@router.put("/quality-checks/{qc_id}", response_model=QualityCheck)
def update_quality_check(
    qc_id: int,
    *,
    db: Session = Depends(get_db),
    qc_update: QualityCheckUpdate,
    current_user = Depends(get_quality_checker)
) -> Any:
    """Update a quality check"""
    qc = db.query(DBQualityCheck).filter(DBQualityCheck.id == qc_id).first()
    if not qc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality check not found"
        )
    
    update_data = qc_update.model_dump(exclude_unset=True)
    
    # Update inspector info if status is being changed
    if 'qc_status' in update_data and update_data['qc_status'] in ['approved', 'rework_required', 'rejected']:
        update_data['inspector_id'] = current_user.id
        update_data['inspector_name'] = current_user.username
        update_data['inspection_date'] = datetime.now()
    
    # Update production paper status if approved
    if update_data.get('qc_status') == 'approved':
        paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == qc.production_paper_id).first()
        if paper:
            paper.status = "ready_for_dispatch"
            db.commit()
    
    for field, value in update_data.items():
        setattr(qc, field, value)
    
    db.commit()
    db.refresh(qc)
    
    return qc


@router.post("/quality-checks/{qc_id}/approve", response_model=QualityCheck)
def approve_quality_check(
    qc_id: int,
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker)
) -> Any:
    """Approve a quality check"""
    qc = db.query(DBQualityCheck).filter(DBQualityCheck.id == qc_id).first()
    if not qc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality check not found"
        )
    
    qc.qc_status = "approved"
    qc.inspector_id = current_user.id
    qc.inspector_name = current_user.username
    qc.inspection_date = datetime.now()
    
    # Update production paper status
    paper = db.query(DBProductionPaper).filter(DBProductionPaper.id == qc.production_paper_id).first()
    if paper:
        paper.status = "ready_for_dispatch"
    
    db.commit()
    db.refresh(qc)
    
    return qc


@router.post("/quality-checks/{qc_id}/reject", response_model=QualityCheck)
def reject_quality_check(
    qc_id: int,
    *,
    db: Session = Depends(get_db),
    defect_category: Optional[str] = None,
    severity: Optional[str] = None,
    remarks: Optional[str] = None,
    current_user = Depends(get_quality_checker)
) -> Any:
    """Reject a quality check"""
    qc = db.query(DBQualityCheck).filter(DBQualityCheck.id == qc_id).first()
    if not qc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality check not found"
        )
    
    qc.qc_status = "rejected"
    qc.inspector_id = current_user.id
    qc.inspector_name = current_user.username
    qc.inspection_date = datetime.now()
    
    if defect_category:
        qc.defect_category = defect_category
    if severity:
        qc.severity = severity
    if remarks:
        qc.remarks = remarks
    
    db.commit()
    db.refresh(qc)
    
    return qc


@router.post("/rework-jobs", response_model=ReworkJob, status_code=status.HTTP_201_CREATED)
def create_rework_job(
    *,
    db: Session = Depends(get_db),
    rework_in: ReworkJobCreate,
    current_user = Depends(get_quality_checker)
) -> Any:
    """Create a rework job"""
    rework_data = rework_in.model_dump()
    
    # Auto-generate rework number if not provided
    if not rework_data.get('rework_number'):
        rework_data['rework_number'] = generate_next_rework_number(db)
    
    db_rework = DBReworkJob(
        **rework_data,
        created_by=current_user.id
    )
    db.add(db_rework)
    
    # Update QC status to rework_required
    qc = db.query(DBQualityCheck).filter(DBQualityCheck.id == rework_in.quality_check_id).first()
    if qc:
        qc.qc_status = "rework_required"
        qc.rework_job_id = db_rework.id
    
    db.commit()
    db.refresh(db_rework)
    
    return db_rework


@router.get("/rework-jobs", response_model=List[ReworkJob])
def get_rework_jobs(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all rework jobs"""
    query = db.query(DBReworkJob)
    
    if status_filter:
        query = query.filter(DBReworkJob.status == status_filter)
    
    reworks = query.order_by(DBReworkJob.created_at.desc()).offset(skip).limit(limit).all()
    return reworks


@router.get("/qc-history", response_model=List[QualityCheck])
def get_qc_history(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get QC history - all completed QC checks"""
    qcs = db.query(DBQualityCheck).filter(
        DBQualityCheck.qc_status.in_(["approved", "rejected", "rework_required"])
    ).order_by(DBQualityCheck.inspection_date.desc()).offset(skip).limit(limit).all()
    
    return qcs


@router.get("/qc-reports/stats")
def get_qc_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker)
) -> Any:
    """Get QC statistics for reports"""
    total_qcs = db.query(DBQualityCheck).count()
    approved_qcs = db.query(DBQualityCheck).filter(DBQualityCheck.qc_status == "approved").count()
    rejected_qcs = db.query(DBQualityCheck).filter(DBQualityCheck.qc_status == "rejected").count()
    rework_qcs = db.query(DBQualityCheck).filter(DBQualityCheck.qc_status == "rework_required").count()
    pending_qcs = db.query(DBQualityCheck).filter(DBQualityCheck.qc_status == "pending").count()
    
    pass_rate = (approved_qcs / total_qcs * 100) if total_qcs > 0 else 0
    
    return {
        "total_qcs": total_qcs,
        "approved": approved_qcs,
        "rejected": rejected_qcs,
        "rework_required": rework_qcs,
        "pending": pending_qcs,
        "pass_rate": round(pass_rate, 2)
    }


@router.post("/qc-certificates", response_model=QCCertificate, status_code=status.HTTP_201_CREATED)
def create_qc_certificate(
    *,
    db: Session = Depends(get_db),
    cert_in: QCCertificateCreate,
    current_user = Depends(get_quality_checker)
) -> Any:
    """Create a QC certificate"""
    cert_data = cert_in.model_dump()
    
    # Auto-generate certificate number if not provided
    if not cert_data.get('certificate_number'):
        cert_data['certificate_number'] = generate_next_certificate_number(db)
    
    db_cert = DBQCCertificate(**cert_data)
    db.add(db_cert)
    db.commit()
    db.refresh(db_cert)
    
    return db_cert


@router.get("/qc-certificates", response_model=List[QCCertificate])
def get_qc_certificates(
    db: Session = Depends(get_db),
    current_user = Depends(get_quality_checker),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all QC certificates"""
    certs = db.query(DBQCCertificate).order_by(DBQCCertificate.created_at.desc()).offset(skip).limit(limit).all()
    return certs

