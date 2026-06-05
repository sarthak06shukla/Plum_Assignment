import os
import shutil
from pathlib import Path
from sqlalchemy import select, delete
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.models.entities import (
    Claim, User, UserRole, Document, ExtractedFields,
    DecisionLog, FraudFlag, ManualReview, AuditLog
)
from backend.app.core.security import hash_password

def clean_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Delete child tables first to avoid foreign key constraints (if enforced)
        print("Deleting manual reviews...")
        db.execute(delete(ManualReview))
        
        print("Deleting fraud flags...")
        db.execute(delete(FraudFlag))
        
        print("Deleting decision logs...")
        db.execute(delete(DecisionLog))
        
        print("Deleting extracted fields...")
        db.execute(delete(ExtractedFields))
        
        print("Deleting documents...")
        db.execute(delete(Document))
        
        print("Deleting claims...")
        db.execute(delete(Claim))
        
        print("Deleting audit logs...")
        db.execute(delete(AuditLog))
        
        # Keep only the two seeded users, delete any other registered users
        print("Resetting users...")
        db.execute(delete(User).where(User.email.not_in(["admin@plum.demo", "member@plum.demo"])))
        
        # Make sure the two seeded users exist and have correct passwords
        admin = db.scalar(select(User).where(User.email == "admin@plum.demo"))
        if not admin:
            db.add(User(
                email="admin@plum.demo",
                name="Ops Admin",
                role=UserRole.ADMIN,
                hashed_password=hash_password("admin123")
            ))
        else:
            admin.hashed_password = hash_password("admin123")
            
        user = db.scalar(select(User).where(User.email == "member@plum.demo"))
        if not user:
            db.add(User(
                email="member@plum.demo",
                name="Demo Member",
                role=UserRole.USER,
                hashed_password=hash_password("member123")
            ))
        else:
            user.hashed_password = hash_password("member123")
            
        db.commit()
        print("Database cleaned successfully!")
        
        # Clear uploads folder
        uploads_dir = Path(__file__).resolve().parents[2] / "backend" / "uploads"
        if uploads_dir.exists():
            print(f"Cleaning uploads folder at {uploads_dir}...")
            for item in uploads_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    print(f"Error removing {item}: {e}")
            print("Uploads folder cleaned successfully!")
            
    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
