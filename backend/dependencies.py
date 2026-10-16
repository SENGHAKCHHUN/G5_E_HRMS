"""FastAPI dependencies shared by the routers: database session, current user, role checks."""
from collections.abc import Callable, Iterator

from fastapi import Depends, Query, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .core.config import config
from .core.database import SessionLocal
from .core.errors import Forbidden
from .core.pagination import Page
from .models import User
from .services import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{config.api_prefix}/auth/login")
ACCOUNT_PATH = f"{config.api_prefix}/auth/"


def get_db() -> Iterator[Session]:
    """One database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # account endpoints stay usable while a password change / 2FA setup is pending
    return auth_service.user_from_token(db, token, account_endpoint=request.url.path.startswith(ACCOUNT_PATH))


def require_roles(*roles: str) -> Callable[..., User]:
    """Dependency factory: allow only the given roles."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise Forbidden("You do not have permission for this action")
        return user
    return checker


def pagination(limit: int | None = Query(None, ge=1, le=1000, description="Rows per page (omit for all)"),
               offset: int = Query(0, ge=0, description="Rows to skip")) -> Page:
    return Page(limit=limit, offset=offset)


def paged(response: Response, result: tuple[list, int]) -> list:
    """Return the rows and put the total row count in the X-Total-Count header."""
    rows, total = result
    response.headers["X-Total-Count"] = str(total)
    return rows


def client_ip(request: Request) -> str:
    """The caller's IP address. Behind a reverse proxy (nginx/Caddy) the proxy's address is seen,
    so X-Forwarded-For is used - but only from proxies listed in HRMS_TRUSTED_PROXIES, otherwise
    anyone could fake their address to pass the office-network check."""
    peer = request.client.host if request.client else ""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and peer in config.trusted_proxies:
        # "client, proxy1, proxy2": the right-most address not belonging to our proxies is the client
        for addr in reversed([a.strip() for a in forwarded.split(",") if a.strip()]):
            if addr not in config.trusted_proxies:
                return addr
    return peer
