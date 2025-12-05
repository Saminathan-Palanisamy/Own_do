# routers/notifications.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from core import database
from core.database import get_db
from core.secure import get_current_user
from core.role_based import admin_required, any_registered_user
from models.models import Notification, User
from schemas.notification_schema import NotificationCreate, NotificationResponse

router = APIRouter()
get_db = database.get_db


@router.post("/send", dependencies=[Depends(admin_required)])
def send_notification(payload: NotificationCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Admin sends notification to a specific user (payload.user_id) or to ALL users if user_id is omitted/null.
    """
    try:

        target_users = []
        if payload.user_id is None:
            target_users = db.query(User).all()
            if not target_users:
                raise JSONResponse(status_code=status.HTTP_200_OK, content={"message": "No users to send to", "sent_count": 0})
        else:
            user = db.query(User).filter(User.id == payload.user_id).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            target_users = [user]


        created = 0
        for u in target_users:
            notif = Notification(
                user_id=u.id,
                message=payload.message
            )
            db.add(notif)
            created += 1

        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Notification(s) created", "sent_count": created}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Notification sending failed.")


@router.get("/my", dependencies=[Depends(any_registered_user)])
def my_notifications(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Return notifications for current user (most recent first).
    """
    try:
        notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()

        data = [
            {
                "id": n.id,
                "user_id": n.user_id,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifs
        ]

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Notifications fetched successfully", "count": len(data), "data": data})

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Unable to fetch notifications."})


@router.get("/view_all", dependencies=[Depends(admin_required)])
def all_notifications(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Admin: list all notifications across users.
    """
    try:
        notifs = db.query(Notification).order_by(Notification.created_at.desc()).all()

        data = [
            {
                "id": n.id,
                "user_id": n.user_id,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifs
        ]

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "All notifications fetched successfully", "count": len(data), "data": data})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Unable to fetch notifications."})


@router.patch("/read/{notif_id}", dependencies=[Depends(any_registered_user)])
def mark_as_read(notif_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Mark a specific notification as read for the current user.
    """
    try:
        notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
        if not notif:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Notification not found"})

        notif.is_read = True
        db.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Notification marked as read", "id": notif_id})

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Unable to mark notification."})


@router.delete("/delete/{notif_id}", dependencies=[Depends(any_registered_user)])
def delete_notification(notif_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Delete a notification owned by current user.
    """
    try:
        notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
        if not notif:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Notification not found"})

        db.delete(notif)
        db.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Notification deleted successfully", "id": notif_id})

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Unable to delete notification."})


# -------------------------
# Extra Convenience Endpoints
# -------------------------
@router.post("/send-to-all", dependencies=[Depends(admin_required)])
def send_to_all(payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Admin convenience endpoint: POST /notifications/send-to-all
    Format:
    {
     "user_id": null,
      "message": "Hello all users!"
    }
    """
    try:
        message = payload.get("message")
        if not message:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "message is required"})

        users = db.query(User).all()
        if not users:
            return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "No users found", "sent_count": 0})

        created = 0
        for u in users:
            notif = Notification(user_id=u.id, message=message)
            db.add(notif)
            created += 1
        db.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Notifications sent to all users", "sent_count": created})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Sending failed."})


@router.post("/send-to-role/{role_name}", dependencies=[Depends(admin_required)])
def send_to_role(role_name: str, payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Admin: send message to users having role == role_name.
    POST body: {"message": "..."}
    Format:
    {
      "message": "Hello all users!"
    }
    """
    try:
        message = payload.get("message")
        if not message:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "message is required"})

        users = db.query(User).filter(User.role == role_name).all()
        if not users:
            return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "No users with that role", "sent_count": 0})

        created = 0
        for u in users:
            notif = Notification(user_id=u.id, message=message)
            db.add(notif)
            created += 1
        db.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": f"Notifications sent to role {role_name}", "sent_count": created})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Sending failed."})


@router.get("/unread-count", dependencies=[Depends(any_registered_user)])
def unread_count(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    GET /notifications/unread-count
    returns: {"unread": N}
    """
    try:
        count = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"unread": count})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Unable to compute unread count."})
