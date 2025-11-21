# from fastapi import Request
# from fastapi.responses import JSONResponse
# import jwt
# from core.database import Base, engine
# from fastapi import FastAPI, Request

# Base.metadata.create_all(bind=engine)

# from main import app

# @app.middleware("http")
# async def jwt_middleware(request: Request, call_next):

#     allowed_routes = [
#         "/User_setup/login",
#         "/User_setup/register",
#         "/openapi.json",
#         "/docs",
#         "/docs/oauth2-redirect",
#         "/",
#     ]

#     # Allow public routes
#     if request.url.path in allowed_routes:
#         return await call_next(request)

#     # Require token
#     token = request.headers.get("Authorization")
#     if not token:
#         return JSONResponse(
#             status_code=403,
#             content={"detail": "Forbidden - Authorization header missing"}
#         )

#     # Token format: "Bearer <token>"
#     try:
#         token = token.replace("Bearer ", "")
#         jwt.decode(token, "supersecret", algorithms=["HS256"])
#     except Exception:
#         return JSONResponse(
#             status_code=401,
#             content={"detail": "Invalid or expired token"}
#         )

#     return await call_next(request)
