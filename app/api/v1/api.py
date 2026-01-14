from fastapi import APIRouter

from app.api.v1.endpoints import auth, production, admin, raw_material, scheduler, supervisor, products, quality_check, billing, dispatch, logistics, accounts, sales, site_supervisor, carpenter, purchase, measurement_captain

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(production.router, prefix="/production", tags=["production-docs"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(raw_material.router, prefix="/raw-material", tags=["raw-material"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["production-scheduler"])
api_router.include_router(supervisor.router, prefix="/supervisor", tags=["production-supervisor"])
api_router.include_router(site_supervisor.router, prefix="/site-supervisor", tags=["site-supervisor"])
api_router.include_router(products.router, prefix="/production", tags=["products"])
api_router.include_router(quality_check.router, prefix="/quality-check", tags=["quality-check"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(dispatch.router, prefix="/dispatch", tags=["dispatch"])
api_router.include_router(logistics.router, prefix="/logistics", tags=["logistics"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(sales.router, prefix="/sales", tags=["sales-marketing"])
api_router.include_router(carpenter.router, prefix="/carpenter", tags=["carpenter-captain"])
api_router.include_router(purchase.router, prefix="/purchase", tags=["purchase-management"])
api_router.include_router(measurement_captain.router, prefix="/measurement-captain", tags=["measurement-captain"])
