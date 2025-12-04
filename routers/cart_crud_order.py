from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.cart_order_schema import AddToCartRequest, CartResponse,OrderResponse,UpdateOrderStatusRequest,UpdateCartRequest
from models.models import Cart, CartItem, Product,Order,OrderItem
from core.role_based import any_registered_user, admin_or_user, admin_required
from core.secure import get_current_user, get_or_create_cart
from core import database
from fastapi.responses import JSONResponse

router = APIRouter() 
get_db = database.get_db

ALLOWED_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}

@router.post("/add", dependencies=[Depends(any_registered_user)])
def add_to_cart(payload: AddToCartRequest,
                db: Session = Depends(get_db),
                current_user: dict = Depends(get_current_user)):

    try:
        cart = get_or_create_cart(current_user.id, db)

        product = db.query(Product).filter(
            Product.id == payload.product_id,
            Product.is_active == True
        ).first()

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == payload.product_id
        ).first()

        if item:
            item.qty += payload.qty
            item.total_price = item.qty * float(item.price_snapshot)
        else:
            price_snapshot = float(product.price)
            total_price = float(payload.qty) * price_snapshot
            item = CartItem(
                cart_id=cart.id,
                product_id=payload.product_id,
                qty=payload.qty,
                price_snapshot=price_snapshot,
                total_price = total_price
            )
            db.add(item)

        db.commit()
        db.refresh(item)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
            "message": "Cart updated successfully",
            "data": {
                "product_id": item.product_id,
                "qty": item.qty,
                "price_snapshot": float(item.price_snapshot),
                "total_price": float(item.total_price)
            }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Cart item unable to add.")
