"""Department & position endpoints (Module 3)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.security import STAFF
from ..dependencies import get_current_user, get_db, require_roles
from ..models import User
from ..schemas import DepartmentIn, DepartmentOut, DepartmentUpdate, PositionIn, PositionOut
from ..services import department_service

router = APIRouter(tags=["Departments & Positions"])


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return department_service.list_departments(db)


@router.post("/departments", status_code=201, response_model=DepartmentOut)
def create_department(data: DepartmentIn, user: User = Depends(require_roles(*STAFF)),
                      db: Session = Depends(get_db)):
    return department_service.create_department(db, user, data.model_dump())


@router.put("/departments/{dept_id}", response_model=DepartmentOut)
def update_department(dept_id: int, data: DepartmentUpdate, user: User = Depends(require_roles(*STAFF)),
                      db: Session = Depends(get_db)):
    return department_service.update_department(db, user, dept_id, data.model_dump(exclude_unset=True))


@router.get("/positions", response_model=list[PositionOut])
def list_positions(department_id: int | None = None, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return department_service.list_positions(db, department_id)


@router.post("/positions", status_code=201, response_model=PositionOut)
def create_position(data: PositionIn, user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return department_service.create_position(db, user, data.model_dump())


@router.put("/positions/{pos_id}", response_model=PositionOut)
def update_position(pos_id: int, data: PositionIn, user: User = Depends(require_roles(*STAFF)),
                    db: Session = Depends(get_db)):
    return department_service.update_position(db, user, pos_id, data.model_dump())


@router.delete("/positions/{pos_id}", status_code=204)
def delete_position(pos_id: int, user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    department_service.delete_position(db, user, pos_id)
