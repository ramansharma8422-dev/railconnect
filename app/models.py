from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    full_name: str
    password_hash: str
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Station(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    city: str

class Train(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    train_number: str = Field(index=True, unique=True)
    name: str
    origin_station_id: int = Field(foreign_key="station.id", index=True)
    destination_station_id: int = Field(foreign_key="station.id", index=True)
    departure_time: str
    arrival_time: str
    fare: float = Field(gt=0)
    total_seats: int = Field(gt=0)
    available_seats: int = Field(ge=0)
    is_active: bool = True

class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pnr: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    train_id: int = Field(foreign_key="train.id", index=True)
    journey_date: date
    seats: int = Field(gt=0)
    total_fare: float
    status: str = "CONFIRMED"
    payment_status: str = "SIMULATED_SUCCESS"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    cancelled_at: Optional[datetime] = None

class RevokedToken(SQLModel, table=True):
    jti: str = Field(primary_key=True)
    expires_at: datetime

class PasswordReset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    expires_at: datetime
    used: bool = False
