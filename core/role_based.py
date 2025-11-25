from fastapi import Depends, HTTPException, status
from core.secure import get_current_user

def admin_required(current_user: dict = Depends(get_current_user)):
    # user = current_user["user"]
    if current_user.role!="admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=f"Access denied: admin only allowed.")
    return current_user

def any_registered_user(current_user: dict = Depends(get_current_user)):
    # user = current_user["user"]
    if current_user.role != "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Access denied: Users only.")
    return current_user    

def admin_or_user(current_user: dict= Depends(get_current_user)):
    # user = current_user["user", "admin"]
    if current_user.role not in ["user","admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Access denied: Only admin or user are allowed.")
    return current_user
