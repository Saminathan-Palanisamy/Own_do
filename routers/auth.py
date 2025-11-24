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
                    status_code=403,
                    detail="Admin authentication required to create users"
                )

            user_obj = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()

            if not user_obj or user_obj.role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only admin can create new users"
                )

            if payload.role == UserRole.ADMIN and user_obj.role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only admin can assign admin role"
                )

        existing = db.query(models.User).filter(models.User.email == payload.email).first()

        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")


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
        raise HTTPException(status_code=500, detail=f"Error in registering user: {str(e)}")
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

        session_id, auth_token, refresh_token = secure.initialize_session(user.id, user_payload, request, db)

        response.headers["Session_id"] = session_id
        response.headers["Authorization"] = auth_token
        response.headers["Access-Control-Expose-Headers"] = "Session_id, Authorization"



        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Login successful",
                "session_id": session_id,
                "auth_token": auth_token,
                "refresh_token":refresh_token,
                "user_role": user.role,
                "username": user.username,
                "email": user.email
            }
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"login failed:{str(e)}")
    
    
#---------------------------------------------------------------------------------------------------------
@router.post("/refresh")
def refresh_using_secure(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    try:
        result = secure.refresh_session(payload.session_id,payload.refresh_token, db)
        return JSONResponse(
            status_code=status.HTTP_200_OK, 
            content={
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "bearer",
                "session_id": result["session_id"]
                }
            )
    
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"refresh failed:{str(e)}")
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to login.:{str(e)}")
#--------------------------------------------------------------------------------

# @router.post("/login", response_model=schemas.TokenResponse)
# def login(payload: schemas.LoginRequest, db: Session = Depends(database.get_db)):
#     try:
#         user = db.query(models.User).filter(models.User.email == payload.email).first()
#         if not user or not secure.verify_password(payload.password, user.hashed_password):
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    


#         session_id = str(uuid.uuid4())
#         access_payload = {"user_id": user.id, "session_id": session_id}
#         refresh_payload = {"user_id": user.id, "session_id": session_id, "type": "refresh"}


#         access_token = secure.create_access_token(access_payload)
#         refresh_token = secure.create_refresh_token(refresh_payload)


#         session = models.LoginSession(
#             session_id=session_id,
#             user_id=user.id,
#             auth_token=access_token,
#             refresh_token=refresh_token,
#             is_active=True
#         )
#         db.add(session)
#         db.commit()
#         db.refresh(session)



#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "detail":"login successful",
#                 "access_token":access_token,
#                 "refresh_token":refresh_token,
#                 "session_id":session_id
#             }
#         )
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"login failed:{str(e)}")

#------------------------------------------------------------------------------------------------------------------

# @router.post("/refresh", response_model=schemas.TokenResponse)
# def refresh_token(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
#     try:
        
#         session = db.query(models.LoginSession).filter(
#             models.LoginSession.session_id == payload.session_id,
#             models.LoginSession.is_active == True
#         ).first()
#         if not session:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive session")

        
#         try:
#             data = secure.decode_token(payload.refresh_token)
#         except Exception:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        
#         if data.get("session_id") != payload.session_id:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token session mismatch")

        
#         new_access_payload = {"user_id": session.user_id, "session_id": payload.session_id}
#         new_refresh_payload = {"user_id": session.user_id, "session_id": payload.session_id, "type": "refresh"}

#         new_access = secure.create_access_token(new_access_payload)
#         new_refresh = secure.create_refresh_token(new_refresh_payload)

        
#         session.auth_token = new_access
#         session.refresh_token = new_refresh
#         db.commit()
#         db.refresh(session)

        
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "detail": "Token refreshed successfully",
#                 "access_token": new_access,
#                 "refresh_token": new_refresh,
#                 "session_id": payload.session_id
#             }
#         )

#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         db.rollback()
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={"detail": f"Refreshing token failed: {str(e)}"}
#         )
#-------------------------------------------------------
# @router.post("/login", response_model=schemas.TokenResponse)
# def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
#     try:
#         user = db.query(models.User).filter(models.User.email == payload.email).first()
#         if not user or not secure.verify_password(payload.password, user.hashed_password):
#             raise HTTPException(status_code=401, detail="Invalid email or password")

#         session_data = secure.create_login_session(user, db)
        
#         return JSONResponse(
#             status_code=200,
#             content={"detail": "Login successful", **session_data}
#         )
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"login failed:{str(e)}")
    #------------------------------------------------------------------------------------------