from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.config import settings
from app.db.base import Base
# Import all models to ensure they are registered with SQLAlchemy
from app.db.models.user import (
    User, Measurement, Party, ProductionPaper, ProductionSchedule,
    Product, Department, ProductionSupervisor, ProductionTask,
    ProductionIssue, TaskProgress, ProductionTracking, ManufacturingStage, Design
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

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": settings.DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
