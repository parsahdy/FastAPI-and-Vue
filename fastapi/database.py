from sqlalchemy import create_engine
from sqlalchemy.orm import create_session, declarative_base


DATABSE_URL = "sqlite:///./test.db"

engine = create_engine(DATABSE_URL, connect_args={"check_same_thread": False})

Sessionlocal = create_session(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()