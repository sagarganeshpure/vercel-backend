from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from app.db.base import Base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Initialize database by creating all tables.
    This function imports all models to ensure they are registered with SQLAlchemy.
    """
    try:
        # Import all models here to ensure they are registered with SQLAlchemy
        # This ensures all tables are created when init_db() is called
        from app.db.models.user import (
            User, Measurement, Party, ProductionPaper, ProductionSchedule,
            Product, Department, ProductionSupervisor, ProductionTask,
            ProductionIssue, TaskProgress, ProductionTracking,
            MeasurementTask, MeasurementEntry, ManufacturingStage, Design
        )
        from app.db.models.raw_material import Supplier, RawMaterialCheck, Order, ProductSupplierMapping
        from app.db.models.quality_check import QualityCheck, ReworkJob, QCCertificate
        from app.db.models.billing import BillingRequest, DeliveryChallan, TaxInvoice, TallySync
        from app.db.models.dispatch import Dispatch, DispatchItem, GatePass, DeliveryTracking
        from app.db.models.logistics import Vehicle, Driver, LogisticsAssignment, DeliveryIssue
        from app.db.models.accounts import (
            PaymentReceipt, PaymentAllocation, AccountReceivable, AccountReconciliation,
            VendorPayable, VendorPayment, Ledger, LedgerEntry,
            Contractor, ContractorWorkOrder, ContractorOutput, ContractorPayment,
            OrderCosting, CreditControl
        )
        from app.db.models.sales import Lead, SiteProject, Quotation, SalesOrder, MeasurementRequest, FollowUp
        from app.db.models.site_supervisor import (
            Site, Flat, SiteMeasurement, FrameFixing, DoorFixing, 
            DailySiteProgress, SiteIssue, SitePhoto
        )
        from app.db.models.carpenter import (
            CarpenterCaptain, WorkAllocation, CarpenterFrameFixing,
            CarpenterDoorFixing, CarpenterAttendance, CarpenterIssue, WorkCompletion
        )
        from app.db.models.purchase import (
            Vendor, BOM, PurchaseRequisition, PurchaseOrder, GRN, PurchaseReturn, VendorBill
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Database error during initialization: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {str(e)}", exc_info=True)
        raise
