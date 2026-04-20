from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, TokenResponse, UserResponse, MessageResponse
from security import decode_access_token

router = APIRouter()


# ── POST /auth/register ───────────────────────────────────
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    responses={
        409: {"model": MessageResponse, "description": "Correo ya registrado"},
        422: {"description": "Datos inválidos"},
    },
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en la base de datos.

    - Valida que el correo no esté previamente registrado.
    - Almacena la contraseña con hash bcrypt.
    - Retorna un token JWT listo para usar.
    """
    # Verificar si el correo ya existe
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado.",
        )

    # Crear usuario
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generar token
    token = create_access_token(data={"sub": new_user.email, "user_id": new_user.id})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(new_user),
    )


# ── POST /auth/login ──────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    responses={
        401: {"model": MessageResponse, "description": "Credenciales incorrectas"},
        403: {"model": MessageResponse, "description": "Cuenta inactiva"},
    },
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica un usuario existente.

    - Valida que el correo exista en la base de datos.
    - Verifica que la contraseña sea correcta.
    - Retorna un token JWT en caso de éxito.
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    # Usuario no encontrado o contraseña incorrecta (mismo mensaje por seguridad)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada. Contacta al administrador.",
        )

    token = create_access_token(data={"sub": user.email, "user_id": user.id})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


# ── GET /auth/me ──────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener usuario autenticado",
)
def get_me(token: str, db: Session = Depends(get_db)):
    """
    Retorna los datos del usuario autenticado a partir del token JWT.
    Útil para validar tokens desde el frontend.
    """
    from app.security import decode_access_token

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    return UserResponse.model_validate(user)
