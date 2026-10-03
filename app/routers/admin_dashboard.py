from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..admin_common import render_admin
from ..auth import require_admin
from ..db import get_db
from ..models_db import Brand, Category, Product

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get("")
@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    total_products = db.query(func.count(Product.id)).scalar()
    new_arrivals = db.query(func.count(Product.id)).filter(Product.is_new.is_(True)).scalar()
    featured = db.query(func.count(Product.id)).filter(Product.is_featured.is_(True)).scalar()
    out_of_stock = db.query(func.count(Product.id)).filter(Product.in_stock.is_(False)).scalar()
    unpublished = db.query(func.count(Product.id)).filter(Product.published.is_(False)).scalar()
    categories = db.query(func.count(Category.id)).scalar()
    brands = db.query(func.count(Brand.id)).scalar()

    recent_products = (
        db.query(Product).order_by(Product.updated_at.desc()).limit(6).all()
    )

    return render_admin(request, "dashboard.html", {
        "stats": {
            "total_products": total_products,
            "new_arrivals": new_arrivals,
            "featured": featured,
            "out_of_stock": out_of_stock,
            "unpublished": unpublished,
            "categories": categories,
            "brands": brands,
        },
        "recent_products": recent_products,
        "admin_user": session.user,
    }, session=session)
