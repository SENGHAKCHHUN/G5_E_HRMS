"""Who may see which records (role-based access rules shared by the services)."""
from ..core.errors import Forbidden
from ..core.security import STAFF
from ..models import User


def is_staff(user: User) -> bool:
    return user.role in STAFF


def ensure_self_or_staff(user: User, employee_id: int | None) -> None:
    """Employees may only touch their own records."""
    if not is_staff(user) and employee_id != user.employee_id:
        raise Forbidden("You can only access your own records")


def scope_employee(user: User, employee_id: int | None) -> int | None:
    """Staff may filter by any employee (or none); employees are always limited to themselves."""
    return employee_id if is_staff(user) else user.employee_id
