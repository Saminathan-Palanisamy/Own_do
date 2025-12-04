from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from core import database
from core.database import get_db
from schemas.product_schema import (ProductCreate,ProductUpdate,ProductResponse)
from models.models import Product, ProductImage, Category
from core.secure import get_current_user
from core.role_based import admin_or_user,admin_required,any_registered_user
from typing import List
# from models.models import UserRole,ADMIN, USER

router = APIRouter()
get_db = database.get_db

# -------------------------------------------------------------
@router.post("/categories/{category_id}/products/create", dependencies=[Depends(admin_required)])
def create_products(category_id: int, payload: List[ProductCreate],
                    db: Session = Depends(get_db),
                    current_user: dict = Depends(get_current_user)):
    """
    Create one or many products under the given category_id.
    """
    try:
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True
        ).first()

        if not category:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Category not found"}
            )

        created_products = []

        for item in payload:
            new_product = Product(
                category_id=category_id,
                name=item.name,
                description=item.description,
                price=item.price,
                stock=item.stock
            )

            db.add(new_product)
            db.commit()
            db.refresh(new_product)

            for url in item.image_urls:
                db.add(ProductImage(product_id=new_product.id, image_path=url))

            db.commit()

            created_products.append({
                "id": new_product.id,
                "category_id": category_id,
                "name": new_product.name,
                "description": new_product.description,
                "price": new_product.price,
                "stock": new_product.stock,
                "is_active": new_product.is_active,
                "created_at": new_product.created_at.isoformat(),
                "updated_at": new_product.updated_at.isoformat(),
                "images": item.image_urls
            })

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Products created successfully",
                "count": len(created_products),
                "products": created_products
            }
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail= "Product creation failed.")
            
# -------------------------------------------------------------
@router.patch("/update/{product_id}", dependencies=[Depends(admin_required)])
def update_product(product_id: int,payload: ProductUpdate,db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    try:
        product = db.query(Product).filter(Product.id == product_id,Product.is_active == True).first()

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="updated product failed.")


# -------------------------------------------------------------
@router.delete("/delete/{product_id}",dependencies=[Depends(admin_required)])
def soft_delete_product(product_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:

        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        product.is_active = False
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Product deleted successfully"})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unable to delete, edho sadhi panudhu.")


# -------------------------------------------------------------
@router.get("/list", response_model=list[ProductResponse],  dependencies=[Depends(admin_or_user)])
def list_products(db: Session = Depends(get_db), current_user:dict=Depends(get_current_user)):
    try:
        # if current_user.role=="admin":
        #     products = db.query(Product).all()
        #     data=[
        #         {
        #             "id":d.id,
        #             "name":d.name,
        #             "stock":d.stock,
        #             "is_active":d.is_active
        #         }
        #         for d in products
        #     ]
        #     return JSONResponse(
        #         status_code=status.HTTP_200_OK,
        #         content={
        #             "message":"List fetched successfully",
        #             "count":len(data),
        #             "data":data
        #         }
        #     )
        # elif current_user.role=="user":
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="list eduthutu vara matikudhu.")
#-------------------------------------------------------------------------------------------------------
#view product by selecting their category id within the path
@router.get("/list-by-category/{category_id}", response_model=list[ProductResponse], dependencies=[Depends(admin_or_user)])
def list_products_by_category(category_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        products = db.query(Product).filter(Product.category_id==category_id,Product.is_active == True).all()
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="list category unable to fetch.")
#-----------------------------------------------------------------------------------------------------------------