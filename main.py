import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Product, Order, CartItem, PaymentPlan

app = FastAPI(title="SA Fashion Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "SA Fashion Store Backend Running"}

@app.get("/test")
def test_database():
    """Simple DB connectivity test"""
    resp = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "collections": []
    }
    try:
        if db is not None:
            resp["database"] = "✅ Connected"
            try:
                resp["collections"] = db.list_collection_names()
            except Exception as e:
                resp["database"] = f"⚠️ Connected but {str(e)[:60]}"
    except Exception as e:
        resp["database"] = f"❌ {str(e)[:60]}"
    return resp

# ---------------------- Products ----------------------
@app.get("/api/products", response_model=List[dict])
def list_products(q: Optional[str] = Query(None), category: Optional[str] = Query(None)):
    filt = {}
    if category:
        filt["category"] = category
    if q:
        # Simple case-insensitive text search
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"brand": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    docs = get_documents("product", filt) if db is not None else []
    # If no products exist, seed a few demo ones (only if DB is connected)
    if db is not None and not docs:
        demo_items: List[Product] = [
            Product(
                title="Classic SA Hoodie",
                brand="Mzansi Threads",
                description="Heavyweight fleece with bold embroidery.",
                category="clothing",
                price_zar=799,
                images=["https://images.unsplash.com/photo-1541099649105-f69ad21f3246?q=80&w=1200&auto=format&fit=crop"],
                sizes=["S","M","L","XL"],
            ),
            Product(
                title="Street Runner V2",
                brand="Joburg Kicks",
                description="Lightweight, everyday sneaker.",
                category="shoes",
                price_zar=1299,
                images=["https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1200&auto=format&fit=crop"],
                sizes=["6","7","8","9","10"],
            ),
            Product(
                title="Signature Tee",
                brand="Cape Co.",
                description="Premium cotton tee with oversized fit.",
                category="clothing",
                price_zar=349,
                images=["https://images.unsplash.com/photo-1520975867597-0af37a22e31b?q=80&w=1200&auto=format&fit=crop"],
                sizes=["S","M","L","XL"],
            ),
        ]
        for item in demo_items:
            create_document("product", item)
        docs = get_documents("product")
    # Normalize id
    out = []
    for d in docs:
        d["id"] = str(d.get("_id"))
        out.append({k: v for k, v in d.items() if k != "_id"})
    return out

# ---------------------- Checkout / Orders ----------------------
class CheckoutRequest(BaseModel):
    items: List[CartItem]
    payment_plan: PaymentPlan
    customer_name: str
    email: str
    address: str

@app.post("/api/checkout")
def checkout(payload: CheckoutRequest):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    subtotal = sum(i.price_zar * i.quantity for i in payload.items)
    shipping = 80.0 if subtotal < 1000 else 0.0  # simple rule: free shipping over R1000

    # Payment plan calculation
    if payload.payment_plan.plan_type == "3_month":
        deposit_percent = payload.payment_plan.deposit_percent or 20
        deposit = round(subtotal * deposit_percent / 100, 2)
        remaining = subtotal - deposit
        months = 3
        monthly_amount = round(remaining / months, 2)
        plan = PaymentPlan(
            plan_type="3_month",
            deposit_percent=deposit_percent,
            months=months,
            monthly_amount=monthly_amount,
        )
    else:
        plan = PaymentPlan(plan_type="once_off", deposit_percent=0, months=1, monthly_amount=0)

    total = round(subtotal + shipping, 2)

    order = Order(
        customer_name=payload.customer_name,
        email=payload.email,
        address=payload.address,
        items=payload.items,
        subtotal_zar=round(subtotal, 2),
        shipping_zar=round(shipping, 2),
        total_zar=total,
        payment_plan=plan,
        status="pending",
    )

    # Store order
    order_id = create_document("order", order) if db is not None else None

    return {
        "order_id": order_id,
        "summary": {
            "subtotal_zar": order.subtotal_zar,
            "shipping_zar": order.shipping_zar,
            "total_zar": order.total_zar,
            "payment_plan": plan.model_dump(),
        },
        "status": "pending",
        "message": "Order created. Proceed to payment.",
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
