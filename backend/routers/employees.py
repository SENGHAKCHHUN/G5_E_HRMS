"""Employee endpoints (Module 2)."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..core.pagination import Page
from ..core.security import STAFF
from ..dependencies import get_current_user, get_db, paged, pagination, require_roles
from ..models import User
from ..schemas import EmployeeCreate, EmployeeCreated, EmployeeOut, EmployeeSummary, EmployeeUpdate
from ..services import employee_service

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(response: Response, search: str | None = None, department_id: int | None = None,
                   position: str | None = None, status: str | None = None, page: Page = Depends(pagination),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Staff see everyone; employees only their own profile. `search` matches name, email or code.
    Total count in X-Total-Count."""
    return paged(response, employee_service.list_for(db, user, page, search, department_id, position, status))


@router.get("/summary", response_model=EmployeeSummary)
def employee_summary(_: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    """Number of employees per status."""
    return employee_service.summary(db)


@router.post("", status_code=201, response_model=EmployeeCreated)
def create_employee(data: EmployeeCreate, user: User = Depends(require_roles(*STAFF)),
                    db: Session = Depends(get_db)):
    """Also creates the login; the response includes `username` and a one-time `initial_password`."""
    return employee_service.create(db, user, data.model_dump())


@router.get("/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return employee_service.get_for(db, user, emp_id)


@router.put("/{emp_id}", response_model=EmployeeOut)
def update_employee(emp_id: int, data: EmployeeUpdate, user: User = Depends(require_roles(*STAFF)),
                    db: Session = Depends(get_db)):
    return employee_service.update(db, user, emp_id, data.model_dump(exclude_unset=True))


@router.delete("/{emp_id}", status_code=204)
def delete_employee(emp_id: int, user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    employee_service.delete(db, user, emp_id)
