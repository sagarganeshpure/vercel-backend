from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class CheckStatus(str, enum.Enum):
    PENDING = "pending"
    WORK_IN_PROGRESS = "work_in_progress"
    APPROVED = "approved"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ORDERED = "ordered"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RawMaterialCategory(Base):
    __tablename__ = "raw_material_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)  # e.g., "Wood", "Hardware", "Laminate"
    code = Column(String, unique=True, index=True, nullable=True)  # Auto-generated category code like "CAT001"
    description = Column(Text, nullable=True)  # Description of the category
    is_active = Column(Boolean, default=True, nullable=False)  # Active/inactive status
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    raw_material_checks = relationship("RawMaterialCheck", back_populates="category")
    orders = relationship("Order", back_populates="category")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    code = Column(String, unique=True, index=True, nullable=True)  # Supplier code like "SUP001"
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pin_code = Column(String, nullable=True)
    gstin_number = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    credit_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    raw_material_checks = relationship("RawMaterialCheck", back_populates="supplier")
    orders = relationship("Order", back_populates="supplier")
    product_mappings = relationship("ProductSupplierMapping", back_populates="supplier")


class RawMaterialCheck(Base):
    __tablename__ = "raw_material_checks"

    id = Column(Integer, primary_key=True, index=True)
    check_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated like "RMC001"
    production_paper_id = Column(Integer, ForeignKey("production_papers.id"), nullable=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("raw_material_categories.id"), nullable=True, index=True)
    product_name = Column(String, nullable=False)  # e.g., "Flush Door"
    quantity = Column(Float, nullable=False)
    unit = Column(String, default="pcs", nullable=False)  # pcs, kg, m, etc.
    status = Column(String, default="pending", nullable=False)  # pending, work_in_progress, approved
    checked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    production_paper = relationship("ProductionPaper")
    party = relationship("Party")
    supplier = relationship("Supplier", back_populates="raw_material_checks")
    category = relationship("RawMaterialCategory", back_populates="raw_material_checks")
    checker_user = relationship("User", foreign_keys=[checked_by])
    approver_user = relationship("User", foreign_keys=[approved_by])


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)  # Auto-generated like "ORD001"
    raw_material_check_id = Column(Integer, ForeignKey("raw_material_checks.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("raw_material_categories.id"), nullable=True, index=True)
    product_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, default="pcs", nullable=False)
    unit_price = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, ordered, in_transit, delivered, completed, cancelled
    order_date = Column(DateTime(timezone=True), nullable=True)
    expected_delivery_date = Column(DateTime(timezone=True), nullable=True)
    actual_delivery_date = Column(DateTime(timezone=True), nullable=True)
    invoice_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    raw_material_check = relationship("RawMaterialCheck")
    supplier = relationship("Supplier", back_populates="orders")
    category = relationship("RawMaterialCategory", back_populates="orders")


class ProductSupplierMapping(Base):
    __tablename__ = "product_supplier_mappings"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False, index=True)  # e.g., "Flush Door"
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # 1 = primary, 2 = secondary, etc.
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    supplier = relationship("Supplier", back_populates="product_mappings")

