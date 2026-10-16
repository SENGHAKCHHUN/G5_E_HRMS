"""Database access for departments and job positions."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models import Department, Position


def get(db: Session, department_id: int) -> Department | None:
    return db.get(Department, department_id)


def list_all(db: Session) -> list[Department]:
    stmt = (select(Department)
            .options(selectinload(Department.employees), selectinload(Department.positions))
            .order_by(Department.id))
    return list(db.scalars(stmt))


def get_by_name(db: Session, name: str) -> Department | None:
    return db.scalars(select(Department).where(func.lower(Department.name) == name.lower())).first()


def add(db: Session, department: Department) -> Department:
    db.add(department)
    db.flush()
    return department


def get_position(db: Session, position_id: int) -> Position | None:
    return db.get(Position, position_id)


def list_positions(db: Session, department_id: int | None = None) -> list[Position]:
    stmt = select(Position).order_by(Position.id)
    if department_id:
        stmt = stmt.where(Position.department_id == department_id)
    return list(db.scalars(stmt))


def add_position(db: Session, position: Position) -> Position:
    db.add(position)
    db.flush()
    return position


def delete_position(db: Session, position: Position) -> None:
    db.delete(position)
