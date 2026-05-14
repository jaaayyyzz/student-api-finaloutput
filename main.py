from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List

# --- AUTHENTICATION SETUP ---
API_KEY = "password123"
API_KEY_NAME = "access_token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )

# --- DATABASE SETUP ---
DATABASE_URL = "sqlite:///./students.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class StudentDB(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    major = Column(String)
    gpa = Column(Float)

Base.metadata.create_all(bind=engine)

# --- MODELS ---
class StudentCreate(BaseModel):
    name: str
    email: str
    major: str
    gpa: float

class StudentResponse(BaseModel):
    id: int
    name: str
    email: str
    major: str
    gpa: float
    class Config:
        from_attributes = True

app = FastAPI(title="Student API with Auth")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ENDPOINTS ---

# Public endpoint (No Auth needed)
@app.get("/")
def home():
    return {"message": "Welcome to the Student API. Please use your API Key to access data."}

# 1. Create a Student (Requires Auth)
@app.post("/students", response_model=StudentResponse)
def create_student(student: StudentCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    db_student = StudentDB(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

# 2. Get All Students (Requires Auth)
@app.get("/students", response_model=List[StudentResponse])
def get_all_students(db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    return db.query(StudentDB).all()

# 3. Get One Student (Requires Auth)
@app.get("/students/{s_id}", response_model=StudentResponse)
def get_student(s_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    student = db.query(StudentDB).filter(StudentDB.id == s_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

# 4. Update a Student (Requires Auth)
@app.put("/students/{s_id}", response_model=StudentResponse)
def update_student(s_id: int, updated_data: StudentCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    student = db.query(StudentDB).filter(StudentDB.id == s_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    for key, value in updated_data.dict().items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student

# 5. Delete a Student (Requires Auth)
@app.delete("/students/{s_id}")
def delete_student(s_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    student = db.query(StudentDB).filter(StudentDB.id == s_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}