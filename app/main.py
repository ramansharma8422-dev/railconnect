from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from jose import JWTError
from app.config import settings
from app.database import create_db_and_tables, get_session, engine
from app.models import User, Station, Train, Booking, RevokedToken, PasswordReset
from app.schemas import (SignupIn, LoginIn, UserOut, TokenOut, ForgotPasswordIn,
    ResetPasswordIn, StationIn, TrainIn, TrainUpdate, BookingIn, BookingOut)
from app.security import (hash_password, verify_password, create_access_token,
    decode_token, hash_reset_token, create_reset_token)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.email == settings.admin_email.lower())).first()
        if not admin:
            session.add(User(email=settings.admin_email.lower(), full_name="Railway Administrator",
                password_hash=hash_password(settings.admin_password), is_admin=True))
            session.commit()
    yield

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

def current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    unauthorized = HTTPException(status_code=401, detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_token(token)
        if payload.get("type") != "access" or not payload.get("sub") or not payload.get("jti"):
            raise unauthorized
        if session.get(RevokedToken, payload["jti"]):
            raise HTTPException(status_code=401, detail="Token has been logged out")
        user = session.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            raise unauthorized
        return user
    except (JWTError, ValueError, TypeError):
        raise unauthorized

def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user

@app.get("/")
def root():
    return {"message": "Mini Railway Booking API is running", "docs": "/docs"}

@app.post("/auth/signup", response_model=UserOut, status_code=201)
def signup(data: SignupIn, session: Session = Depends(get_session)):
    email = data.email.lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, full_name=data.full_name.strip(), password_hash=hash_password(data.password))
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    return user

@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email.lower())).first()
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token, _, _ = create_access_token(user.id)
    return TokenOut(access_token=token)

@app.post("/auth/logout")
def logout(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    try:
        payload = decode_token(token)
        if payload.get("type") != "access" or not payload.get("jti"):
            raise HTTPException(status_code=401, detail="Invalid token")
        if not session.get(RevokedToken, payload["jti"]):
            session.add(RevokedToken(jti=payload["jti"], expires_at=datetime.utcfromtimestamp(payload["exp"])))
            session.commit()
        return {"message": "Logged out; this access token has been revoked"}
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

@app.get("/users/me", response_model=UserOut)
def profile(user: User = Depends(current_user)):
    return user

@app.post("/auth/forgot-password")
def forgot_password(data: ForgotPasswordIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email.lower())).first()
    # Generic response avoids disclosing whether an email is registered.
    result = {"message": "If the account exists, reset instructions have been generated."}
    if user:
        raw = create_reset_token()
        session.add(PasswordReset(user_id=user.id, token_hash=hash_reset_token(raw),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.reset_token_expire_minutes)))
        session.commit()
        # Development-only email simulation. Do not log reset tokens in production.
        result["development_reset_token"] = raw
    return result

@app.post("/auth/reset-password")
def reset_password(data: ResetPasswordIn, session: Session = Depends(get_session)):
    hashed = hash_reset_token(data.token)
    reset = session.exec(select(PasswordReset).where(PasswordReset.token_hash == hashed)).first()
    if not reset or reset.used or reset.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token is invalid, expired, or already used")
    user = session.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Reset token is invalid")
    user.password_hash = hash_password(data.new_password)
    reset.used = True
    session.add(user)
    session.add(reset)
    session.commit()
    return {"message": "Password reset successfully"}

@app.post("/admin/stations", response_model=dict, status_code=201)
def add_station(data: StationIn, session: Session = Depends(get_session), _: User = Depends(admin_user)):
    station = Station(code=data.code.upper(), name=data.name.strip(), city=data.city.strip())
    session.add(station)
    try:
        session.commit()
        session.refresh(station)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Station code already exists")
    return {"id": station.id, "code": station.code, "name": station.name, "city": station.city}

@app.get("/stations")
def list_stations(session: Session = Depends(get_session)):
    return session.exec(select(Station).order_by(Station.name)).all()

@app.post("/admin/trains", status_code=201)
def add_train(data: TrainIn, session: Session = Depends(get_session), _: User = Depends(admin_user)):
    if data.origin_station_id == data.destination_station_id:
        raise HTTPException(status_code=422, detail="Origin and destination must be different")
    origin, dest = session.get(Station, data.origin_station_id), session.get(Station, data.destination_station_id)
    if not origin or not dest:
        raise HTTPException(status_code=404, detail="Origin or destination station not found")
    train = Train(**data.model_dump(), available_seats=data.total_seats)
    session.add(train)
    try:
        session.commit()
        session.refresh(train)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Train number already exists")
    return train

