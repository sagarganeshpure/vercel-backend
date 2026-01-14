from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
from app.db.session import SessionLocal
from app.db.models.user import User as DBUser
from app.core import security


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> DBUser:
    """
    Get the current authenticated user from the JWT token.
    """
    try:
        token = credentials.credentials
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token. Please provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token. Please provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = security.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(DBUser).filter(DBUser.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an administrator.",
        )
    
    return user


def require_role(allowed_roles: List[str]):
    """
    Dependency factory to check if user has required role.
    """
    def role_checker(current_user: DBUser = Depends(get_current_user)) -> DBUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}. Your role: {current_user.role}"
            )
        return current_user
    return role_checker


# Common role dependencies
get_production_manager = require_role(["production_manager", "admin"])
get_production_manager_or_scheduler = require_role(["production_manager", "production_scheduler", "measurement_captain", "admin"])
get_raw_material_checker = require_role(["raw_material_checker", "admin"])
get_production_manager_or_raw_material_checker = require_role(["production_manager", "raw_material_checker", "admin"])
get_production_access = require_role(["production_manager", "production_scheduler", "measurement_captain", "raw_material_checker", "admin"])
get_production_scheduler = require_role(["production_scheduler", "admin"])
get_production_supervisor = require_role(["production_supervisor", "admin"])
get_quality_checker = require_role(["quality_checker", "admin"])
get_billing_executive = require_role(["billing_executive", "accounts_manager", "accounts_executive", "finance_head", "admin"])
get_accounts_manager = require_role(["accounts_manager", "finance_head", "admin"])
get_accounts_executive = require_role(["accounts_executive", "accounts_manager", "finance_head", "admin"])
get_finance_head = require_role(["finance_head", "admin"])
get_auditor = require_role(["auditor", "finance_head", "admin"])
get_accounts_user = require_role(["accounts_manager", "accounts_executive", "finance_head", "auditor", "admin"])
get_dispatch_executive = require_role(["dispatch_executive", "dispatch_supervisor", "logistics_manager", "admin"])
get_dispatch_supervisor = require_role(["dispatch_supervisor", "admin"])
get_logistics_manager = require_role(["logistics_manager", "admin"])
get_logistics_executive = require_role(["logistics_manager", "logistics_executive", "admin"])
get_driver = require_role(["driver", "logistics_manager", "logistics_executive", "admin"])
get_logistics_user = require_role(["logistics_manager", "logistics_executive", "driver", "admin"])
get_marketing_executive = require_role(["marketing_executive", "sales_executive", "sales_manager", "admin"])
get_sales_executive = require_role(["sales_executive", "sales_manager", "admin"])
get_sales_manager = require_role(["sales_manager", "admin"])
get_sales_user = require_role(["marketing_executive", "sales_executive", "sales_manager", "admin"])
get_site_supervisor = require_role(["site_supervisor", "admin"])
get_carpenter_captain = require_role(["carpenter_captain", "site_supervisor", "admin"])
get_purchase_executive = require_role(["purchase_executive", "purchase_manager", "admin"])
get_purchase_manager = require_role(["purchase_manager", "admin"])
get_store_incharge = require_role(["store_incharge", "admin"])
get_purchase_user = require_role(["purchase_executive", "purchase_manager", "store_incharge", "admin"])
get_measurement_captain = require_role(["measurement_captain", "admin"])
get_measurement_task_assigner = require_role(["site_supervisor", "marketing_executive", "sales_executive", "sales_manager", "admin"])
get_admin = require_role(["admin"])
