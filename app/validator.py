import re
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator, model_validator

class CleanedOrder(BaseModel):
    order_id: str
    customer_name: str
    customer_email: str
    product_name: str
    price: float
    quantity: int
    total_amount: float
    order_date: datetime
    status: str

    @field_validator("order_id", mode="before")
    @classmethod
    def clean_order_id(cls, v):
        if v is None or not str(v).strip():
            raise ValueError("Order ID cannot be null or empty")
        return str(v).strip()

    @field_validator("customer_name", mode="before")
    @classmethod
    def clean_name(cls, v):
        if v is None:
            raise ValueError("Customer name cannot be null")
        s = str(v).strip()
        if not s:
            raise ValueError("Customer name cannot be empty")
        return s.title()

    @field_validator("customer_email", mode="before")
    @classmethod
    def clean_email(cls, v):
        if v is None:
            raise ValueError("Customer email cannot be null")
        s = str(v).strip().lower()
        # Basic but standard email format check
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, s):
            raise ValueError(f"Invalid email format: '{v}'")
        return s

    @field_validator("product_name", mode="before")
    @classmethod
    def clean_product(cls, v):
        if v is None or not str(v).strip():
            return "Unknown Product"
        return str(v).strip()

    @field_validator("price", mode="before")
    @classmethod
    def clean_price(cls, v):
        if v is None:
            raise ValueError("Price cannot be null")
        if isinstance(v, str):
            # Clean string price like "$123.45" or "45.00USD" or " 12,34 "
            cleaned = re.sub(r"[^\d.-]", "", v)
            try:
                val = float(cleaned)
            except ValueError:
                raise ValueError(f"Cannot parse price from string: '{v}'")
        else:
            val = float(v)
        if val <= 0:
            raise ValueError("Price must be greater than zero")
        return val

    @field_validator("quantity", mode="before")
    @classmethod
    def clean_quantity(cls, v):
        if v is None:
            raise ValueError("Quantity cannot be null")
        try:
            # Handle float values represented as strings, e.g., "2.0"
            val = int(float(str(v).strip()))
        except ValueError:
            raise ValueError(f"Cannot parse quantity from value: '{v}'")
        if val <= 0:
            raise ValueError("Quantity must be greater than zero")
        return val

    @field_validator("order_date", mode="before")
    @classmethod
    def clean_date(cls, v):
        if v is None:
            raise ValueError("Order date cannot be null")
        try:
            if isinstance(v, str):
                # ISO datetime parser
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            elif isinstance(v, datetime):
                dt = v
            else:
                raise ValueError()
        except Exception:
            raise ValueError(f"Invalid datetime format: '{v}'")
        
        # Check if in future (allow a small 10s buffer for server delays)
        if dt > datetime.now() + timedelta(seconds=10):
            raise ValueError("Order date cannot be in the future")
        return dt

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, v):
        if v is None:
            return "PENDING"
        s = str(v).strip().upper()
        if s not in {"COMPLETED", "PENDING", "CANCELLED"}:
            return "PENDING"
        return s

    @model_validator(mode="after")
    def recalculate_total(self) -> "CleanedOrder":
        # Calculate expected total
        expected_total = round(self.price * self.quantity, 2)
        # Enforce consistency and auto-correct totals if minor rounding issues or mismatch errors exist
        self.total_amount = expected_total
        return self
