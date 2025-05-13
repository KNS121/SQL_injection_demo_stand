from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import os


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="/app/static")


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/testdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password = Column(String(50))
    is_admin = Column(Boolean, default=False)



def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.add_all([
            User(username='admin', password='admin', is_admin=True),
            User(username='user1', password='user1'),
            User(username='user2', password='user2')
        ])
        db.commit()


@app.on_event("startup")
async def startup_event():
    init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



@app.post("/vulner-login")
async def vulnerable_login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...)
):
    try:
        # Vulnerable SQL query
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"

        with engine.connect() as conn:
            result = conn.execute(text(query))
            user = result.fetchone()

        if user:
            return {"status": "success", "user": dict(zip(result.keys(), user))}
        return {"status": "error", "message": "Invalid credentials"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# OOOOORRRRRRMMMMM
@app.post("/secure-login")
async def secure_login(
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    try:
        # long login -> neaa :D
        if len(username) < 3 or len(username) > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be 3-20 characters"
            )

        # security query
        user = db.query(User).filter(
            User.username == username,
            User.password == password
        ).first()

        # standart answer
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        return {
            "status": "success",
            "username": user.username,
            "is_admin": user.is_admin
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )