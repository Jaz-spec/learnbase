"""Task create/edit dialog — dark themed."""

import tkinter as tk
from datetime import datetime
from typing import Optional, Dict, Any

from . import theme as T

WORKSPACES = ["personal", "work", "contract"]
CATEGORIES = ["people", "idea", "project", "admin"]
STATUSES = ["pending", "in_progress", "completed"]


class _DarkOptionMenu(tk.Menubutton):
    """A styled dropdown replacing ttk.Combobox."""

    def __init__(self, parent, variable, values, **kw):
        super().__init__(
            parent, textvariable=variable, font=T.FONT_SMALL,
            fg=T.TEXT, bg=T.BG_INPUT, activebackground=T.BG_HOVER,
            activeforeground=T.TEXT_BRIGHT, bd=0,
            highlightbackground=T.BORDER, highlightthickness=1,
            padx=8, pady=4, anchor="w", cursor="hand2",
            indicatoron=True, relief="flat", **kw,
        )
        self.menu = tk.Menu(
            self, tearoff=0, bg=T.BG_SURFACE, fg=T.TEXT,
            activebackground=T.BG_SELECTED, activeforeground=T.TEXT_BRIGHT,
            font=T.FONT_SMALL,
        )
        self["menu"] = self.menu
        for v in values:
            self.menu.add_command(label=v, command=lambda val=v: variable.set(val))


