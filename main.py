from fastapi import FastAPI
from routers import auth,check, category_crud, product_crud
from core.database import Base, engine
from fastapi.responses import JSONResponse
from fastapi import status

Base.metadata.create_all(bind=engine)



app = FastAPI(title="Own_do_project API - session based")

app.include_router(auth.router, prefix="/User_setup", tags=["User_SetUp"])
app.include_router(check.router, prefix="/List_active_sessions", tags=["View_purpose"])
app.include_router(category_crud.router,prefix="/categories", tags=["Categories"])
app.include_router(product_crud.router,prefix="/products", tags=["Products"])

@app.get("/")
def root():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Welcome to the Sajith task_2_project API"
    "paaka nala irukum, vandhu paarungal!"}
    )

