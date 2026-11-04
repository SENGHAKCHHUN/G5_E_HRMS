"""Central start point of the HRMS application.

    python app.py                 start the backend, then the desktop app; stop both when the window closes
    python app.py --backend       backend only (API at http://127.0.0.1:8000/api/v1, docs at /docs)
    python app.py --frontend      desktop app only (backend must already be running)

Options: --host, --port, --reload (backend auto-reload for development).
The desktop app talks to the backend at HRMS_API_URL (set automatically for a local backend).
"""
import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STARTUP_TIMEOUT = 30  # seconds to wait for the backend to accept connections


def backend_command(host: str, port: int, reload: bool) -> list[str]:
    cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", host, "--port", str(port)]
    return cmd + ["--reload"] if reload else cmd


def frontend_command() -> list[str]:
    return [sys.executable, str(ROOT / "frontend" / "main.py")]


def wait_for_port(host: str, port: int, backend: subprocess.Popen) -> bool:
    """True once something accepts connections on host:port; False if the backend exits or times out."""
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if backend.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1" if host == "0.0.0.0" else host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the HRMS backend and/or desktop app.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--backend", action="store_true", help="start only the backend API")
    mode.add_argument("--frontend", action="store_true", help="start only the desktop app")
    parser.add_argument("--host", default="127.0.0.1", help="backend host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="backend port (default 8000)")
    parser.add_argument("--reload", action="store_true", help="auto-reload the backend on code changes")
    args = parser.parse_args()

    env = os.environ.copy()
    if not args.frontend:
        env.setdefault("HRMS_API_URL", f"http://{args.host}:{args.port}")

    if args.frontend:
        return subprocess.call(frontend_command(), cwd=ROOT, env=env)

    backend = subprocess.Popen(backend_command(args.host, args.port, args.reload), cwd=ROOT, env=env)
    try:
        if args.backend:
            return backend.wait()
        if not wait_for_port(args.host, args.port, backend):
            print(f"Backend did not start on {args.host}:{args.port}.", file=sys.stderr)
            return 1
        return subprocess.call(frontend_command(), cwd=ROOT, env=env)
    except KeyboardInterrupt:
        return 0
    finally:
        stop(backend)


if __name__ == "__main__":
    sys.exit(main())
