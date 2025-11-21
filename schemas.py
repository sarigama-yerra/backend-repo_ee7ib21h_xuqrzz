"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Class name lowercased = collection name.

This project stores South African clothing and shoes products and creates
checkout orders with optional payment plans.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr

# Collections

class Product(BaseModel):
    """
    Collection: "product"
    Represents clothing and shoe items sold in ZAR.
    """
    title: str = Field(..., description="Product title")
    brand: Optional[str] = Field(None, description="Brand name")
    description: Optional[str] = Field(None, description="Product description")
    category: Literal["clothing", "shoes", "accessories"] = Field(
        ..., description="Primary category"
    )
    price_zar: float = Field(..., ge=0, description="Price in South African Rand")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    sizes: List[str] = Field(default_factory=list, description="Available sizes")
    in_stock: bool = Field(True, description="Is available for purchase")


# Embedded models (not collections on their own)
class CartItem(BaseModel):
    product_id: str
    title: str
    price_zar: float
    quantity: int = Field(1, ge=1)
    size: Optional[str] = None
    image: Optional[str] = None

class PaymentPlan(BaseModel):
    plan_type: Literal["once_off", "3_month"] = "once_off"
    deposit_percent: int = Field(0, ge=0, le=100)
    months: int = 1
    monthly_amount: float = 0.0

class Order(BaseModel):
    """
    Collection: "order"
    Customer checkout orders with optional payment plans.
    """
    customer_name: str
    email: EmailStr
    address: str
    items: List[CartItem]
    subtotal_zar: float
    shipping_zar: float
    total_zar: float
    currency: Literal["ZAR"] = "ZAR"
    payment_plan: PaymentPlan
    status: Literal["pending", "paid", "processing", "cancelled"] = "pending"
