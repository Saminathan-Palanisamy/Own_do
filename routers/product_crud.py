from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from core import database
from core.database import get_db
from schemas.product_schema import (ProductCreate,ProductUpdate,ProductResponse)
from models.models import Product, ProductImage, Category
from core.secure import get_current_user
from core.role_based import admin_or_user,admin_required,any_registered_user


router = APIRouter()
get_db = database.get_db

# -------------------------------------------------------------
@router.post("/create_product",dependencies=[Depends(admin_required)])
def create_product(payload: ProductCreate,db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    try:
        category = db.query(Category).filter(Category.id == payload.category_id,Category.is_active == True).first()

        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        new_product = Product(
            category_id=payload.category_id,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            stock=payload.stock
        )

        db.add(new_product)
        db.commit()
        db.refresh(new_product)


        for url in payload.image_urls:
            img = ProductImage(product_id=new_product.id, image_path=url)
            db.add(img)
 
        db.commit()
        image_list=payload.image_urls 
        data={
                "id" : new_product.id,
                "category_id" : new_product.category_id,
                "name" :new_product.name,
                "description": new_product.description,
                "price" : new_product.price,
                "stock": new_product.stock,
                "is_active" : new_product.is_active,
                "created_at" : new_product.created_at.isoformat(),
                "updated_at" : new_product.updated_at.isoformat(),
                "image":image_list
            }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=
            {
                "message": "Product created successfully",
                "created_category_data":data
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"product creation failed:{str(e)}")


# -------------------------------------------------------------
@router.patch("/update/{product_id}", dependencies=[Depends(admin_required)])
def update_product(product_id: int,payload: ProductUpdate,db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    try:
        product = db.query(Product).filter(Product.id == product_id,Product.is_active == True).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        if payload.name is not None:
            product.name = payload.name.strip()

        if payload.description is not None:
            product.description = payload.description.strip()

        if payload.price is not None:
            product.price = payload.price

        if payload.stock is not None:
            product.stock = payload.stock

        if payload.image_urls is not None:

            db.query(ProductImage).filter(ProductImage.product_id == product_id).delete()

            for url in payload.image_urls:
                db.add(ProductImage(product_id=product_id, image_path=url))


        db.commit()
        db.refresh(product)


        data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "image": [img.image_path for img in product.images]
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Product updated successfully",
                "data":data
                }
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"updated product failed: {str(e)}")


# -------------------------------------------------------------
@router.delete("/delete/{product_id}",dependencies=[Depends(admin_required)])
def soft_delete_product(product_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:

        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.is_active = False
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Product deleted successfully"})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unable to delete, edho sadhi panudhu:{str(e)}")


# -------------------------------------------------------------
@router.get("/list", response_model=list[ProductResponse],  dependencies=[Depends(admin_or_user)])
def list_products(db: Session = Depends(get_db), current_user:dict=Depends(get_current_user)):
    try:
        if current_user.role=="admin":
            products = db.query(Product).all()
            data=[
                {
                    "id":d.id,
                    "name":d.name,
                    "stock":d.stock,
                    "is_active":d.is_active
                }
                for d in products
            ]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message":"List fetched successfully",
                    "count":len(data),
                    "data":data
                }
            )
        elif current_user.role=="user":
            products = db.query(Product).filter(Product.is_active == True).all()
            data=[
                {
                    "id":d.id,
                    "name":d.name,
                    "stock":d.stock,
                    "is_active":d.is_active
                }
                for d in products
            ]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message":"List fetched successfully",
                    "count":len(data),
                    "data":data
                }
            )     
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"list eduthutu vara matikudhu, reason: {str(e)}")
#-------------------------------------------------------------------------------------------------------