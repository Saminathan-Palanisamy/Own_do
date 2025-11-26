from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from core import database, secure
from models import models
from schemas import schemas
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid, jwt
from schemas.schemas import UserRole
from core.secure import get_current_user, hash_password
from fastapi import Request, Response
from core.secure import bearer_scheme
from core.role_based import any_registered_user, admin_or_user, admin_required

router = APIRouter()

get_db = database.get_db

@router.get("/list_Login_sessions_active", dependencies=[Depends(admin_required)])
def list_login_sessions_active(db:Session=Depends(get_db), current_user:dict=Depends(get_current_user)):
    try:
        true_cond=db.query(models.LoginSession).filter(models.LoginSession.is_active==True)
        login_sessions=true_cond.all()
        data=[
            {
                "logging_id" :t.logging_id,
                "session_id" :t.session_id,
                "user_id" :t.user_id,
                "is_active" :t.is_active
            }
            for t in login_sessions
        ]
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message":"List fetch success",
                "count":len(data),
                "data":data
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"listing failed:{str(e)}")
    