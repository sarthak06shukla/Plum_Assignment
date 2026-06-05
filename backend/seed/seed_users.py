from backend.app.core.security import hash_password
from backend.app.db.session import Base, SessionLocal, engine
from backend.app.models.entities import User, UserRole


def seed_users() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        get_or_create_user(db, "admin@plum.demo", "Ops Admin", "admin123", UserRole.ADMIN)
        get_or_create_user(db, "member@plum.demo", "Demo Member", "member123", UserRole.USER)
        db.commit()
        print("Ensured demo admin/member users exist.")
    finally:
        db.close()


def get_or_create_user(db, email: str, name: str, password: str, role: UserRole) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(email=email, name=name, role=role, hashed_password=hash_password(password))
    db.add(user)
    db.flush()
    return user


if __name__ == "__main__":
    seed_users()
