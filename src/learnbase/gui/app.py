"""LearnBase Tkinter GUI — main window with dark theme."""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from typing import Optional, List

from ..core.tasks_manager import TasksManager
from ..core.models import Task
from .dialogs import TaskDialog
from . import theme as T

REFRESH_MS = 30_000


# ────────────────────────────────────────────────────────────────
#  Scrollable frame helper
# ────────────────────────────────────────────────────────────────

class ScrollableFrame(tk.Frame):
    """A vertically-scrollable frame using canvas."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=T.BG_BASE, **kw)
        self.canvas = tk.Canvas(self, bg=T.BG_BASE, bd=0, highlightthickness=0)
        self.inner = tk.Frame(self.canvas, bg=T.BG_BASE)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.pack(fill="both", expand=True)

        # Mouse-wheel scrolling
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120 or event.delta), "units")


# ────────────────────────────────────────────────────────────────
#  Task row widget
# ────────────────────────────────────────────────────────────────

class TaskRow(tk.Frame):
    """A single task row with accent bar, hover, and click handling."""

    def __init__(self, parent, task, *, overdue=False, on_click=None, on_right_click=None):
        super().__init__(parent, bg=T.BG_SURFACE, cursor="hand2")
        self.task_id = task.id
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._selected = False

        # Left accent bar
        accent_color = T.ACCENT_RED if overdue else T.BG_SURFACE
        self.accent = tk.Frame(self, bg=accent_color, width=3)
        self.accent.pack(side="left", fill="y")

        # Content area
        content = tk.Frame(self, bg=T.BG_SURFACE, padx=14, pady=10)
        content.pack(side="left", fill="both", expand=True)

        # Top row: title + status
        top = tk.Frame(content, bg=T.BG_SURFACE)
        top.pack(fill="x")

        self.title_lbl = tk.Label(
            top, text=task.title, font=T.FONT_BODY,
            fg=T.TEXT_BRIGHT if overdue else T.TEXT, bg=T.BG_SURFACE, anchor="w",
        )
        self.title_lbl.pack(side="left", fill="x", expand=True)

        status_color = T.STATUS_COLORS.get(task.status, T.TEXT_MUTED)
        status_text = task.status.replace("_", " ")
        self.status_lbl = tk.Label(
            top, text=status_text, font=T.FONT_TINY,
            fg=status_color, bg=T.BG_SURFACE,
        )
        self.status_lbl.pack(side="right")

        # Bottom row: workspace badge + due + categories
        bottom = tk.Frame(content, bg=T.BG_SURFACE)
        bottom.pack(fill="x", pady=(4, 0))

        ws_color = T.WS_COLORS.get(task.workspace, T.TEXT_MUTED)
        tk.Label(
            bottom, text=task.workspace, font=T.FONT_TINY,
            fg=ws_color, bg=T.BG_SURFACE,
        ).pack(side="left")

        due_text = task.due.strftime("%b %d")
        due_fg = T.ACCENT_RED if overdue else T.TEXT_MUTED
        tk.Label(
            bottom, text=f"  {due_text}", font=T.FONT_TINY,
            fg=due_fg, bg=T.BG_SURFACE,
        ).pack(side="left")

        if task.categories:
            cats = "  ·  " + ", ".join(task.categories)
            tk.Label(
                bottom, text=cats, font=T.FONT_TINY,
                fg=T.TEXT_DIM, bg=T.BG_SURFACE,
            ).pack(side="left")

        if task.project:
            tk.Label(
                bottom, text=f"  {task.project}", font=T.FONT_TINY,
                fg=T.ACCENT_TEAL, bg=T.BG_SURFACE,
            ).pack(side="right")

        # Separator at bottom
        tk.Frame(self, bg=T.DIVIDER, height=1).pack(side="bottom", fill="x")

        # Bind events to all child widgets
        self._bind_recursive(self)

    def _bind_recursive(self, widget):
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Button-1>", self._click, add="+")
        widget.bind("<Double-1>", self._dbl_click, add="+")
        widget.bind("<Button-2>", self._right, add="+")
        widget.bind("<Button-3>", self._right, add="+")
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _set_bg(self, color):
        for w in self._all_widgets():
            try:
                w.configure(bg=color)
            except tk.TclError:
                pass

    def _all_widgets(self):
        yield self
        stack = list(self.winfo_children())
        while stack:
            w = stack.pop()
            # Skip the accent bar and bottom separator
            if w is self.accent:
                continue
            yield w
            stack.extend(w.winfo_children())

    def _on_enter(self, _e):
        if not self._selected:
            self._set_bg(T.BG_HOVER)

    def _on_leave(self, _e):
        if not self._selected:
            self._set_bg(T.BG_SURFACE)

    def _click(self, _e):
        if self._on_click:
            self._on_click(self.task_id)

    def _dbl_click(self, e):
        if self._on_click:
            self._on_click(self.task_id, double=True)

    def _right(self, e):
        if self._on_right_click:
            self._on_right_click(self.task_id, e)

    def select(self):
        self._selected = True
        self._set_bg(T.BG_SELECTED)
        self.accent.configure(bg=T.ACCENT_GREEN)

    def deselect(self):
        self._selected = False
        self._set_bg(T.BG_SURFACE)


# ────────────────────────────────────────────────────────────────
#  Filter pill button
# ────────────────────────────────────────────────────────────────

class PillButton(tk.Label):
    """Small toggle button that looks like a pill/chip."""

    def __init__(self, parent, text, variable, value, command=None, **kw):
        self._var = variable
        self._value = value
        self._command = command
        super().__init__(
            parent, text=text, font=T.FONT_TINY,
            padx=10, pady=3, cursor="hand2", **kw,
        )
        self._var.trace_add("write", lambda *_: self._update_style())
        self.bind("<Button-1>", self._toggle)
        self._update_style()

    def _toggle(self, _e):
        self._var.set(self._value)
        if self._command:
            self._command()

    def _update_style(self):
        active = self._var.get() == self._value
        self.configure(
            bg=T.BG_SELECTED if active else T.BG_BASE,
            fg=T.TEXT_BRIGHT if active else T.TEXT_MUTED,
        )


# ────────────────────────────────────────────────────────────────
#  Main application
# ────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LearnBase Tasks")
        self.geometry("760x620")
        self.minsize(620, 420)
        self.configure(bg=T.BG_BASE)

        self.manager = TasksManager()
        self.view_mode = tk.StringVar(value="daily")
        self.filter_workspace = tk.StringVar(value="all")
        self.filter_category = tk.StringVar(value="all")
        self._selected_id: Optional[str] = None
        self._rows: dict[str, TaskRow] = {}

        self._build_header()
        self._build_filters()
        self._build_list()
        self._build_statusbar()

        self.refresh()
        self.after(REFRESH_MS, self._auto_refresh)

    # ── Layout ───────────────────────────────────────────────────

    def _build_header(self):
        header = tk.Frame(self, bg=T.BG_BASE)
        header.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(
            header, text="LEARNBASE", font=T.FONT_GROUP,
            fg=T.TEXT_DIM, bg=T.BG_BASE,
        ).pack(side="left")

        # New task button
        btn = tk.Label(
            header, text="+ New Task", font=T.FONT_SMALL,
            fg=T.ACCENT, bg=T.BG_BASE, cursor="hand2",
            padx=12, pady=4,
        )
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda e: self._new_task())
        btn.bind("<Enter>", lambda e: btn.configure(fg=T.TEXT_BRIGHT))
        btn.bind("<Leave>", lambda e: btn.configure(fg=T.ACCENT))

    def _build_filters(self):
        bar = tk.Frame(self, bg=T.BG_BASE)
        bar.pack(fill="x", padx=20, pady=(0, 8))

        # View mode pills
        for text, val in [("Daily", "daily"), ("All", "all")]:
            PillButton(bar, text, self.view_mode, val, command=self.refresh).pack(
                side="left", padx=(0, 6))

        # Spacer
        tk.Frame(bar, bg=T.BG_BASE, width=16).pack(side="left")

        # Workspace pills
        for text, val in [("All", "all"), ("Work", "work"),
                          ("Personal", "personal"), ("Contract", "contract")]:
            PillButton(bar, text, self.filter_workspace, val, command=self.refresh).pack(
                side="left", padx=(0, 4))

        tk.Frame(bar, bg=T.BG_BASE, width=16).pack(side="left")

        # Category pills
        for text, val in [("All", "all"), ("People", "people"), ("Idea", "idea"),
                          ("Project", "project"), ("Admin", "admin")]:
            PillButton(bar, text, self.filter_category, val, command=self.refresh).pack(
                side="left", padx=(0, 4))

    def _build_list(self):
        # Thin top separator
        tk.Frame(self, bg=T.DIVIDER, height=1).pack(fill="x", padx=20)
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 0))

    def _build_statusbar(self):
        tk.Frame(self, bg=T.DIVIDER, height=1).pack(fill="x", padx=20)
        self.statusbar = tk.Label(
            self, text="", font=T.FONT_TINY,
            fg=T.TEXT_DIM, bg=T.BG_BASE, anchor="w", padx=20, pady=8,
        )
        self.statusbar.pack(fill="x")

    # ── Data ─────────────────────────────────────────────────────

    def refresh(self):
        for w in self.scroll.inner.winfo_children():
            w.destroy()
        self._rows.clear()
        self._selected_id = None

        ws = self.filter_workspace.get()
        workspace = ws if ws != "all" else None
        cat = self.filter_category.get()
        categories = [cat] if cat != "all" else None

        if self.view_mode.get() == "daily":
            self._load_daily(workspace, categories)
        else:
            self._load_all(workspace, categories)

    def _add_group_label(self, text: str, count: int):
        lbl = tk.Label(
            self.scroll.inner, text=f"{text}  ({count})",
            font=T.FONT_GROUP, fg=T.TEXT_DIM, bg=T.BG_BASE,
            anchor="w", padx=4,
        )
        lbl.pack(fill="x", pady=(14, 6))

    def _add_task_row(self, task, overdue=False):
        row = TaskRow(
            self.scroll.inner, task,
            overdue=overdue,
            on_click=self._on_row_click,
            on_right_click=self._on_row_right_click,
        )
        row.pack(fill="x")
        self._rows[task.id] = row

    def _load_daily(self, workspace, categories):
        now = datetime.now()
        today = now.date()
        week_end = (now + timedelta(days=7)).date()

        all_tasks = self.manager.list_tasks(workspace=workspace, categories=categories)
        active = [t for t in all_tasks if t.status in ("pending", "in_progress")]

        overdue = [t for t in active if t.due < now and t.due.date() < today]
        due_today = [t for t in active if t.due.date() == today]
        this_week = [t for t in active if today < t.due.date() <= week_end]
        later = [t for t in active if t.due.date() > week_end]

        if overdue:
            self._add_group_label("OVERDUE", len(overdue))
            for t in overdue:
                self._add_task_row(t, overdue=True)
        if due_today:
            self._add_group_label("TODAY", len(due_today))
            for t in due_today:
                self._add_task_row(t)
        if this_week:
            self._add_group_label("THIS WEEK", len(this_week))
            for t in this_week:
                self._add_task_row(t)
        if later:
            self._add_group_label("LATER", len(later))
            for t in later:
                self._add_task_row(t)

        total = len(active)
        self.statusbar.config(text=f"{total} tasks  ·  {len(overdue)} overdue")

    def _load_all(self, workspace, categories):
        tasks = self.manager.list_tasks(workspace=workspace, categories=categories)
        now = datetime.now()
        for t in tasks:
            is_overdue = t.due < now and t.status in ("pending", "in_progress")
            self._add_task_row(t, overdue=is_overdue)
        self.statusbar.config(text=f"{len(tasks)} tasks")

    # ── Actions ──────────────────────────────────────────────────

    def _on_row_click(self, task_id: str, double: bool = False):
        # Deselect previous
        if self._selected_id and self._selected_id in self._rows:
            self._rows[self._selected_id].deselect()
        self._selected_id = task_id
        if task_id in self._rows:
            self._rows[task_id].select()
        if double:
            self._edit_task(task_id)

    def _on_row_right_click(self, task_id: str, event):
        self._on_row_click(task_id)
        menu = tk.Menu(
            self, tearoff=0,
            bg=T.BG_SURFACE, fg=T.TEXT,
            activebackground=T.BG_SELECTED, activeforeground=T.TEXT_BRIGHT,
            font=T.FONT_SMALL,
        )
        menu.add_command(label="Mark Complete",
                         command=lambda: self._set_status(task_id, "completed"))
        menu.add_command(label="Mark In Progress",
                         command=lambda: self._set_status(task_id, "in_progress"))
        menu.add_separator()
        menu.add_command(label="Archive",
                         command=lambda: self._archive(task_id))
        menu.tk_popup(event.x_root, event.y_root)

    def _new_task(self):
        dlg = TaskDialog(self)
        if dlg.result is None:
            return
        r = dlg.result
        task_id = Task.create_id(r["title"], r["due"])
        task = Task(
            id=task_id,
            title=r["title"],
            description=r["description"],
            categories=r["categories"],
            workspace=r["workspace"],
            project=r["project"],
            due=r["due"],
            status=r["status"],
            filename=Task.create_filename(task_id),
        )
        try:
            self.manager.create_task(task)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.refresh()

    def _edit_task(self, task_id: str):
        try:
            task = self.manager.get_task(task_id)
        except ValueError:
            return

        data = {
            "title": task.title,
            "description": task.description,
            "due": task.due,
            "status": task.status,
            "workspace": task.workspace,
            "project": task.project,
            "categories": list(task.categories),
        }
        dlg = TaskDialog(self, task=data)
        if dlg.result is None:
            return

        updates = {}
        for key in ("title", "description", "due", "status", "workspace", "project", "categories"):
            if dlg.result[key] != data.get(key):
                updates[key] = dlg.result[key]

        if updates:
            try:
                self.manager.update_task(task_id, updates)
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            self.refresh()

    def _set_status(self, task_id: str, status: str):
        try:
            self.manager.update_task(task_id, {"status": status})
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.refresh()

    def _archive(self, task_id: str):
        try:
            self.manager.archive_task(task_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.refresh()

    def _auto_refresh(self):
        self.refresh()
        self.after(REFRESH_MS, self._auto_refresh)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
