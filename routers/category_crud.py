from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core import database
from core.database import get_db
from models.models import Category
from schemas.category_schema import (CategoryCreate,CategoryUpdate,CategoryResponse)
from datetime import datetime
from core.role_based import admin_or_user,admin_required,any_registered_user
from core.secure import get_current_user
from fastapi.responses import JSONResponse

router = APIRouter() 
get_db = database.get_db


# -----------------------------------------------------------
@router.post("/create_category", response_model=CategoryResponse, dependencies=[Depends(admin_required)] )
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), current_user:dict=Depends(get_current_user)):
    try:
    
        exists = db.query(Category).filter(Category.name == payload.name).first()
        if exists:
            raise HTTPException(
                status_code=400,
                detail="Category name already exists"
            )

        category = Category(name=payload.name)
        db.add(category)
        db.commit()
        db.refresh(category)
        new_category={
            "id":category.id,
            "name":category.name,
            "created_at":category.created_at.isoformat(),
            "is_active":category.is_active
        }

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message":"success",
                "category":new_category
            }
        ) 
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category creation failed:{str(e)}")



# -----------------------------------------------------------
@router.get("/list_category", response_model=list[CategoryResponse], dependencies=[Depends(admin_or_user)])
def list_categories(db: Session = Depends(get_db), current_user:dict=Depends(get_current_user)):
    try:
        if current_user.role=="admin":

            categories = db.query(Category).all()
            if not categories:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="no category found")
            data=[
                {
                        "id" :c.id,
                        "name" :c.name,
                        "is_active" :c.is_active,
                        "created_at" :c.created_at.isoformat(),
                        "updated_at" :c.updated_at.isoformat()
                }
                for c in categories
            ]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message":"list fetched",
                    "count":len(data),
                    "returning_category":data
                }
            )
        elif current_user.role=="user":
            categories = db.query(Category).filter(Category.is_active == True).all()
            data=[
                {
                        "name" :c.name,
                        "is_active" :c.is_active,
                }
                for c in categories
            ]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message":"list fetched",
                    "count":len(data),
                    "returning_category":data
                }
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Unable to fetch list:{str(e)}")


# -----------------------------------------------------------
@router.put("/update_category/{category_id}", response_model=CategoryResponse, dependencies=[Depends(admin_required)])
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db), current_user:dict=Depends(get_current_user)):
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        if payload.name:
            
            name_exists = db.query(Category).filter(Category.name == payload.name).first()
            if name_exists and name_exists.id != category_id:
                raise HTTPException(status_code=400,detail="Category name already exists")
            category.name = payload.name

        if payload.is_active is not None:
            category.is_active = payload.is_active

        category.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(category)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message":"Update successful",
                "id":category_id.id,
                "name":category.name,
                "is_active":category.is_active,
                "created_time":category.created_at.isoformat(),
                "updated_time":category.updated_at.isoformat()
            }

        ) 
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"update failed:{str(e)}")

# -----------------------------------------------------------
@router.delete("/delete_category/{category_id}", dependencies=[Depends(admin_required)])
def delete_category(category_id: int, db: Session = Depends(get_db),current_user:dict=Depends(get_current_user)):
    try:

        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        category.is_active = False
        category.updated_at = datetime.utcnow()

        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Category soft deleted successfully.",
                "updated time":category.updated_at.isoformat()
                }
        )
    except Exception as e:
        raise HTTPException(status_codee=status.HTTP_400_BAD_REQUEST,detail=f"unable to delete:{str(e)}")
#---------------------------------------------------------------------------------------------------------------