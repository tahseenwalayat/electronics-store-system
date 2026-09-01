"""
Customer and Supplier Domain Models.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Customer:
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    loyalty_points: int = 0
    credit_limit: float = 0.0
    current_balance: float = 0.0
    is_active: bool = True
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Supplier:
    id: int
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_number: Optional[str] = None
    current_balance: float = 0.0
    is_active: bool = True
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
