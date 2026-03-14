"""Worker launcher that honors configured thread limits."""

from __future__ import annotations

import os

from app.core.queue import get_worker_threads


def main() -> None:
    """Exec Dramatiq with the configured thread count."""
    threads = str(get_worker_threads())
    os.execvp(
        "dramatiq",
        [
            "dramatiq",
            "app.workers.tasks",
            "--threads",
            threads,
        ],
    )


if __name__ == "__main__":
    main()
