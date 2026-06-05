from backend.app.api.routes_auth import register
from backend.app.models.entities import UserRole
from backend.app.schemas.auth import UserCreate


class FakeRegisterDb:
    def __init__(self) -> None:
        self.created_user = None

    def scalar(self, _query):
        return None

    def add(self, user):
        self.created_user = user

    def commit(self):
        pass

    def refresh(self, _user):
        pass


def test_public_registration_always_creates_member_user():
    db = FakeRegisterDb()
    payload = UserCreate(
        email="new.member@example.com",
        name="New Member",
        password="member123",
        role=UserRole.ADMIN,
    )

    response = register(payload, db)

    assert db.created_user.role == UserRole.USER
    assert response.role == UserRole.USER
