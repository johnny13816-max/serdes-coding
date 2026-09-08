"""Manual GUI for the file-backed IEEE 802.3 Annex 178A split search.

The GUI owns no COM equations. It only loads a project case and invokes the
public orchestration actions in :mod:`com_search_178A`.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import csv
from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Thread
from typing import Any, Callable, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..io.com_excel_io import excel_to_config_178A, excel_to_search_config_178A
from .com_search_178A import (
    SearchArtifacts,
    create_search_plan,
    finalize_search,
    merge_partial_results,
    run_full_search,
    run_partial_group,
)


class _QueueWriter:
    """Forward stdout/stderr from a worker thread into the Tk event loop."""

    def __init__(self, events: Queue[tuple[str, str]]):
        self._events = events

    def write(self, text: str) -> int:
        if text.strip():
            self._events.put(("log", text.rstrip()))
        return len(text)

    def flush(self) -> None:
        return None


class COMSearchGui178A:
    """Tk front end for manually executing one 178A search case."""

    def __init__(self, root: tk.Tk, initial_case: Optional[str | Path] = None):
        self.root = root
        self.root.title("IEEE 802.3 178A COM Search")
        self.root.minsize(760, 520)

        self._events: Queue[tuple[str, str]] = Queue()
        self._cfg: Any = None
        self._search: Any = None
        self._buttons: list[ttk.Button] = []

        self.case_path = tk.StringVar(value="" if initial_case is None else str(initial_case))
        self.group_id = tk.StringVar(value="0")
        self.status_text = tk.StringVar(value="Select and load a case.")

        self._build_widgets()
        self.root.after(100, self._drain_events)
        if initial_case is not None:
            self._load_case()

    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(4, weight=1)

        ttk.Label(frame, text="Case folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(frame, textvariable=self.case_path).grid(row=0, column=1, sticky="ew")
        ttk.Button(frame, text="Browse", command=self._browse_case).grid(row=0, column=2, padx=(8, 0))
        self._add_button(frame, "Load", self._load_case, row=0, column=3, padx=(8, 0))

        ttk.Separator(frame).grid(row=1, column=0, columnspan=4, sticky="ew", pady=12)
        self._add_button(frame, "Create Manifest", self._create_manifest, row=2, column=0, sticky="ew")
        ttk.Label(frame, text="Group ID").grid(row=2, column=1, sticky="e", padx=(20, 8))
        ttk.Entry(frame, textvariable=self.group_id, width=8).grid(row=2, column=2, sticky="w")
        self._add_button(frame, "Run Group", self._run_group, row=2, column=3, sticky="ew")
        self._add_button(frame, "Merge Results", self._merge_results, row=3, column=0, sticky="ew", pady=(8, 0))
        self._add_button(frame, "Finalize Top-K", self._finalize, row=3, column=1, sticky="ew", pady=(8, 0))
        self._add_button(frame, "Run Full Search", self._run_full, row=3, column=3, sticky="ew", pady=(8, 0))

        self.log = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.log.grid(row=4, column=0, columnspan=4, sticky="nsew", pady=(12, 6))
        ttk.Label(frame, textvariable=self.status_text).grid(row=5, column=0, columnspan=4, sticky="w")

    def _add_button(self, parent: ttk.Frame, text: str, command: Callable[[], None], **grid: Any) -> None:
        button = ttk.Button(parent, text=text, command=command)
        button.grid(**grid)
        self._buttons.append(button)

    def _browse_case(self) -> None:
        selected = filedialog.askdirectory(title="Select a COM case folder")
        if selected:
            self.case_path.set(selected)

    def _load_case(self) -> None:
        try:
            case_dir = self._case_dir()
            workbook = case_dir / "config" / "config_178A.xlsx"
            if not workbook.exists():
                raise FileNotFoundError(f"Missing 178A workbook: {workbook}")
            self._cfg = excel_to_config_178A(str(workbook))
            self._search = excel_to_search_config_178A(str(workbook))
            artifacts = self._artifacts()
            self.status_text.set(
                f"Loaded {case_dir.name}; report: {artifacts.root}"
            )
            self._log(f"Loaded case: {case_dir}")
            self._log(f"Search report directory: {artifacts.root}")
        except Exception as error:
            messagebox.showerror("Load case failed", str(error))

    def _create_manifest(self) -> None:
        self._run_background("Create manifest", self._create_manifest_action)

    def _run_group(self) -> None:
        self._run_background("Run group", self._run_group_action)

    def _merge_results(self) -> None:
        self._run_background("Merge partial results", self._merge_action)

    def _finalize(self) -> None:
        self._run_background("Finalize top-K", self._finalize_action)

    def _run_full(self) -> None:
        if not messagebox.askyesno(
            "Run full search",
            "This will run every planned group and then top-K finalization. Continue?",
        ):
            return
        self._run_background("Run full search", self._run_full_action)

    def _create_manifest_action(self) -> str:
        cfg, search, artifacts = self._require_case()
        create_search_plan(cfg, search, artifacts.root)
        return f"Manifest and group plan written to: {artifacts.root}"

    def _run_group_action(self) -> str:
        cfg, search, artifacts = self._require_case()
        group_id = int(self.group_id.get())
        output = run_partial_group(cfg, search, artifacts.root, group_id)
        return f"Partial result written: {output}"

    def _merge_action(self) -> str:
        _, _, artifacts = self._require_case()
        rows = merge_partial_results(artifacts.root)
        return f"Merged {len(rows)} candidates: {artifacts.merged_results_path}"

    def _finalize_action(self) -> str:
        cfg, search, artifacts = self._require_case()
        status = finalize_search(cfg, search, artifacts.root, include_plots=True)
        return f"Finalized best index={status.best_row.idx}, MSE={status.best_row.mse:.6e} V^2, COM={status.COM}"

    def _run_full_action(self) -> str:
        cfg, search, artifacts = self._require_case()
        status = run_full_search(cfg, search, artifacts.root, include_plots=True)
        return f"Full search complete: best index={status.best_row.idx}, COM={status.COM}"

    def _run_background(self, label: str, action: Callable[[], str]) -> None:
        try:
            self._require_case()
        except Exception as error:
            messagebox.showerror(f"{label} failed", str(error))
            return
        self._set_busy(True, label)

        def worker() -> None:
            writer = _QueueWriter(self._events)
            try:
                with redirect_stdout(writer), redirect_stderr(writer):
                    message = action()
                self._events.put(("done", message))
            except Exception as error:
                self._events.put(("error", f"{type(error).__name__}: {error}"))

        Thread(target=worker, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                kind, message = self._events.get_nowait()
                if kind == "log":
                    self._log(message)
                elif kind == "done":
                    self._log(message)
                    self._set_busy(False, "Ready")
                elif kind == "error":
                    self._log(message)
                    self._set_busy(False, "Failed")
                    messagebox.showerror("Search action failed", message)
        except Empty:
            pass
        self.root.after(100, self._drain_events)

    def _set_busy(self, busy: bool, text: str) -> None:
        state = "disabled" if busy else "normal"
        for button in self._buttons:
            button.configure(state=state)
        self.status_text.set(text)

    def _require_case(self) -> tuple[Any, Any, SearchArtifacts]:
        if self._cfg is None or self._search is None:
            raise RuntimeError("Load a valid case before running a search action.")
        return self._cfg, self._search, self._artifacts()

    def _case_dir(self) -> Path:
        path = Path(self.case_path.get()).expanduser()
        if not path.is_dir():
            raise NotADirectoryError(f"Case folder does not exist: {path}")
        return path.resolve()

    def _artifacts(self) -> SearchArtifacts:
        return SearchArtifacts(self._case_dir() / "report" / "178A" / "search_run")

    def _log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main(argv: Optional[list[str]] = None) -> None:
    """Launch the manual 178A split-search GUI."""
    parser = argparse.ArgumentParser(description="IEEE 802.3 178A COM search GUI")
    parser.add_argument("--case", dest="case_dir", default=None, help="Path to cases/<case_id>")
    args = parser.parse_args(argv)
    root = tk.Tk()
    COMSearchGui178A(root, initial_case=args.case_dir)
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:])
