from fastapi import FastAPI, Depends
from routers import auth,check
from core.database import Base, engine
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, status

Base.metadata.create_all(bind=engine)



app = FastAPI(title="Own_do_project API - session based")

app.include_router(auth.router, prefix="/User_setup", tags=["User_SetUp"])
app.include_router(check.router, prefix="/List_active_sessions", tags=["View_purpose"])


@app.get("/")
def root():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Welcome to the Sajith task_2_project API"
    "paaka nala irukum, vandhu paarungal!"}
    )

