"""Standalone web server launcher for LNG Fleet Performance Management System.

Usage:
    python -m lng_fleet_performance.web [--port 8000] [--host 0.0.0.0]
"""
import uvicorn
import argparse
import webbrowser
import threading
import time
import os


def main():
    parser = argparse.ArgumentParser(
        description="LNG Fleet Performance Management System - Web Server")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    from .api.app import app
    from .database.schema import create_all_tables
    from .api.deps import get_db

    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend", "build")
    has_frontend = os.path.exists(os.path.join(frontend_dir, "index.html"))

    if has_frontend:
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        @app.get("/")
        async def serve_index():
            return FileResponse(os.path.join(frontend_dir, "index.html"))

    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://localhost:{args.port}")

    if not args.no_browser:
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"=" * 60)
    print(f"  LNG Fleet Performance Management System")
    print(f"  Server: http://localhost:{args.port}")
    print(f"  API Docs: http://localhost:{args.port}/docs")
    print(f"  Frontend: {'Yes' if has_frontend else 'API only'}")
    print(f"=" * 60)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
