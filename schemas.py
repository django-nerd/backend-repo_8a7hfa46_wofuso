"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from datetime import datetime

# Typography note: Schemas define data shape only.

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Address")
    phone: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Perfume products
    Collection name: "product"
    """
    title: str = Field(..., description="Product title")
    brand: Optional[str] = Field("", description="Brand name")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Base price in INR")
    images: List[HttpUrl] = Field(default_factory=list, description="Image URLs")
    notes_top: Optional[List[str]] = Field(default=None, description="Top notes")
    notes_heart: Optional[List[str]] = Field(default=None, description="Heart notes")
    notes_base: Optional[List[str]] = Field(default=None, description="Base notes")
    sizes_ml: List[int] = Field(default_factory=lambda: [50, 100], description="Available sizes in ml")
    sku: Optional[str] = Field(None, description="SKU code")
    in_stock: bool = Field(True, description="Stock availability")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Product _id as string")
    title: str = Field(..., description="Product title snapshot")
    size_ml: int = Field(..., description="Selected size in ml")
    price: float = Field(..., ge=0, description="Unit price at time of order")
    quantity: int = Field(..., ge=1, description="Quantity")

class Order(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str
    shipping_address: str
    items: List[OrderItem]
    subtotal: float = Field(..., ge=0)
    shipping_fee: float = Field(0, ge=0)
    total_amount: float = Field(..., ge=0)
    currency: Literal["INR"] = "INR"
    status: Literal["pending", "paid", "processing", "shipped", "delivered", "cancelled"] = "pending"
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Shipment(BaseModel):
    order_id: str
    provider: Literal["shiprocket", "delhivery", "bluedart", "xpressbees", "other"] = "other"
    tracking_id: Optional[str] = None
    status: Literal["created", "in_transit", "delivered", "failed"] = "created"
    meta: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# The Flames database viewer can read these at GET /schema if exposed by the backend.
