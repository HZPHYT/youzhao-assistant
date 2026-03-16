from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./customer_data.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CustomerCredit(Base):
    __tablename__ = "customer_credit"
    
    customer_id = Column(String, primary_key=True)
    customer_name = Column(String)
    credit_limit = Column(Float)
    loan_limit = Column(Float)
    used_credit = Column(Float)
    used_loan = Column(Float)
    credit_status = Column(String)
    loan_status = Column(String)
    update_time = Column(String)

class CustomerApproval(Base):
    __tablename__ = "customer_approval"
    
    customer_id = Column(String, primary_key=True)
    customer_name = Column(String)
    apply_type = Column(String)
    apply_amount = Column(Float)
    apply_date = Column(String)
    approval_status = Column(String)
    approval_result = Column(String)
    approver = Column(String, nullable=True)
    approval_date = Column(String, nullable=True)
    remark = Column(String, nullable=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