class TaskDialog(tk.Toplevel):
    """Dialog for creating or editing a task."""

    def __init__(self, parent: tk.Tk, task: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.result: Optional[Dict[str, Any]] = None
        self.task = task
        editing = task is not None

        self.title("Edit Task" if editing else "New Task")
        self.geometry("500x560")
        self.resizable(False, False)
        self.configure(bg=T.BG_BASE)
        self.transient(parent)
        self.grab_set()

        # Main container
        outer = tk.Frame(self, bg=T.BG_BASE, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        # Heading
        tk.Label(
            outer, text="Edit Task" if editing else "New Task",
            font=T.FONT_HEADING, fg=T.TEXT_BRIGHT, bg=T.BG_BASE,
        ).pack(anchor="w", pady=(0, 16))

        # ── Title ──
        self._label(outer, "Title")
        self.title_var = tk.StringVar(value=task["title"] if editing else "")
        self._entry(outer, self.title_var).pack(fill="x", pady=(0, 12))

        # ── Description ──
        self._label(outer, "Description")
        self.desc_text = tk.Text(
            outer, height=5, wrap="word",
            font=T.FONT_SMALL, fg=T.TEXT, bg=T.BG_INPUT,
            insertbackground=T.TEXT, bd=0,
            highlightbackground=T.BORDER, highlightthickness=1,
            padx=8, pady=6,
        )
        self.desc_text.pack(fill="x", pady=(0, 12))
        if editing:
            self.desc_text.insert("1.0", task.get("description", ""))

        # ── Due + Status row ──
        row1 = tk.Frame(outer, bg=T.BG_BASE)
        row1.pack(fill="x", pady=(0, 12))

        left = tk.Frame(row1, bg=T.BG_BASE)
        left.pack(side="left", fill="x", expand=True)
        self._label(left, "Due date")
        due_default = task["due"].strftime("%Y-%m-%d %H:%M") if editing else ""
        self.due_var = tk.StringVar(value=due_default)
        self._entry(left, self.due_var, width=20).pack(anchor="w")

        right = tk.Frame(row1, bg=T.BG_BASE)
        right.pack(side="right")
        self._label(right, "Status")
        self.status_var = tk.StringVar(value=task["status"] if editing else "pending")
        _DarkOptionMenu(right, self.status_var, STATUSES).pack(anchor="w")

        # ── Workspace + Project row ──
        row2 = tk.Frame(outer, bg=T.BG_BASE)
        row2.pack(fill="x", pady=(0, 12))

        left2 = tk.Frame(row2, bg=T.BG_BASE)
        left2.pack(side="left", fill="x", expand=True)
        self._label(left2, "Workspace")
        self.workspace_var = tk.StringVar(value=task["workspace"] if editing else "personal")
        _DarkOptionMenu(left2, self.workspace_var, WORKSPACES).pack(anchor="w")

        right2 = tk.Frame(row2, bg=T.BG_BASE)
        right2.pack(side="right")
        self._label(right2, "Project")
        self.project_var = tk.StringVar(value=task.get("project") or "" if editing else "")
        self._entry(right2, self.project_var, width=18).pack(anchor="w")

        # ── Categories ──
        self._label(outer, "Categories")
        cat_frame = tk.Frame(outer, bg=T.BG_BASE)
        cat_frame.pack(anchor="w", pady=(0, 20))
        self.cat_vars: Dict[str, tk.BooleanVar] = {}
        existing_cats = task.get("categories", []) if editing else []
        for cat in CATEGORIES:
            var = tk.BooleanVar(value=cat in existing_cats)
            self.cat_vars[cat] = var
            cb = tk.Checkbutton(
                cat_frame, text=cat, variable=var,
                font=T.FONT_SMALL, fg=T.TEXT, bg=T.BG_BASE,
                selectcolor=T.BG_INPUT, activebackground=T.BG_BASE,
                activeforeground=T.TEXT_BRIGHT, highlightthickness=0,
                cursor="hand2",
            )
            cb.pack(side="left", padx=(0, 16))

        # ── Buttons ──
        btn_frame = tk.Frame(outer, bg=T.BG_BASE)
        btn_frame.pack(fill="x")

        save_btn = tk.Label(
            btn_frame, text="Save", font=T.FONT_SMALL,
            fg=T.BG_BASE, bg=T.ACCENT, padx=16, pady=6, cursor="hand2",
        )
        save_btn.pack(side="right")
        save_btn.bind("<Button-1>", lambda e: self._save())
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=T.TEXT_BRIGHT))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=T.ACCENT))

        cancel_btn = tk.Label(
            btn_frame, text="Cancel", font=T.FONT_SMALL,
            fg=T.TEXT_MUTED, bg=T.BG_BASE, padx=16, pady=6, cursor="hand2",
        )
        cancel_btn.pack(side="right", padx=(0, 12))
        cancel_btn.bind("<Button-1>", lambda e: self.destroy())
        cancel_btn.bind("<Enter>", lambda e: cancel_btn.configure(fg=T.TEXT_BRIGHT))
        cancel_btn.bind("<Leave>", lambda e: cancel_btn.configure(fg=T.TEXT_MUTED))

        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window()

    # ── Helpers ──────────────────────────────────────────────────

    def _label(self, parent, text):
        tk.Label(
            parent, text=text, font=T.FONT_TINY,
            fg=T.TEXT_MUTED, bg=T.BG_BASE, anchor="w",
        ).pack(anchor="w", pady=(0, 3))

    def _entry(self, parent, variable, width=40):
        e = tk.Entry(
            parent, textvariable=variable, width=width,
            font=T.FONT_SMALL, fg=T.TEXT, bg=T.BG_INPUT,
            insertbackground=T.TEXT, bd=0,
            highlightbackground=T.BORDER, highlightthickness=1,
        )
        return e

    def _save(self):
        title = self.title_var.get().strip()
        if not title:
            return

        due_str = self.due_var.get().strip()
        if not due_str:
            return
        try:
            due = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                due = datetime.strptime(due_str, "%Y-%m-%d")
            except ValueError:
                return

        self.result = {
            "title": title,
            "description": self.desc_text.get("1.0", "end-1c").strip(),
            "due": due,
            "status": self.status_var.get(),
            "workspace": self.workspace_var.get(),
            "project": self.project_var.get().strip() or None,
            "categories": [c for c, v in self.cat_vars.items() if v.get()],
        }
        self.destroy()
