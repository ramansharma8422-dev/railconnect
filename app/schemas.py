from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class SignupIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)

class StationIn(BaseModel):
    code: str = Field(min_length=2, max_length=10)
    name: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)

class TrainIn(BaseModel):
    train_number: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=100)
    origin_station_id: int
    destination_station_id: int
    departure_time: str
    arrival_time: str
    fare: float = Field(gt=0)
    total_seats: int = Field(gt=0, le=1000)

class TrainUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    departure_time: str | None = None
    arrival_time: str | None = None
    fare: float | None = Field(default=None, gt=0)
    total_seats: int | None = Field(default=None, gt=0, le=1000)
    is_active: bool | None = None

class BookingIn(BaseModel):
    train_id: int
    journey_date: date
    seats: int = Field(default=1, ge=1, le=6)

class BookingOut(BaseModel):
    id: int
    pnr: str
    user_id: int
    train_id: int
    journey_date: date
    seats: int
    total_fare: float
    status: str
    payment_status: str
    created_at: datetime
    cancelled_at: datetime | None
    model_config = ConfigDict(from_attributes=True)
