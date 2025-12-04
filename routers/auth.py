from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from core import database, secure
# from typing import Optional
from models import models
from schemas import schemas
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid, jwt
from schemas.schemas import UserRole
from core.secure import get_current_user, hash_password, optional_current_user
from fastapi import Request, Response
from core.secure import bearer_scheme

router = APIRouter()

get_db = database.get_db



#--------------------------------------------------------------------------------
#
@router.post("/register", response_model=schemas.RegisterResponse,dependencies=[Depends(bearer_scheme)])
def register(
    payload: schemas.RegisterRequest,
    db: Session = Depends(database.get_db),
    current_user: dict | None = Depends(secure.optional_current_user)
):
    try:

        admin_exists = db.query(models.User).filter(models.User.role == "admin").first()

        if admin_exists:


            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin authentication required to create users"
                )

            user_obj = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()

            if not user_obj or user_obj.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admin can create new users"
                )

            if payload.role == UserRole.ADMIN and user_obj.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admin can assign admin role"
                )

        existing = db.query(models.User).filter(models.User.email == payload.email).first()

        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")


        new_user = models.User(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            contact_number=payload.contact_number,
            role=payload.role.value
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)


        return JSONResponse({
            "status": "Success",
            "data": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role
            }
        })

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in registering user")
#----------------------------------------------------------------------


@router.post("/login", response_model=schemas.TokenResponse)
def login_user(request: Request, response: Response, payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.email == payload.email).first()
        if not user or not secure.verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        user_payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role
        }

        session_id, auth_token = secure.initialize_session(user.id, user_payload, request, db)

        response.headers["Session_id"] = session_id
        response.headers["Authorization"] = auth_token
        response.headers["Access-Control-Expose-Headers"] = "Session_id, Authorization"



        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Login successful",
                "session_id": session_id,
                "auth_token": auth_token,
                "user_role": user.role,
                "email": user.email
            }
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"login failed.")
    
    
#---------------------------------------------------------------------------------------------------------
@router.post("/refresh")
def refresh_using_secure(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    try:
        result = secure.refresh_session(payload.session_id, db)
        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content={
                "access_token": result["access_token"],
                "session_id": result["session_id"]
                }
            )
    
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"refresh failed.")
#--------------------------------------------------------------------------------
@router.post("/logout")
def logout(payload: schemas.LogoutRequest, db: Session = Depends(database.get_db)):
    try:
        session = db.query(models.LoginSession).filter(models.LoginSession.session_id == payload.session_id, models.LoginSession.is_active == True).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already logged out session")


        session.is_active = False
        
        session.logout_time = datetime.utcnow()
        db.add(session)
        db.commit()


        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=
            {"detail": "Logged out"}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to login.")
#--------------------------------------------------------------------------------
