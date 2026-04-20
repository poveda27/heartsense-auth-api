from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import auth
from database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HeartSense Auth API",
    description="API de autenticación para registro e inicio de sesión de usuarios",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "HeartSense Auth API corriendo correctamente"}