"""Directory watcher - monitors a directory for new CTF challenges and auto-solves."""

from __future__ import annotations

import time
import json
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .agents.base import ChallengeInfo
from .agents.dispatcher import dispatcher
from .config.settings import settings


class ChallengeHandler(FileSystemEventHandler):
    """Handles new challenge files appearing in the watched directory."""

    def __init__(self, auto_solve: bool = True, auto_writeup: bool = True):
        self.auto_solve = auto_solve
        self.auto_writeup = auto_writeup
        self.processed: set[str] = set()
        self._pending: dict[str, float] = {}
        self.watch_dir: Path | None = None

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        if filepath.suffix in [".tmp", ".swp", ".swx", ".part"] or filepath.name.startswith("~"):
            return
        self._pending[str(filepath)] = time.time()

    def process_pending(self):
        now = time.time()
        ready = []
        for path_str, first_seen in list(self._pending.items()):
            if now - first_seen > 2.0:
                ready.append(path_str)
                del self._pending[path_str]
        for path_str in ready:
            self._process_file(Path(path_str))

    def _process_file(self, filepath: Path):
        if str(filepath) in self.processed or not filepath.exists():
            return
        self.processed.add(str(filepath))

        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] New challenge: {filepath.name}")
        print(f"{'='*60}")

        if not self.auto_solve:
            return

        challenge = ChallengeInfo(
            name=filepath.stem,
            files=[filepath],
            description=f"Auto-detected from watched directory",
        )
        result = dispatcher.solve_with_fallback(challenge)

        log_path = settings.output_dir / f"{filepath.stem}_log.json"
        log_path.write_text(json.dumps({
            "name": filepath.stem,
            "category": result.category,
            "success": result.success,
            "flag": result.flag,
            "approach": result.approach,
            "steps": result.steps,
            "errors": result.errors,
            "duration": result.duration_seconds,
        }, indent=2, ensure_ascii=False))

        print(f"  Category: {result.category}")
        print(f"  Success:  {result.success}")
        if result.flag:
            print(f"  Flag:     {result.flag}")
        if result.errors:
            print(f"  Errors:   {'; '.join(result.errors)}")

        if self.auto_writeup and result.success:
            from .writeup.generator import WriteupGenerator
            generator = WriteupGenerator()
            wp = generator.generate(
                challenge_name=filepath.stem,
                category=result.category,
                result={
                    "success": result.success,
                    "flag": result.flag,
                    "category": result.category,
                    "approach": result.approach,
                    "steps": result.steps,
                    "errors": result.errors,
                    "duration": result.duration_seconds,
                },
            )
            print(f"  Writeup:  {wp}")


class ChallengeWatcher:
    """Watches a directory for new challenge files and auto-solves them."""

    def __init__(self, watch_dir: Path | None = None, auto_solve: bool = True, auto_writeup: bool = True):
        self.watch_dir = watch_dir or settings.work_dir
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.observer = Observer()
        self.handler = ChallengeHandler(auto_solve, auto_writeup)
        self.handler.watch_dir = self.watch_dir

    def start(self):
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=True)
        self.observer.start()
        print(f"Watching: {self.watch_dir}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
