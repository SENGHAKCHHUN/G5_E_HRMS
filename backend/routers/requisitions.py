"""Job requisition endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.security import STAFF
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import RequisitionIn, RequisitionOut, RequisitionUpdate
from ..services import requisition_service

router = APIRouter(prefix="/requisitions", tags=["Requisitions"])


@router.get("", response_model=list[RequisitionOut])
def list_requisitions(department_id: int | None = None, status: str | None = None,
                      _: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return requisition_service.list_requisitions(db, department_id, status)


@router.post("", status_code=201, response_model=RequisitionOut)
def create_requisition(data: RequisitionIn, user: User = Depends(require_roles(*STAFF)),
                       db: Session = Depends(get_db)):
    return requisition_service.create(db, user, data.model_dump())


@router.put("/{req_id}", response_model=RequisitionOut)
def update_requisition(req_id: int, data: RequisitionUpdate, user: User = Depends(require_roles(*STAFF)),
                       db: Session = Depends(get_db)):
    return requisition_service.set_status(db, user, req_id, data.status)
