from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import engine, Sessionlocal
from datetime import datetime, timedelta, timezone
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, List, Optional
import schemas
import models
import secrets

SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

app.add_middleware (
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = Sessionlocal()
    try:
        yield db
    finally:
        db.close()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
db_dependency = Annotated[Session, Depends(get_db)]


def get_current_user(db: db_dependency, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not available credentials.",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

user_dependency = Annotated[dict, Depends(get_current_user)]

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: db_dependency, username: str):
    return db.query(models.User).filter(models.User.username == username)

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

@app.post("/register", response_model=schemas.Token)
def register(user: schemas.UserCreate, db: db_dependency):
    db_user = get_user(db, user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User already registerd.")
    hashed_password = get_password_hash(user.password)
    new_user = models.User(user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "Bearer"}

@app.get("/users/me", response_model=schemas.UserCreate)
def read_users_me(current_user: user_dependency):
    return current_user

@app.post("/todos/", response_model=schemas.TodoCreate)
def create_todo(todo: schemas.TodoCreate, db: db_dependency, current_user: user_dependency):
    db_todo = models.Todo(**todo.model_dump(), owner_id=current_user.id)
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, db: db_dependency, current_user: user_dependency):
    todo = db.query(models.Todo).filter(models.Todo.id == current_user.id).first()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Todo not found.")
    db.delete(todo)
    db.commit()
    return {"detail": "Todo deleted"}

@app.get("/todos/", response_model=List[schemas.TodoGet])
def read_todos(db: db_dependency, current_user: user_dependency, skip: int = 0, limit: int = 10):
    todos = db.query(models.Todo).filter(models.Todo.id == current_user.id).offset(skip).limit(limit).all()
    return todos