#------------------------------------------------------------------
@router.patch("/update/{product_id}", dependencies=[Depends(any_registered_user)])
def update_cart_item(
    product_id: int,
    payload: UpdateCartRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update quantity of an item in the user's cart. 
    If qty <= 0, item is removed.
    """
    try:
        cart = get_or_create_cart(current_user.id, db)

        item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).first()

        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

        if payload.qty <= 0:
            db.delete(item)
            db.commit()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Item removed from cart"}
            )

        item.qty = payload.qty
        item.total_price = float(item.qty) * float(item.price_snapshot)

        db.commit()
        db.refresh(item)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Cart item updated successfully",
                "data": {
                    "product_id": item.product_id,
                    "qty": item.qty,
                    "price_snapshot": float(item.price_snapshot),
                    "total_price": float(item.total_price)
                }
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to update cart item."
        )
#-------------------------------------------------------------------------

@router.get("/view", dependencies=[Depends(admin_or_user)])
def view_cart(db: Session = Depends(get_db),
              current_user: dict = Depends(get_current_user)):

    try:
        if current_user.role == "user":
            cart = get_or_create_cart(current_user.id, db)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                "message": "Cart fetched successfully",
                "cart count":len(cart.items),
                "data": {
                    "id": cart.id,
                    "user_id": cart.user_id,
                    "items": [
                        {
                            "product_id": i.product_id,
                            "qty": i.qty,
                            "price_snapshot": float(i.price_snapshot),
                            "total_price": float(i.total_price)
                        }
                        for i in cart.items
                    ]
                }
            })

        elif current_user.role == "admin":
            cart_items = db.query(CartItem).all()

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                "message": "All cart items fetched successfully",
                "data": [
                    {
                        "id": c.id,
                        "cart_id": c.cart_id,
                        "product_id": c.product_id,
                        "qty": c.qty,
                        "price_snapshot": float(c.price_snapshot)
                    }
                    for c in cart_items
                ]
            })

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unable to fetch cart.")
#-------------------------------------------------------------------------

@router.delete("/remove/{product_id}", dependencies=[Depends(any_registered_user)])
def remove_item(product_id: int,
                db: Session = Depends(get_db),
                current_user: dict = Depends(get_current_user)):

    try:
        cart = get_or_create_cart(current_user.id, db)

        item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).first()

        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")

        db.delete(item)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Item removed successfully"}
)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unable to remove item.")

#-------------------------------------------------------------------------------------------

#--- order-----------------------------------
#----------------------------------------------------------------------------------------
@router.post("/place", dependencies=[Depends(any_registered_user)])
def place_order(db: Session = Depends(get_db),
                current_user: dict = Depends(get_current_user)):

    try:
        cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()

        if not cart or not cart.items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

  
        for item in cart.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()

            if not product:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item.product_id} not found")

            if product.stock < item.qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product '{product.name}' has only {product.stock} in stock"
                )


        total = sum(i.qty * float(i.price_snapshot) for i in cart.items)

        order = Order(user_id=current_user.id, total=total)
        db.add(order)
        db.commit()
        db.refresh(order)

        order_items = []

        for item in cart.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product.stock -= item.qty  

            oi = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                qty=item.qty,
                price_snapshot=item.price_snapshot
            )
            db.add(oi)
            order_items.append(oi)


        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Order placed successfully",
                "data": {
                    "id": order.id,
                    "total": float(order.total),
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "items": [
                        {
                            "product_id": oi.product_id,
                            "qty": oi.qty,
                            "price_snapshot": float(oi.price_snapshot)
                        }
                        for oi in order_items
                    ]
                }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Order placement failed.")

#-----------------------------------------------------------------------------------------------------------------
@router.get("/orders", dependencies=[Depends(admin_required)])
def list_orders(
    order_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,              # NEW
    limit: int = 10,            # NEW
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        """
        {"pending", "confirmed", "shipped", "delivered", "cancelled"}
        """

        if order_id is not None:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                "id": order.id,
                "total": float(order.total),
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "items": [
                    {
                        "product_id": i.product_id,
                        "qty": i.qty,
                        "price_snapshot": float(i.price_snapshot)
                    }
                    for i in order.items
                ]
            }
    )

        query = db.query(Order)

        #  Filter by status if provided
        if status_filter:
            s = status_filter.lower().strip()
            if s not in ALLOWED_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Allowed: {', '.join(sorted(ALLOWED_STATUSES))}"
                )
            query = query.filter(Order.status == s)

        #  Pagination logic
        total_orders = query.count()
        offset = (page - 1) * limit

        orders = query.offset(offset).limit(limit).all()


        return JSONResponse({
            "page": page,
            "limit": limit,
            "total_orders": total_orders,
            "total_pages": (total_orders + limit - 1) // limit,
            "status_filter": status_filter,
            "orders": [
                {
                    "id": order.id,
                    "total": float(order.total),
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "items": [
                        {
                            "product_id": i.product_id,
                            "qty": i.qty,
                            "price_snapshot": float(i.price_snapshot)
                        }
                        for i in order.items
                    ]
                }
                for order in orders
            ]
        }
    )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="unable to view order.")
#-------------------------------------------------------------------------------------------


@router.patch("/orders/{order_id}/status", dependencies=[Depends(admin_required)])
def update_order_status(order_id: int,
                        payload: UpdateOrderStatusRequest,
                        db: Session = Depends(get_db),
                        current_user: dict = Depends(get_current_user)):
    """
    {"pending", "confirmed", "shipped", "delivered", "cancelled"}
    """
    try:
        new_status = payload.status.lower().strip()

        if new_status not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed: {', '.join(sorted(ALLOWED_STATUSES))}"
            )

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


        order.status = new_status
        db.commit()
        db.refresh(order)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Order status updated",
                "data": {
                    "id": order.id,
                    "status": order.status,
                    "total": float(order.total),
                    "created_at": order.created_at.isoformat(),
                    "items": [
                        {
                            "product_id": i.product_id,
                            "qty": i.qty,
                            "price_snapshot": float(i.price_snapshot)
                        }
                        for i in order.items
                    ]
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="order update failed.")
#-------------------------------------------------------------------------------------------

@router.patch("/orders/{order_id}/cancel", dependencies=[Depends(admin_or_user)])
def cancel_order(order_id: int,
                 db: Session = Depends(get_db),
                 current_user: dict = Depends(get_current_user)):
    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        if current_user.role == "user" and order.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot cancel another user's order")

        if order.status not in {"pending", "confirmed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order cannot be cancelled once it is {order.status}"
            )


        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.qty


        order.status = "cancelled"
        db.commit()
        db.refresh(order)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Order cancelled successfully",
                "data": {
                    "id": order.id,
                    "status": order.status,
                    "total": float(order.total),
                    "created_at": order.created_at.isoformat(),
                    "items": [
                        {
                            "product_id": i.product_id,
                            "qty": i.qty,
                            "price_snapshot": float(i.price_snapshot)
                        }
                        for i in order.items
                    ]
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="unable to view order.")
    
#-------------------------------------------------------------------------------------
@router.get("/my_orders", dependencies=[Depends(any_registered_user)])
def user_orders(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        orders = db.query(Order).filter(Order.user_id == current_user.id).all()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "My orders fetched successfully",
                "count": len(orders),
                "data": [
                    {
                        "id": order.id,
                        "total": float(order.total),
                        "status": order.status,
                        "created_at": order.created_at.isoformat(),
                        "items": [
                            {
                                "product_id": item.product_id,
                                "qty": item.qty,
                                "price_snapshot": float(item.price_snapshot)
                            }
                            for item in order.items
                        ]
                    }
                    for order in orders
                ]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to fetch orders.")
#----------------------------------------------------------------------------