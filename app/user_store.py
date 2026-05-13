import uuid

from app.auth import hash_password
from app.auth_models import UserCreate, UserRole, UserStored

_user_db: dict[str, UserStored] = {}


class DuplicateEmailError(Exception):
    pass


def create_user(data: UserCreate) -> UserStored:
    for existing in _user_db.values():
        if existing.email == data.email:
            raise DuplicateEmailError(data.email)
    user = UserStored(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=UserRole.operator,
    )
    _user_db[user.id] = user
    return user


def get_user(user_id: str) -> UserStored | None:
    return _user_db.get(user_id)


def get_user_by_email(email: str) -> UserStored | None:
    for user in _user_db.values():
        if user.email == email:
            return user
    return None
