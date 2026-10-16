"""Database access for login accounts."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Employee, User


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalars(select(User).where(User.username == username)).first()


def get_by_employee_email(db: Session, email: str) -> User | None:
    stmt = select(User).join(Employee, User.employee_id == Employee.id).where(Employee.email == email)
    return db.scalars(stmt).first()


def list_all(db: Session) -> list[User]:
    return list(db.scalars(select(User).options(joinedload(User.employee)).order_by(User.id)))


def add(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    return user
