"""Convenience entrypoint for running the backend with ``python main.py``."""

import uvicorn


def main() -> None:
    """Run the FastAPI application with Uvicorn."""
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=False)


if __name__ == '__main__':
    main()
