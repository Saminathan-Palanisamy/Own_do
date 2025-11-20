from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from core import database, secure
from typing import Optional
from models import models
from schemas import schemas
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid, jwt

router = APIRouter()

get_db = database.get_db




@router.post("/register", response_model=schemas.RegisterResponse)
def register(payload: schemas.RegisterRequest, db: Session = Depends(database.get_db)):
    try:
    
        existing = db.query(models.User).filter(models.User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        total_users = db.query(models.User).count()

        # Check if admin already exists
        admin_exists = db.query(models.User).filter(models.User.role == "admin").first()

        # Enforce first-user-must-be-admin rule
        if total_users == 0:
            if payload.role != schemas.UserRole.ADMIN:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="First user must be admin")
        else:
            if payload.role == schemas.UserRole.ADMIN:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only one admin allowed")

        user = models.User(
            username=payload.username,
            email=payload.email,
            hashed_password=secure.hash_password(payload.password),
            contact_number=payload.contact_number,
            role=payload.role.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return JSONResponse(

            status_code=status.HTTP_201_CREATED,
            content={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active":user.is_active,
                "created_at":user.created_at.isoformat(),
                "role": user.role
                }
        )
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=f"Error in registering user:{str(e)}")





@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not secure.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
 
    db.query(models.LoginSession).filter(
        models.LoginSession.user_id == user.id,
        models.LoginSession.is_active == True
    ).update(
        {"is_active": False, "logout_time": datetime.utcnow()},
        synchronize_session=False
    )
    db.commit()

    # create tokens (embed user_id and session_id in token claims)
    session_id = str(uuid.uuid4())
    access_payload = {"user_id": user.id, "session_id": session_id}
    refresh_payload = {"user_id": user.id, "session_id": session_id, "type": "refresh"}


    access_token = secure.create_access_token(access_payload)
    refresh_token = secure.create_refresh_token(refresh_payload)


    # save session
    session = models.LoginSession(
        session_id=session_id,
        user_id=user.id,
        auth_token=access_token,
        refresh_token=refresh_token,
        is_active=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # login_data=schemas.TokenResponse(
    #     access_token=access_token,
    #     refresh_token=refresh_token,
    #     session_id=session_id
    # )


    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "detail":"login successful",
            "access_token":access_token,
            "refresh_token":refresh_token,
            "session_id":session_id
        }
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(payload: schemas.RefreshRequest, db: Session = Depends(database.get_db)):

    session = db.query(models.LoginSession).filter(models.LoginSession.session_id == payload.session_id, models.LoginSession.is_active == True).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    try:
        data = secure.decode_token(payload.refresh_token)
    except jwt.ExpiredSignatureError:
        #  Auto-expire session
        session.is_active = False
        session.logout_time = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")

    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")


    if data.get("session_id") != payload.session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token session mismatch")


    # create new access token (and optionally refresh token)
    access_payload = {"user_id": session.user_id, "session_id": payload.session_id}
    new_access = secure.create_access_token(access_payload)
    new_refresh = secure.create_refresh_token({"user_id": session.user_id, "session_id": payload.session_id, "type": "refresh"})


    session.auth_token = new_access
    session.refresh_token = new_refresh
    db.add(session)
    db.commit()
    refresf_data=schemas.TokenResponse(
        access_token=new_access, 
        refresh_token=new_refresh, 
        session_id=payload.session_id
        )


    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "detail":"Refresh successful",
            "refresf_data":refresf_data
        }
    )


@router.post("/logout")
def logout(payload: schemas.LogoutRequest, db: Session = Depends(database.get_db)):
    session = db.query(models.LoginSession).filter(models.LoginSession.session_id == payload.session_id, models.LoginSession.is_active == True).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already logged out session")


    session.is_active = False
    from datetime import datetime
    session.logout_time = datetime.utcnow()
    db.add(session)
    db.commit()


    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=
        {"detail": "Logged out"}
    )