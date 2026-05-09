"""
Agenda Personal — App de Escritorio
Recordatorios inteligentes con fechas permanentes y únicas.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import sys
import datetime
import winreg
import subprocess
from pathlib import Path

# ─── PATHS ────────────────────────────────────────────────────────────────────

APP_NAME    = "AgendaPersonal"
APP_DIR     = Path(os.environ.get("APPDATA", ".")) / "AgendaPersonal"
DATA_FILE   = APP_DIR / "recordatorios.json"
CONFIG_FILE = APP_DIR / "config.json"
APP_DIR.mkdir(parents=True, exist_ok=True)

# ─── COLORS & FONTS ───────────────────────────────────────────────────────────

DARK = {
    "bg":        "#0f0f11",
    "surface":   "#18181c",
    "surface2":  "#222228",
    "border":    "#2e2e36",
    "accent":    "#e8c97a",
    "accent_dk": "#b89a50",
    "danger":    "#c85a3e",
    "warn":      "#d4874a",
    "success":   "#5a9e7a",
    "blue":      "#5b8fa8",
    "text":      "#f0ede6",
    "text_mid":  "#a0a099",
    "text_dim":  "#5a5a60",
    "hoy":       "#c85a3e",
    "pronto":    "#d4874a",
    "normal":    "#5a9e7a",
    "pasado":    "#5a5a60",
}

FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_SUB    = ("Segoe UI", 11)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_TINY   = ("Segoe UI", 8)

# ─── DATA ─────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "default_alert_days": 3,
    "urgent_days":        1,
    "soon_days":          3,
    "upcoming_days":      7,
    "autostart":          True,
    "show_popup_on_start": True,
}

CATEGORIES = [
    "General", "Cumpleaños", "Aniversario", "Médico / Salud",
    "Trabajo", "Universidad", "Social / Salida",
    "Familia", "Pago / Finanzas", "Feriado", "Otro"
]

CAT_ICONS = {
    "Cumpleaños": "🎂", "Aniversario": "💍", "Médico / Salud": "🏥",
    "Trabajo": "💼", "Universidad": "📚", "Social / Salida": "🎉",
    "Familia": "👨‍👩‍👧", "Pago / Finanzas": "💳", "Feriado": "🗓",
    "General": "📌", "Otro": "⭐"
}

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_config():
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ─── DATE UTILS ───────────────────────────────────────────────────────────────

def today():
    return datetime.date.today()

def parse_date(s):
    return datetime.date.fromisoformat(s)

def next_occurrence(month, day):
    """For permanent/recurring events, returns next upcoming occurrence."""
    t = today()
    try:
        candidate = datetime.date(t.year, month, day)
    except ValueError:
        # Feb 29 etc.
        candidate = datetime.date(t.year, month, 28)
    if candidate < t:
        try:
            candidate = datetime.date(t.year + 1, month, day)
        except ValueError:
            candidate = datetime.date(t.year + 1, month, 28)
    return candidate

def days_until(rem):
    """Returns days until event. For permanent, uses next occurrence."""
    if rem.get("permanent"):
        m = rem.get("recur_month")
        d = rem.get("recur_day")
        if m and d:
            occ = next_occurrence(m, d)
            return (occ - today()).days
        return 9999
    else:
        try:
            target = parse_date(rem["date"])
            return (target - today()).days
        except Exception:
            return 9999

def get_display_date(rem):
    """Returns the date to display for this reminder."""
    if rem.get("permanent"):
        m = rem.get("recur_month")
        d = rem.get("recur_day")
        if m and d:
            return next_occurrence(m, d)
    else:
        try:
            return parse_date(rem["date"])
        except Exception:
            pass
    return today()

def urgency(rem, cfg):
    diff = days_until(rem)
    if not rem.get("permanent") and diff < 0:
        return "pasado"
    if diff == 0:
        return "hoy"
    if diff <= cfg["urgent_days"]:
        return "urgente"
    if diff <= cfg["soon_days"]:
        return "pronto"
    if diff <= cfg["upcoming_days"]:
        return "proximo"
    return "normal"

MONTHS_ES = [
    "", "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
]
DAYS_ES = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]

def fmt_date(d):
    return f"{d.day} {MONTHS_ES[d.month]} {d.year}"

def days_label(diff, permanent=False):
    if diff < 0 and not permanent:
        return f"Hace {abs(diff)} día{'s' if abs(diff)!=1 else ''}"
    if diff == 0:
        return "¡HOY!"
    if diff == 1:
        return "Mañana"
    return f"En {diff} días"

# ─── AUTOSTART ────────────────────────────────────────────────────────────────

def set_autostart(enable, app_path=None):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable and app_path:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{app_path}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        return False

def get_autostart_status():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

# ─── NOTIFICATION POPUP ───────────────────────────────────────────────────────

def show_startup_notification(root, reminders, cfg):
    """Shows a floating alert popup if there are urgent reminders."""
    alerts = []
    for r in reminders:
        diff = days_until(r)
        alert_days = r.get("alert_days", cfg["default_alert_days"])
        if r.get("permanent"):
            if diff <= alert_days:
                alerts.append((diff, r))
        else:
            if diff >= 0 and diff <= alert_days:
                alerts.append((diff, r))
            elif diff < 0 and diff >= -1:  # show "today/yesterday" for one-time too
                alerts.append((diff, r))

    if not alerts:
        return

    alerts.sort(key=lambda x: x[0])

    pop = tk.Toplevel(root)
    pop.title("⚡ Recordatorios — Agenda Personal")
    pop.configure(bg=DARK["surface"])
    pop.resizable(False, False)
    pop.attributes("-topmost", True)

    # Position bottom-right
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    pop.geometry(f"420x{min(70 + len(alerts)*62, 500)}+{sw-450}+{sh-100-min(70+len(alerts)*62,500)}")

    tk.Label(pop, text="⚡  Fechas que requieren tu atención",
             font=FONT_BOLD, bg=DARK["surface"], fg=DARK["accent"],
             pady=12, padx=16).pack(anchor="w")

    frame = tk.Frame(pop, bg=DARK["surface"])
    frame.pack(fill="both", expand=True, padx=12, pady=(0,8))

    for diff, r in alerts[:8]:
        row = tk.Frame(frame, bg=DARK["surface2"], bd=0)
        row.pack(fill="x", pady=3, ipady=8, ipadx=10)

        icon = CAT_ICONS.get(r.get("cat","General"), "📌")
        col = DARK["hoy"] if diff <= 0 else DARK["warn"] if diff <= cfg["soon_days"] else DARK["accent"]

        tk.Label(row, text=icon, font=("Segoe UI", 14),
                 bg=DARK["surface2"], fg=col).pack(side="left", padx=(8,6))

        info = tk.Frame(row, bg=DARK["surface2"])
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info, text=r["title"], font=FONT_BOLD,
                 bg=DARK["surface2"], fg=DARK["text"], anchor="w").pack(anchor="w")

        lbl = days_label(diff, r.get("permanent", False))
        if r.get("permanent"):
            lbl += f"  ·  {MONTHS_ES[r.get('recur_month',1)]} {r.get('recur_day',1)}"
        elif r.get("date"):
            lbl += f"  ·  {fmt_date(parse_date(r['date']))}"

        tk.Label(info, text=lbl, font=FONT_SMALL,
                 bg=DARK["surface2"], fg=col, anchor="w").pack(anchor="w")

    btn_frame = tk.Frame(pop, bg=DARK["surface"])
    btn_frame.pack(fill="x", padx=12, pady=(0,12))
    tk.Button(btn_frame, text="Abrir Agenda", font=FONT_SMALL,
              bg=DARK["accent"], fg="#0f0f11", bd=0, padx=12, pady=5,
              cursor="hand2", command=lambda: [pop.destroy(), root.deiconify(), root.lift()]
              ).pack(side="left")
    tk.Button(btn_frame, text="Cerrar", font=FONT_SMALL,
              bg=DARK["surface2"], fg=DARK["text_mid"], bd=0, padx=12, pady=5,
              cursor="hand2", command=pop.destroy).pack(side="left", padx=8)

# ─── MAIN APP ─────────────────────────────────────────────────────────────────

class AgendaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agenda Personal")
        self.root.configure(bg=DARK["bg"])
        self.root.geometry("1020x700")
        self.root.minsize(820, 560)

        # Icon (optional, won't crash if missing)
        try:
            self.root.iconbitmap(default="agenda.ico")
        except Exception:
            pass

        self.data = load_data()
        self.cfg  = load_config()
        self.filter_var = tk.StringVar(value="all")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.render_list())

        self._build_ui()
        self.render_list()

        # Show startup popup after a short delay
        if self.cfg.get("show_popup_on_start", True):
            self.root.after(600, lambda: show_startup_notification(self.root, self.data, self.cfg))

        # Minimize to taskbar initially (silent start)
        # Comment the next line if you want app to show on startup:
        # self.root.withdraw()

        # System tray via minimize-to-taskbar workaround
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── BUILD UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=DARK["surface"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # Main
        self.main = tk.Frame(self.root, bg=DARK["bg"])
        self.main.pack(side="left", fill="both", expand=True)

        # Notebook (pages)
        self.pages = {}
        self._build_page_list()
        self._build_page_add()
        self._build_page_settings()

        self.show_page("list")

    def _build_sidebar(self):
        tk.Label(self.sidebar, text="📅", font=("Segoe UI", 28),
                 bg=DARK["surface"], fg=DARK["accent"]).pack(pady=(24,4))
        tk.Label(self.sidebar, text="Agenda", font=("Segoe UI", 13, "bold"),
                 bg=DARK["surface"], fg=DARK["text"]).pack()
        tk.Label(self.sidebar, text="Personal", font=("Segoe UI", 9),
                 bg=DARK["surface"], fg=DARK["text_dim"]).pack(pady=(0,24))

        self.nav_btns = {}
        for key, label, icon in [
            ("list",     "Mis Recordatorios", "📋"),
            ("add",      "Agregar Nuevo",      "＋"),
            ("settings", "Configuración",      "⚙"),
        ]:
            btn = tk.Button(
                self.sidebar, text=f"  {icon}  {label}",
                font=FONT_BODY, anchor="w", bd=0,
                bg=DARK["surface"], fg=DARK["text_mid"],
                activebackground=DARK["surface2"],
                activeforeground=DARK["accent"],
                padx=16, pady=10, cursor="hand2",
                command=lambda k=key: self.show_page(k)
            )
            btn.pack(fill="x")
            self.nav_btns[key] = btn

        # Date display at bottom
        tk.Frame(self.sidebar, bg=DARK["border"], height=1).pack(fill="x", pady=20)
        t = today()
        tk.Label(self.sidebar, text=f"{t.day}", font=("Segoe UI", 32, "bold"),
                 bg=DARK["surface"], fg=DARK["accent"]).pack()
        tk.Label(self.sidebar, text=MONTHS_ES[t.month].upper(),
                 font=FONT_TINY, bg=DARK["surface"], fg=DARK["text_dim"],
                 letter_spacing=2).pack()
        tk.Label(self.sidebar, text=str(t.year),
                 font=FONT_TINY, bg=DARK["surface"], fg=DARK["text_dim"]).pack()

    def show_page(self, key):
        for k, frame in self.pages.items():
            frame.pack_forget()
        self.pages[key].pack(fill="both", expand=True, padx=20, pady=16)
        for k, btn in self.nav_btns.items():
            btn.configure(
                bg=DARK["surface2"] if k == key else DARK["surface"],
                fg=DARK["accent"] if k == key else DARK["text_mid"]
            )
        if key == "list":
            self.render_list()

    # ── PAGE: LIST ────────────────────────────────────────────────────────────

    def _build_page_list(self):
        frame = tk.Frame(self.main, bg=DARK["bg"])
        self.pages["list"] = frame

        # Header
        hdr = tk.Frame(frame, bg=DARK["bg"])
        hdr.pack(fill="x", pady=(0, 12))
        tk.Label(hdr, text="Mis Recordatorios", font=FONT_TITLE,
                 bg=DARK["bg"], fg=DARK["text"]).pack(side="left")

        # Stats bar
        self.stats_frame = tk.Frame(frame, bg=DARK["bg"])
        self.stats_frame.pack(fill="x", pady=(0,10))
        self.stat_labels = {}
        for key, label, color in [
            ("total",   "Total",          DARK["blue"]),
            ("perm",    "Permanentes",     DARK["accent"]),
            ("urgente", "Urgentes / Hoy",  DARK["danger"]),
            ("prox",    "Próximos",        DARK["warn"]),
        ]:
            card = tk.Frame(self.stats_frame, bg=DARK["surface"], padx=14, pady=10)
            card.pack(side="left", padx=(0,8))
            num = tk.Label(card, text="0", font=("Segoe UI", 20, "bold"),
                           bg=DARK["surface"], fg=color)
            num.pack()
            tk.Label(card, text=label, font=FONT_TINY,
                     bg=DARK["surface"], fg=DARK["text_dim"]).pack()
            self.stat_labels[key] = num

        # Alert banner
        self.alert_frame = tk.Frame(frame, bg="#2a1010", pady=8, padx=14)
        self.alert_lbl   = tk.Label(self.alert_frame, text="",
                                     font=FONT_SMALL, bg="#2a1010",
                                     fg=DARK["danger"], justify="left", wraplength=700)
        self.alert_lbl.pack(anchor="w")

        # Controls
        ctrl = tk.Frame(frame, bg=DARK["bg"])
        ctrl.pack(fill="x", pady=(0,8))

        tk.Entry(ctrl, textvariable=self.search_var,
                 font=FONT_BODY, bg=DARK["surface"],
                 fg=DARK["text"], insertbackground=DARK["accent"],
                 relief="flat", bd=6, width=30).pack(side="left")
        tk.Label(ctrl, text="  Buscar…  ", font=FONT_SMALL,
                 bg=DARK["bg"], fg=DARK["text_dim"]).pack(side="left")

        for val, label in [
            ("all","Todos"), ("permanent","Permanentes"), ("once","Únicos"),
            ("urgent","Urgentes"), ("upcoming","Próximos"), ("past","Pasados")
        ]:
            rb = tk.Radiobutton(ctrl, text=label, variable=self.filter_var, value=val,
                                font=FONT_SMALL, bg=DARK["bg"], fg=DARK["text_mid"],
                                selectcolor=DARK["surface2"],
                                activebackground=DARK["bg"],
                                activeforeground=DARK["accent"],
                                indicatoron=False,
                                relief="flat", padx=10, pady=4, cursor="hand2",
                                command=self.render_list)
            rb.pack(side="left", padx=2)

        # List canvas (scrollable)
        list_outer = tk.Frame(frame, bg=DARK["bg"])
        list_outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_outer, bg=DARK["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=DARK["bg"])

        self.scroll_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def render_list(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        search  = self.search_var.get().lower().strip()
        filt    = self.filter_var.get()
        t       = today()

        # Sort: permanent by next occurrence, once by date
        def sort_key(r):
            diff = days_until(r)
            if diff < 0:
                return 9999 + abs(diff)
            return diff

        items = sorted(self.data, key=sort_key)

        # Filter
        visible = []
        for r in items:
            diff = days_until(r)
            urg  = urgency(r, self.cfg)
            if search and search not in r["title"].lower() and search not in r.get("desc","").lower():
                continue
            if filt == "permanent" and not r.get("permanent"):
                continue
            if filt == "once" and r.get("permanent"):
                continue
            if filt == "urgent" and urg not in ("hoy","urgente","pronto"):
                continue
            if filt == "upcoming" and urg not in ("proximo","normal"):
                continue
            if filt == "past" and (r.get("permanent") or diff >= 0):
                continue
            visible.append(r)

        # Stats
        all_pend = [r for r in self.data if r.get("permanent") or days_until(r) >= 0]
        perms    = [r for r in self.data if r.get("permanent")]
        urgents  = [r for r in self.data if urgency(r, self.cfg) in ("hoy","urgente")]
        proximos = [r for r in self.data if urgency(r, self.cfg) in ("pronto","proximo")]
        self.stat_labels["total"].config(text=str(len(all_pend)))
        self.stat_labels["perm"].config(text=str(len(perms)))
        self.stat_labels["urgente"].config(text=str(len(urgents)))
        self.stat_labels["prox"].config(text=str(len(proximos)))

        # Alert banner
        alerts = [r for r in self.data if urgency(r, self.cfg) in ("hoy","urgente","pronto")]
        if alerts:
            lines = []
            for r in alerts[:5]:
                diff = days_until(r)
                lines.append(f"  ⚡ {r['title']}  —  {days_label(diff, r.get('permanent'))}")
            self.alert_lbl.config(text="\n".join(lines))
            self.alert_frame.pack(fill="x", pady=(0,10), before=self.canvas.master)
        else:
            self.alert_frame.pack_forget()

        if not visible:
            tk.Label(self.scroll_frame, text="\n\n🗓\n\nNo hay recordatorios en esta vista.",
                     font=FONT_SUB, bg=DARK["bg"], fg=DARK["text_dim"],
                     justify="center").pack(pady=40)
            return

        for r in visible:
            self._build_card(self.scroll_frame, r)

    def _build_card(self, parent, r):
        diff = days_until(r)
        urg  = urgency(r, self.cfg)
        icon = CAT_ICONS.get(r.get("cat","General"), "📌")

        COLOR_MAP = {
            "hoy":     DARK["hoy"],
            "urgente": DARK["hoy"],
            "pronto":  DARK["warn"],
            "proximo": DARK["accent"],
            "normal":  DARK["success"],
            "pasado":  DARK["text_dim"],
        }
        strip_color = COLOR_MAP.get(urg, DARK["text_dim"])

        outer = tk.Frame(parent, bg=DARK["bg"], pady=3)
        outer.pack(fill="x")

        card = tk.Frame(outer, bg=DARK["surface"], pady=0)
        card.pack(fill="x")

        # Color strip
        strip = tk.Frame(card, bg=strip_color, width=4)
        strip.pack(side="left", fill="y")

        # Date block
        display_date = get_display_date(r)
        date_block = tk.Frame(card, bg=DARK["surface"], width=64, padx=6, pady=10)
        date_block.pack(side="left", fill="y")
        date_block.pack_propagate(False)
        tk.Label(date_block, text=str(display_date.day),
                 font=("Segoe UI", 18, "bold"),
                 bg=DARK["surface"], fg=DARK["accent"]).pack()
        tk.Label(date_block, text=MONTHS_ES[display_date.month][:3].upper(),
                 font=FONT_TINY, bg=DARK["surface"], fg=DARK["text_dim"]).pack()
        tk.Label(date_block, text=str(display_date.year),
                 font=FONT_TINY, bg=DARK["surface"], fg=DARK["text_dim"]).pack()

        # Info
        info = tk.Frame(card, bg=DARK["surface"], pady=10, padx=10)
        info.pack(side="left", fill="both", expand=True)

        title_row = tk.Frame(info, bg=DARK["surface"])
        title_row.pack(anchor="w", fill="x")
        tk.Label(title_row, text=f"{icon}  {r['title']}",
                 font=FONT_BOLD, bg=DARK["surface"], fg=DARK["text"],
                 anchor="w").pack(side="left")

        if r.get("permanent"):
            tk.Label(title_row, text="  ♻ Permanente",
                     font=FONT_TINY, bg=DARK["surface"], fg=DARK["accent"],
                     anchor="w").pack(side="left", padx=4)

        if r.get("desc"):
            tk.Label(info, text=r["desc"], font=FONT_SMALL,
                     bg=DARK["surface"], fg=DARK["text_mid"],
                     anchor="w", wraplength=460, justify="left").pack(anchor="w")

        tags_row = tk.Frame(info, bg=DARK["surface"])
        tags_row.pack(anchor="w", pady=(4,0))

        # Category tag
        self._tag(tags_row, r.get("cat","General"), DARK["blue"])

        # Days tag
        dl = days_label(diff, r.get("permanent",False))
        self._tag(tags_row, dl, strip_color)

        # Time tag
        if r.get("time"):
            self._tag(tags_row, f"🕐 {r['time']}", DARK["text_mid"])

        # Actions
        actions = tk.Frame(card, bg=DARK["surface"], padx=10, pady=10)
        actions.pack(side="right", fill="y")
        tk.Button(actions, text="Editar", font=FONT_TINY,
                  bg=DARK["surface2"], fg=DARK["text_mid"],
                  relief="flat", padx=8, pady=4, cursor="hand2",
                  command=lambda rid=r["id"]: self.open_edit(rid)).pack(pady=2)
        tk.Button(actions, text="Eliminar", font=FONT_TINY,
                  bg=DARK["surface2"], fg=DARK["danger"],
                  relief="flat", padx=8, pady=4, cursor="hand2",
                  command=lambda rid=r["id"]: self.delete_reminder(rid)).pack(pady=2)

    def _tag(self, parent, text, color):
        tk.Label(parent, text=f" {text} ", font=FONT_TINY,
                 bg=DARK["bg"], fg=color,
                 relief="flat", padx=2, pady=2).pack(side="left", padx=2)

    # ── PAGE: ADD / EDIT ──────────────────────────────────────────────────────

    def _build_page_add(self):
        frame = tk.Frame(self.main, bg=DARK["bg"])
        self.pages["add"] = frame
        self._build_add_form(frame, editing=False)

    def _build_add_form(self, parent, editing=False, data=None):
        for w in parent.winfo_children():
            w.destroy()

        tk.Label(parent, text="Editar Recordatorio" if editing else "Nuevo Recordatorio",
                 font=FONT_TITLE, bg=DARK["bg"], fg=DARK["text"]).pack(anchor="w", pady=(0,20))

        # ─ Type selector ─
        type_frame = tk.Frame(parent, bg=DARK["bg"])
        type_frame.pack(anchor="w", pady=(0,16))
        tk.Label(type_frame, text="Tipo de recordatorio:", font=FONT_BOLD,
                 bg=DARK["bg"], fg=DARK["text_dim"]).pack(side="left")

        self.form_type = tk.StringVar(value=("permanent" if data and data.get("permanent") else "once"))
        for val, lbl, desc in [
            ("once",      "📌 Fecha única",   "Cita, tarea, evento puntual"),
            ("permanent", "♻ Permanente",      "Cumpleaños, aniversario (se repite cada año)"),
        ]:
            f = tk.Frame(type_frame, bg=DARK["surface"], padx=12, pady=8)
            f.pack(side="left", padx=8)
            rb = tk.Radiobutton(f, text=lbl, variable=self.form_type, value=val,
                                font=FONT_BOLD, bg=DARK["surface"], fg=DARK["text"],
                                selectcolor=DARK["surface2"],
                                activebackground=DARK["surface"],
                                indicatoron=True, cursor="hand2",
                                command=lambda: self._toggle_form_type(date_section, perm_section))
            rb.pack(anchor="w")
            tk.Label(f, text=desc, font=FONT_TINY, bg=DARK["surface"], fg=DARK["text_dim"]).pack(anchor="w")

        # ─ Fields ─
        fields_frame = tk.Frame(parent, bg=DARK["bg"])
        fields_frame.pack(fill="x")

        self.f_title = self._field(fields_frame, "Título *", width=50)
        self.f_desc  = self._field_text(fields_frame, "Descripción")
        self.f_cat   = self._field_combo(fields_frame, "Categoría", CATEGORIES)
        self.f_time  = self._field(fields_frame, "Hora (opcional, ej: 10:30 AM)", width=20)
        self.f_alert = self._field(fields_frame, f"Avisar con X días antes (defecto: {self.cfg['default_alert_days']})", width=8)

        # Date section (for one-time)
        date_section = tk.Frame(fields_frame, bg=DARK["bg"])
        date_section.pack(anchor="w", fill="x", pady=4)
        tk.Label(date_section, text="Fecha *", font=FONT_BOLD,
                 bg=DARK["bg"], fg=DARK["text_dim"]).pack(anchor="w")
        date_row = tk.Frame(date_section, bg=DARK["bg"])
        date_row.pack(anchor="w")

        self.f_year  = self._mini_field(date_row, "Año",  6)
        self.f_month = self._mini_field(date_row, "Mes (1-12)", 6)
        self.f_day   = self._mini_field(date_row, "Día",  5)
        tk.Label(date_row, text="  (o deja año vacío para hoy+)",
                 font=FONT_TINY, bg=DARK["bg"], fg=DARK["text_dim"]).pack(side="left")

        # Permanent section (month+day only)
        perm_section = tk.Frame(fields_frame, bg=DARK["bg"])
        tk.Label(perm_section, text="Día y mes del evento (se repetirá cada año) *",
                 font=FONT_BOLD, bg=DARK["bg"], fg=DARK["text_dim"]).pack(anchor="w")
        perm_row = tk.Frame(perm_section, bg=DARK["bg"])
        perm_row.pack(anchor="w")
        self.f_perm_month = self._mini_field(perm_row, "Mes (1-12)", 6)
        self.f_perm_day   = self._mini_field(perm_row, "Día",  5)

        # Populate if editing
        if data:
            self.f_title.insert(0, data.get("title",""))
            self.f_desc.insert("1.0", data.get("desc",""))
            self.f_cat.set(data.get("cat","General"))
            self.f_time.insert(0, data.get("time",""))
            self.f_alert.insert(0, str(data.get("alert_days","")))
            if data.get("permanent"):
                self.f_perm_month.insert(0, str(data.get("recur_month","")))
                self.f_perm_day.insert(0, str(data.get("recur_day","")))
            else:
                d = data.get("date","")
                if d:
                    parts = d.split("-")
                    if len(parts)==3:
                        self.f_year.insert(0, parts[0])
                        self.f_month.insert(0, parts[1].lstrip("0") or parts[1])
                        self.f_day.insert(0, parts[2].lstrip("0") or parts[2])

        self._toggle_form_type(date_section, perm_section)

        # Save btn
        self._editing_id = data["id"] if data else None
        self._date_section = date_section
        self._perm_section = perm_section

        btn_lbl = "Guardar Cambios" if editing else "Guardar Recordatorio"
        tk.Button(parent, text=btn_lbl, font=FONT_BOLD,
                  bg=DARK["accent"], fg="#0f0f11",
                  relief="flat", padx=20, pady=10, cursor="hand2",
                  command=self._save_form).pack(anchor="w", pady=16)

    def _toggle_form_type(self, date_section, perm_section):
        if self.form_type.get() == "once":
            perm_section.pack_forget()
            date_section.pack(anchor="w", fill="x", pady=4)
        else:
            date_section.pack_forget()
            perm_section.pack(anchor="w", fill="x", pady=4)

    def _field(self, parent, label, width=40):
        tk.Label(parent, text=label, font=FONT_BOLD,
                 bg=DARK["bg"], fg=DARK["text_dim"]).pack(anchor="w", pady=(8,2))
        e = tk.Entry(parent, font=FONT_BODY, bg=DARK["surface"],
                     fg=DARK["text"], insertbackground=DARK["accent"],
                     relief="flat", bd=6, width=width)
        e.pack(anchor="w")
        return e

    def _field_text(self, parent, label):
        tk.Label(parent, text=label, font=FONT_BOLD,
                 bg=DARK["bg"], fg=DARK["text_dim"]).pack(anchor="w", pady=(8,2))
        t = tk.Text(parent, font=FONT_BODY, bg=DARK["surface"],
                    fg=DARK["text"], insertbackground=DARK["accent"],
                    relief="flat", bd=6, width=50, height=3)
        t.pack(anchor="w")
        return t

    def _field_combo(self, parent, label, values):
        tk.Label(parent, text=label, font=FONT_BOLD,
                 bg=DARK["bg"], fg=DARK["text_dim"]).pack(anchor="w", pady=(8,2))
        v = tk.StringVar(value=values[0])
        cb = ttk.Combobox(parent, textvariable=v, values=values,
                          font=FONT_BODY, state="readonly", width=28)
        cb.pack(anchor="w")
        return v

    def _mini_field(self, parent, placeholder, width):
        f = tk.Frame(parent, bg=DARK["bg"])
        f.pack(side="left", padx=4)
        tk.Label(f, text=placeholder, font=FONT_TINY,
                 bg=DARK["bg"], fg=DARK["text_dim"]).pack()
        e = tk.Entry(f, font=FONT_BODY, bg=DARK["surface"],
                     fg=DARK["text"], insertbackground=DARK["accent"],
                     relief="flat", bd=6, width=width, justify="center")
        e.pack()
        return e

    def _save_form(self):
        title = self.f_title.get().strip()
        desc  = self.f_desc.get("1.0","end").strip()
        cat   = self.f_cat.get()
        time_ = self.f_time.get().strip()
        alert_raw = self.f_alert.get().strip()
        alert_days = int(alert_raw) if alert_raw.isdigit() else self.cfg["default_alert_days"]

        if not title:
            messagebox.showerror("Error", "El título es obligatorio."); return

        is_perm = (self.form_type.get() == "permanent")
        rec = {
            "id":         self._editing_id or (datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")),
            "title":      title,
            "desc":       desc,
            "cat":        cat,
            "time":       time_,
            "alert_days": alert_days,
            "permanent":  is_perm,
        }

        if is_perm:
            m_raw = self.f_perm_month.get().strip()
            d_raw = self.f_perm_day.get().strip()
            if not m_raw or not d_raw:
                messagebox.showerror("Error","Ingresa el mes y día del evento recurrente."); return
            try:
                m,d = int(m_raw), int(d_raw)
                assert 1<=m<=12 and 1<=d<=31
            except Exception:
                messagebox.showerror("Error","Mes o día inválido."); return
            rec["recur_month"] = m
            rec["recur_day"]   = d
            rec["date"]        = f"{today().year}-{m:02d}-{d:02d}"
        else:
            y_raw = self.f_year.get().strip()
            m_raw = self.f_month.get().strip()
            d_raw = self.f_day.get().strip()
            if not m_raw or not d_raw:
                messagebox.showerror("Error","Ingresa la fecha."); return
            try:
                y = int(y_raw) if y_raw else today().year
                m,d = int(m_raw), int(d_raw)
                date_obj = datetime.date(y, m, d)
                rec["date"] = date_obj.isoformat()
            except Exception:
                messagebox.showerror("Error","Fecha inválida."); return

        if self._editing_id:
            idx = next((i for i,r in enumerate(self.data) if r["id"]==self._editing_id), None)
            if idx is not None:
                self.data[idx] = rec
        else:
            self.data.append(rec)

        save_data(self.data)
        messagebox.showinfo("✓", f"Recordatorio guardado:\n{title}")
        self.show_page("list")
        # Reset form
        self._build_add_form(self.pages["add"], editing=False)

    # ── EDIT / DELETE ─────────────────────────────────────────────────────────

    def open_edit(self, rid):
        r = next((x for x in self.data if x["id"]==rid), None)
        if not r: return
        self._build_add_form(self.pages["add"], editing=True, data=r)
        self.show_page("add")

    def delete_reminder(self, rid):
        r = next((x for x in self.data if x["id"]==rid), None)
        if not r: return
        if messagebox.askyesno("Eliminar", f"¿Eliminar '{r['title']}'?\nEsta acción no se puede deshacer."):
            self.data = [x for x in self.data if x["id"]!=rid]
            save_data(self.data)
            self.render_list()

    # ── PAGE: SETTINGS ────────────────────────────────────────────────────────

    def _build_page_settings(self):
        frame = tk.Frame(self.main, bg=DARK["bg"])
        self.pages["settings"] = frame

        tk.Label(frame, text="Configuración", font=FONT_TITLE,
                 bg=DARK["bg"], fg=DARK["text"]).pack(anchor="w", pady=(0,20))

        def section(title):
            tk.Label(frame, text=title, font=FONT_BOLD,
                     bg=DARK["bg"], fg=DARK["accent"]).pack(anchor="w", pady=(14,4))
            sep = tk.Frame(frame, bg=DARK["border"], height=1)
            sep.pack(fill="x", pady=(0,8))

        def row(label, desc, widget_fn):
            r = tk.Frame(frame, bg=DARK["surface"], pady=10, padx=16)
            r.pack(fill="x", pady=3)
            left = tk.Frame(r, bg=DARK["surface"])
            left.pack(side="left", fill="x", expand=True)
            tk.Label(left, text=label, font=FONT_BOLD,
                     bg=DARK["surface"], fg=DARK["text"]).pack(anchor="w")
            tk.Label(left, text=desc, font=FONT_SMALL,
                     bg=DARK["surface"], fg=DARK["text_dim"]).pack(anchor="w")
            w = widget_fn(r)
            w.pack(side="right", padx=8)
            return w

        section("Alertas")
        self.cfg_default = row("Días de aviso por defecto",
            "Usado al crear si no se especifica uno",
            lambda p: self._cfg_spin(p, "default_alert_days", 0, 90))
        self.cfg_urgent = row("Urgencia máxima — días (rojo)",
            "N días o menos = URGENTE",
            lambda p: self._cfg_spin(p, "urgent_days", 0, 30))
        self.cfg_soon = row("Urgencia alta — días (naranja)",
            "N días o menos = MUY PRONTO",
            lambda p: self._cfg_spin(p, "soon_days", 0, 30))
        self.cfg_upcoming = row("Próximo — días (verde)",
            "N días o menos = PRÓXIMO",
            lambda p: self._cfg_spin(p, "upcoming_days", 0, 90))

        section("Inicio")
        self.cfg_popup_var = tk.BooleanVar(value=self.cfg.get("show_popup_on_start", True))
        row("Mostrar notificación al iniciar",
            "Popup con recordatorios urgentes al abrir la app",
            lambda p: tk.Checkbutton(p, variable=self.cfg_popup_var,
                                     bg=DARK["surface"], activebackground=DARK["surface"],
                                     selectcolor=DARK["surface2"], cursor="hand2"))

        self.cfg_autostart_var = tk.BooleanVar(value=get_autostart_status())
        row("Iniciar con Windows",
            "Abre la app automáticamente al encender la PC",
            lambda p: tk.Checkbutton(p, variable=self.cfg_autostart_var,
                                     bg=DARK["surface"], activebackground=DARK["surface"],
                                     selectcolor=DARK["surface2"], cursor="hand2"))

        section("Datos")
        btn_row = tk.Frame(frame, bg=DARK["bg"])
        btn_row.pack(anchor="w", pady=4)

        for label, cmd in [
            ("Exportar JSON", self.export_data),
            ("Importar JSON", self.import_data),
            ("Abrir carpeta de datos", lambda: os.startfile(str(APP_DIR))),
        ]:
            tk.Button(btn_row, text=label, font=FONT_SMALL,
                      bg=DARK["surface2"], fg=DARK["text_mid"],
                      relief="flat", padx=12, pady=6, cursor="hand2",
                      command=cmd).pack(side="left", padx=(0,8))

        tk.Button(frame, text="Guardar Configuración", font=FONT_BOLD,
                  bg=DARK["accent"], fg="#0f0f11",
                  relief="flat", padx=20, pady=10, cursor="hand2",
                  command=self.save_settings).pack(anchor="w", pady=16)

    def _cfg_spin(self, parent, key, mn, mx):
        var = tk.IntVar(value=self.cfg.get(key, 3))
        sb = tk.Spinbox(parent, from_=mn, to=mx, textvariable=var,
                        font=FONT_BODY, bg=DARK["surface2"], fg=DARK["text"],
                        buttonbackground=DARK["surface"],
                        relief="flat", bd=4, width=6, justify="center")
        setattr(self, f"_spin_{key}", var)
        return sb

    def save_settings(self):
        for key in ("default_alert_days","urgent_days","soon_days","upcoming_days"):
            try:
                self.cfg[key] = int(getattr(self, f"_spin_{key}").get())
            except Exception:
                pass
        self.cfg["show_popup_on_start"] = self.cfg_popup_var.get()

        autostart = self.cfg_autostart_var.get()
        self.cfg["autostart"] = autostart
        exe = sys.executable
        set_autostart(autostart, exe + f' "{os.path.abspath(__file__)}"')

        save_config(self.cfg)
        messagebox.showinfo("✓", "Configuración guardada.")
        self.render_list()

    def export_data(self):
        from tkinter.filedialog import asksaveasfilename
        path = asksaveasfilename(defaultextension=".json",
                                 filetypes=[("JSON","*.json")],
                                 initialfile=f"agenda_{today()}.json")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"reminders": self.data, "config": self.cfg}, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("✓", f"Exportado en:\n{path}")

    def import_data(self):
        from tkinter.filedialog import askopenfilename
        path = askopenfilename(filetypes=[("JSON","*.json")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                if "reminders" in obj:
                    if messagebox.askyesno("Importar", f"¿Reemplazar datos actuales con {len(obj['reminders'])} recordatorios?"):
                        self.data = obj["reminders"]
                        if "config" in obj:
                            self.cfg.update(obj["config"])
                        save_data(self.data)
                        save_config(self.cfg)
                        self.render_list()
                        messagebox.showinfo("✓","Datos importados.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo importar:\n{e}")

    def on_close(self):
        self.root.destroy()


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()

    # Dark title bar on Windows 11
    try:
        root.update()
        from ctypes import windll, byref, c_int
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        windll.dwmapi.DwmSetWindowAttribute(
            windll.user32.GetForegroundWindow(),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(c_int(1)), 4
        )
    except Exception:
        pass

    app = AgendaApp(root)
    root.mainloop()
