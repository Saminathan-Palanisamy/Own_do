from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import jwt
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from models import models
from core.database import get_db
from fastapi.responses import JSONResponse
import uuid
from fastapi import Request
from enum import Enum
from models.models import Cart


PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 2))




def hash_password(password: str) -> str:
    return PWD_CONTEXT.hash(password)




def verify_password(plain: str, hashed: str) -> bool:
    return PWD_CONTEXT.verify(plain, hashed)




def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token




def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token




def decode_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload

#for get current user
bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials  # extract actual JWT

    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    #---------
async def optional_current_user(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")


    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "").strip()

    try:
        payload = decode_token(token)
        return payload
    except Exception:
        return None
#----------------------------------
def initialize_session(user_id: int, user_payload: dict, request: Request, db: Session):
    try:

        session_uid = str(uuid.uuid4())
 
        access_payload = user_payload.copy()
        access_payload.update({"user_id": user_id, "session_id": session_uid})

        access_token = create_access_token(access_payload)


        new_session = models.LoginSession(
            session_id=session_uid,
            user_id=user_id,
            auth_token=access_token,
            login_time=datetime.utcnow(),
            logout_time=datetime.utcnow() + timedelta(days=2),
            is_active=True
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        return session_uid, access_token
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session creation failed.")

# Refresh endpoint logic: validate refresh token.
def refresh_session(session_id: str, db: Session):
    try:
        session = (db.query(models.LoginSession).filter(models.LoginSession.session_id == session_id,models.LoginSession.is_active == True)
            .first())

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.logout_time < datetime.now(timezone.utc):
            db.commit()
            raise HTTPException(status_code=401, detail="Session expired")
        user = db.query(models.User).filter(models.User.id == session.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "session_id": session.session_id
        }

        new_access_token = create_access_token(new_payload)

        session.auth_token = new_access_token
        db.commit()
        db.refresh(session)

        return {
            "session_id": session.session_id,
            "access_token": new_access_token,
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="refresh failed.")


#----------------------------------------------------------------------------
# for cart
def get_or_create_cart(user_id: int, db: Session):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart
#---------------------------------------------------------------------------