@app.patch("/admin/trains/{train_id}")
def update_train(train_id: int, data: TrainUpdate, session: Session = Depends(get_session), _: User = Depends(admin_user)):
    train = session.get(Train, train_id)
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    changes = data.model_dump(exclude_unset=True)
    if "total_seats" in changes:
        booked = train.total_seats - train.available_seats
        if changes["total_seats"] < booked:
            raise HTTPException(status_code=409, detail="Total seats cannot be lower than already booked seats")
        train.available_seats = changes["total_seats"] - booked
    for key, value in changes.items():
        setattr(train, key, value)
    session.add(train)
    session.commit()
    session.refresh(train)
    return train

@app.post("/admin/trains/{train_id}/deactivate")
def deactivate_train(train_id: int, session: Session = Depends(get_session), _: User = Depends(admin_user)):
    train = session.get(Train, train_id)
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    train.is_active = False
    session.add(train)
    session.commit()
    return {"message": "Train deactivated"}

@app.get("/trains/search")
def search_trains(origin: str, destination: str, journey_date: date, session: Session = Depends(get_session)):
    if origin.strip().lower() == destination.strip().lower():
        raise HTTPException(status_code=422, detail="Origin and destination must be different")
    start = session.exec(select(Station).where(
        (Station.code == origin.upper()) | (Station.name.ilike(origin.strip())) | (Station.city.ilike(origin.strip()))
    )).first()
    end = session.exec(select(Station).where(
        (Station.code == destination.upper()) | (Station.name.ilike(destination.strip())) | (Station.city.ilike(destination.strip()))
    )).first()
    if not start or not end:
        raise HTTPException(status_code=404, detail="Origin or destination station not found")
    trains = session.exec(select(Train).where(
        Train.origin_station_id == start.id,
        Train.destination_station_id == end.id,
        Train.is_active == True
    )).all()
    return [{
        "train_id": t.id, "train_number": t.train_number, "name": t.name,
        "origin": start.name, "destination": end.name, "journey_date": journey_date,
        "departure_time": t.departure_time, "arrival_time": t.arrival_time,
        "fare_per_seat": t.fare, "available_seats": t.available_seats
    } for t in trains]

@app.post("/bookings", response_model=BookingOut, status_code=201)
def book_ticket(data: BookingIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if data.journey_date < date.today():
        raise HTTPException(status_code=422, detail="Journey date cannot be in the past")
    train = session.get(Train, data.train_id)
    if not train or not train.is_active:
        raise HTTPException(status_code=404, detail="Active train not found")
    # Atomic conditional decrement prevents overselling when requests race.
    # SQLite serializes writes; the WHERE clause is the final seat-availability guard.
    result = session.exec(update(Train).where(
        Train.id == data.train_id, Train.is_active == True, Train.available_seats >= data.seats
    ).values(available_seats=Train.available_seats - data.seats))
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=409, detail="Not enough seats available")
    pnr = secrets.token_hex(5).upper()
    booking = Booking(pnr=pnr, user_id=user.id, train_id=train.id, journey_date=data.journey_date,
        seats=data.seats, total_fare=round(train.fare * data.seats, 2))
    session.add(booking)
    try:
        session.commit()
        session.refresh(booking)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Booking failed; please retry")
    return booking

@app.get("/bookings/me", response_model=list[BookingOut])
def my_bookings(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return session.exec(select(Booking).where(Booking.user_id == user.id).order_by(Booking.created_at.desc())).all()

@app.get("/bookings/{pnr}", response_model=BookingOut)
def booking_detail(pnr: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    booking = session.exec(select(Booking).where(Booking.pnr == pnr.upper(), Booking.user_id == user.id)).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.post("/bookings/{pnr}/cancel", response_model=BookingOut)
def cancel_booking(pnr: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    booking = session.exec(select(Booking).where(Booking.pnr == pnr.upper(), Booking.user_id == user.id)).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Booking is already cancelled")
    if booking.journey_date <= date.today():
        raise HTTPException(status_code=409, detail="Only future journeys can be cancelled")
    result = session.exec(update(Train).where(Train.id == booking.train_id).values(
        available_seats=Train.available_seats + booking.seats))
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=500, detail="Could not release seats")
    booking.status = "CANCELLED"
    booking.cancelled_at = datetime.utcnow()
    session.add(booking)
    session.commit()
    session.refresh(booking)
    return booking

@app.get("/health")
def health():
    return {"status": "ok"}
