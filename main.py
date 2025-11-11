import os
import hmac
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import Product, Order, Shipment
import requests
from bson import ObjectId

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

app = FastAPI(title="Luxury Perfume Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "service": "perfume-store-api"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# ---------- Products ----------
@app.post("/api/products")
def create_product(product: Product):
    try:
        _id = create_document("product", product)
        return {"_id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products")
def list_products(limit: Optional[int] = 50):
    try:
        items = get_documents("product", {}, limit)
        for i in items:
            i["_id"] = str(i.get("_id"))
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Orders + Razorpay ----------
class CreateOrderPayload(BaseModel):
    order: Order

@app.post("/api/orders")
def create_order(payload: CreateOrderPayload):
    order = payload.order
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        # Allow creation without payment intent for demo
        try:
            _id = create_document("order", order)
            return {"order_id": _id, "razorpay": "not_configured"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Create Razorpay order
    try:
        amount_paise = int(order.total_amount * 100)
        r = requests.post(
            "https://api.razorpay.com/v1/orders",
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
            json={
                "amount": amount_paise,
                "currency": order.currency,
                "receipt": "rcpt_" + os.urandom(4).hex(),
                "payment_capture": 1
            },
            timeout=15
        )
        if r.status_code >= 300:
            raise HTTPException(status_code=502, detail=r.text)
        data = r.json()
        order.razorpay_order_id = data.get("id")
        _id = create_document("order", order)
        return {"order_id": _id, "razorpay_order_id": order.razorpay_order_id, "amount": amount_paise}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@app.post("/api/orders/verify")
def verify_payment(body: PaymentVerification):
    if not RAZORPAY_KEY_SECRET:
        return {"status": "skipped", "reason": "Razorpay not configured"}
    try:
        generated_signature = hmac.new(
            bytes(RAZORPAY_KEY_SECRET, 'utf-8'),
            msg=bytes(body.razorpay_order_id + '|' + body.razorpay_payment_id, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        if generated_signature == body.razorpay_signature:
            db["order"].update_one({"razorpay_order_id": body.razorpay_order_id}, {"$set": {"status": "paid"}})
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- POS / Order Management ----------
class UpdateOrderStatus(BaseModel):
    status: str

@app.get("/api/orders")
def list_orders(limit: Optional[int] = 100):
    try:
        items = get_documents("order", {}, limit)
        for i in items:
            i["_id"] = str(i.get("_id"))
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/orders/{order_id}/status")
def update_order_status(order_id: str, body: UpdateOrderStatus):
    try:
        db["order"].update_one({"_id": ObjectId(order_id)}, {"$set": {"status": body.status}})
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Shipments (Delivery Partners integration placeholders) ----------
class CreateShipmentPayload(BaseModel):
    order_id: str
    provider: str

@app.post("/api/shipments")
def create_shipment(payload: CreateShipmentPayload):
    try:
        shipment = Shipment(order_id=payload.order_id, provider=payload.provider)
        _id = create_document("shipment", shipment)
        return {"shipment_id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/shipments")
def list_shipments(limit: Optional[int] = 100):
    try:
        items = get_documents("shipment", {}, limit)
        for i in items:
            i["_id"] = str(i.get("_id"))
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
