"""
Actualizar Agenda Personal
==========================
Doble clic (o arrastrar) para actualizar agenda.py desde GitHub.

Uso:
  - Doble clic en el archivo  →  descarga e instala la última versión
  - También puede ejecutarse desde consola: python actualizar_agenda.py

Configuración:
  Edita las constantes RAW_URL y LOCAL_FILE según tu proyecto.
"""

import sys
import os
import shutil
import urllib.request
import urllib.error
import json
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import hashlib
import subprocess

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN  ←  Edita esto con tu repositorio
# ─────────────────────────────────────────────────────────────────────────────

GITHUB_USER   = "MasteryShoot"           # ← tu usuario de GitHub
GITHUB_REPO   = "Agenda-Personal"      # ← nombre del repositorio
GITHUB_BRANCH = "main"                 # ← rama principal

# URL del archivo principal en GitHub (raw)
RAW_URL = (
    f"https://raw.githubusercontent.com/MasteryShoot/Agenda-Personal/refs/heads/main/agenda.py?token=GHSAT0AAAAAAD4WKV4SBEB4XWL5OHFIZQVU2P7Y7UA"
    f"{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/agenda.py"
)

# URL del archivo de versión (opcional: un version.json en tu repo)
VERSION_URL = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.json"
)

# Ruta local del script principal
LOCAL_FILE = Path(__file__).parent / "agenda.py"

# Carpeta de backups
BACKUP_DIR  = Path(os.environ.get("APPDATA", ".")) / "AgendaPersonal" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────

DARK = {
    "bg":       "#0f0f11",
    "surface":  "#18181c",
    "surface2": "#222228",
    "border":   "#2e2e36",
    "accent":   "#e8c97a",
    "danger":   "#c85a3e",
    "success":  "#5a9e7a",
    "text":     "#f0ede6",
    "text_mid": "#a0a099",
    "text_dim": "#5a5a60",
}

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO  = ("Consolas", 9)


# ─────────────────────────────────────────────────────────────────────────────
# LÓGICA DE ACTUALIZACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_url(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "AgendaUpdater/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_remote_version() -> dict:
    """Intenta leer version.json del repo. Devuelve {} si no existe."""
    try:
        data = fetch_url(VERSION_URL)
        return json.loads(data.decode("utf-8"))
    except Exception:
        return {}


def backup_current() -> Path | None:
    """Hace backup del archivo local antes de actualizar."""
    if not LOCAL_FILE.exists():
        return None
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"agenda_{ts}.py.bak"
    shutil.copy2(LOCAL_FILE, dest)
    # Mantener solo los últimos 10 backups
    baks = sorted(BACKUP_DIR.glob("*.bak"), key=lambda p: p.stat().st_mtime)
    for old in baks[:-10]:
        old.unlink(missing_ok=True)
    return dest


def check_for_updates() -> dict:
    """
    Compara hash local vs remoto.
    Retorna dict con keys: up_to_date, remote_content, remote_version, local_hash, remote_hash, error
    """
    result = {
        "up_to_date":      False,
        "remote_content":  None,
        "remote_version":  {},
        "local_hash":      None,
        "remote_hash":     None,
        "error":           None,
    }
    try:
        remote_content      = fetch_url(RAW_URL)
        result["remote_content"] = remote_content
        result["remote_hash"]    = sha256_bytes(remote_content)

        if LOCAL_FILE.exists():
            result["local_hash"] = sha256_file(LOCAL_FILE)
            result["up_to_date"] = result["local_hash"] == result["remote_hash"]
        else:
            result["up_to_date"] = False   # no existe → instalar

        result["remote_version"] = get_remote_version()

    except urllib.error.URLError as e:
        result["error"] = f"Sin conexión o URL inválida:\n{e.reason}"
    except Exception as e:
        result["error"] = str(e)

    return result


def apply_update(remote_content: bytes) -> tuple[bool, str]:
    """Escribe el nuevo archivo. Retorna (éxito, mensaje)."""
    backup_path = backup_current()
    try:
        LOCAL_FILE.write_bytes(remote_content)
        msg = "✓ Actualización aplicada correctamente."
        if backup_path:
            msg += f"\nBackup guardado en:\n{backup_path}"
        return True, msg
    except PermissionError:
        return False, "Error de permisos al escribir el archivo.\nCierra la app antes de actualizar."
    except Exception as e:
        # Intentar restaurar backup si falló
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, LOCAL_FILE)
            except Exception:
                pass
        return False, f"Error al aplicar la actualización:\n{e}"


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

class UpdaterApp:
    def __init__(self, root: tk.Tk):
        self.root  = root
        self.root.title("Actualizador — Agenda Personal")
        self.root.configure(bg=DARK["bg"])
        self.root.geometry("520x420")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # Intentar ícono
        try:
            ico = Path(__file__).parent / "agenda.ico"
            if ico.exists():
                self.root.iconbitmap(str(ico))
        except Exception:
            pass

        # Centrar ventana
        self.root.update_idletasks()
        w, h = 520, 420
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._build_ui()
        # Arrancar verificación automáticamente
        self.root.after(300, self._start_check)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=DARK["surface"], pady=16, padx=24)
        hdr.pack(fill="x")

        tk.Label(hdr, text="📅", font=("Segoe UI", 26),
                 bg=DARK["surface"], fg=DARK["accent"]).pack(side="left", padx=(0, 12))
        info = tk.Frame(hdr, bg=DARK["surface"])
        info.pack(side="left")
        tk.Label(info, text="Agenda Personal — Actualizador",
                 font=FONT_TITLE, bg=DARK["surface"], fg=DARK["text"]).pack(anchor="w")
        tk.Label(info, text=f"Archivo: {LOCAL_FILE}",
                 font=FONT_SMALL, bg=DARK["surface"], fg=DARK["text_dim"],
                 wraplength=380, justify="left").pack(anchor="w")

        tk.Frame(self.root, bg=DARK["border"], height=1).pack(fill="x")

        # Status area
        body = tk.Frame(self.root, bg=DARK["bg"], padx=24, pady=18)
        body.pack(fill="both", expand=True)

        # Estado
        self.status_icon = tk.Label(body, text="⏳", font=("Segoe UI", 32),
                                     bg=DARK["bg"], fg=DARK["accent"])
        self.status_icon.pack(pady=(0, 6))

        self.status_lbl = tk.Label(body, text="Verificando actualizaciones…",
                                    font=FONT_BOLD, bg=DARK["bg"], fg=DARK["text"])
        self.status_lbl.pack()

        self.detail_lbl = tk.Label(body, text="",
                                    font=FONT_SMALL, bg=DARK["bg"], fg=DARK["text_mid"],
                                    wraplength=460, justify="center")
        self.detail_lbl.pack(pady=(4, 0))

        # Progress bar
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Gold.Horizontal.TProgressbar",
                         troughcolor=DARK["surface2"],
                         background=DARK["accent"],
                         darkcolor=DARK["accent"],
                         lightcolor=DARK["accent"],
                         bordercolor=DARK["surface2"])
        self.progress = ttk.Progressbar(body, mode="indeterminate", length=380,
                                         style="Gold.Horizontal.TProgressbar")
        self.progress.pack(pady=16)

        # Hash info
        self.hash_frame = tk.Frame(body, bg=DARK["surface"], padx=12, pady=8)
        self._hash_local  = self._hash_row(self.hash_frame, "Local: ")
        self._hash_remote = self._hash_row(self.hash_frame, "Remoto:")

        # Buttons
        btn_frame = tk.Frame(self.root, bg=DARK["surface"], pady=12, padx=24)
        btn_frame.pack(fill="x", side="bottom")

        self.btn_update = tk.Button(btn_frame, text="Actualizar ahora",
                                     font=FONT_BOLD,
                                     bg=DARK["accent"], fg="#0f0f11",
                                     relief="flat", padx=18, pady=8,
                                     cursor="hand2", state="disabled",
                                     command=self._do_update)
        self.btn_update.pack(side="left")

        self.btn_open = tk.Button(btn_frame, text="Abrir Agenda",
                                   font=FONT_SMALL,
                                   bg=DARK["surface2"], fg=DARK["text_mid"],
                                   relief="flat", padx=14, pady=8,
                                   cursor="hand2", state="disabled",
                                   command=self._open_app)
        self.btn_open.pack(side="left", padx=8)

        tk.Button(btn_frame, text="Cerrar",
                  font=FONT_SMALL,
                  bg=DARK["surface2"], fg=DARK["text_dim"],
                  relief="flat", padx=14, pady=8,
                  cursor="hand2",
                  command=self.root.destroy).pack(side="right")

        self.btn_recheck = tk.Button(btn_frame, text="↻ Re-verificar",
                                      font=FONT_SMALL,
                                      bg=DARK["surface2"], fg=DARK["text_mid"],
                                      relief="flat", padx=14, pady=8,
                                      cursor="hand2",
                                      command=self._start_check)
        self.btn_recheck.pack(side="right", padx=8)

        # Guardar resultado para el update
        self._check_result = None

    def _hash_row(self, parent, label):
        row = tk.Frame(parent, bg=DARK["surface"])
        row.pack(anchor="w", fill="x")
        tk.Label(row, text=label, font=FONT_MONO,
                 bg=DARK["surface"], fg=DARK["text_dim"], width=8).pack(side="left")
        val = tk.Label(row, text="—", font=FONT_MONO,
                       bg=DARK["surface"], fg=DARK["text_mid"])
        val.pack(side="left")
        return val

    # ── CHECK FLOW ────────────────────────────────────────────────────────────

    def _start_check(self):
        self._set_state_checking()
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        result = check_for_updates()
        self.root.after(0, lambda: self._on_check_done(result))

    def _on_check_done(self, result: dict):
        self.progress.stop()
        self.progress.pack_forget()
        self._check_result = result

        if result["error"]:
            self._set_state_error(result["error"])
            return

        # Mostrar hashes
        lh = result["local_hash"]
        rh = result["remote_hash"]
        self._hash_local.config(text=lh[:16] + "…" if lh else "No encontrado")
        self._hash_remote.config(text=rh[:16] + "…" if rh else "—")
        self.hash_frame.pack(pady=(0, 8))

        # Versión remota
        ver = result["remote_version"]
        ver_str = ver.get("version", "")
        date_str = ver.get("date", "")
        notes = ver.get("notes", "")

        if result["up_to_date"]:
            self._set_state_ok(ver_str, date_str)
        else:
            self._set_state_update_available(ver_str, date_str, notes)

    # ── UPDATE FLOW ───────────────────────────────────────────────────────────

    def _do_update(self):
        if not self._check_result or not self._check_result.get("remote_content"):
            messagebox.showerror("Error", "No hay datos remotos descargados.\nRe-verifica primero.")
            return

        self.btn_update.config(state="disabled", text="Actualizando…")
        self.status_lbl.config(text="Aplicando actualización…")

        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        ok, msg = apply_update(self._check_result["remote_content"])
        self.root.after(0, lambda: self._on_update_done(ok, msg))

    def _on_update_done(self, ok: bool, msg: str):
        if ok:
            self.status_icon.config(text="✅", fg=DARK["success"])
            self.status_lbl.config(text="¡Actualización completada!", fg=DARK["success"])
            self.detail_lbl.config(text=msg)
            self.btn_open.config(state="normal")
            self.btn_update.config(text="✓ Actualizado", state="disabled",
                                    bg=DARK["surface2"], fg=DARK["text_dim"])
        else:
            self.status_icon.config(text="❌", fg=DARK["danger"])
            self.status_lbl.config(text="Error al actualizar", fg=DARK["danger"])
            self.detail_lbl.config(text=msg)
            self.btn_update.config(state="normal", text="Reintentar")

    def _open_app(self):
        if LOCAL_FILE.exists():
            try:
                subprocess.Popen([sys.executable, str(LOCAL_FILE)],
                                  creationflags=subprocess.CREATE_NO_WINDOW
                                  if sys.platform == "win32" else 0)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la app:\n{e}")
        else:
            messagebox.showerror("Error", f"No se encontró:\n{LOCAL_FILE}")

    # ── STATES ────────────────────────────────────────────────────────────────

    def _set_state_checking(self):
        self.hash_frame.pack_forget()
        self.progress.pack(pady=16)
        self.progress.start(12)
        self.status_icon.config(text="⏳", fg=DARK["accent"])
        self.status_lbl.config(text="Verificando actualizaciones…", fg=DARK["text"])
        self.detail_lbl.config(text="Conectando con el repositorio…", fg=DARK["text_mid"])
        self.btn_update.config(state="disabled")
        self.btn_open.config(state="disabled")
        self._check_result = None

    def _set_state_ok(self, ver="", date=""):
        self.status_icon.config(text="✅", fg=DARK["success"])
        self.status_lbl.config(text="Estás al día", fg=DARK["success"])
        extra = f"v{ver}" if ver else ""
        if date:
            extra += f"  ·  {date}"
        self.detail_lbl.config(
            text=f"No hay actualizaciones disponibles.  {extra}".strip(),
            fg=DARK["text_mid"]
        )
        self.btn_open.config(state="normal")
        self.btn_update.config(state="disabled", bg=DARK["surface2"], fg=DARK["text_dim"],
                                text="Sin actualizaciones")

    def _set_state_update_available(self, ver="", date="", notes=""):
        self.status_icon.config(text="🔄", fg=DARK["accent"])
        self.status_lbl.config(text="¡Nueva versión disponible!", fg=DARK["accent"])
        detail_parts = []
        if ver:
            detail_parts.append(f"v{ver}")
        if date:
            detail_parts.append(date)
        if notes:
            detail_parts.append(notes)
        self.detail_lbl.config(
            text="  ·  ".join(detail_parts) if detail_parts else "Hay cambios disponibles en el repositorio.",
            fg=DARK["text_mid"]
        )
        self.btn_update.config(state="normal",
                                bg=DARK["accent"], fg="#0f0f11",
                                text="⬇  Actualizar ahora")
        self.btn_open.config(state="normal")

    def _set_state_error(self, msg: str):
        self.status_icon.config(text="⚠️", fg=DARK["danger"])
        self.status_lbl.config(text="No se pudo verificar", fg=DARK["danger"])
        self.detail_lbl.config(text=msg, fg=DARK["text_dim"])
        self.btn_update.config(state="disabled", text="Sin conexión",
                                bg=DARK["surface2"], fg=DARK["text_dim"])
        self.btn_open.config(state="normal" if LOCAL_FILE.exists() else "disabled")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()

    # Barra de título oscura en Windows 11
    try:
        root.update()
        from ctypes import windll, byref, c_int
        windll.dwmapi.DwmSetWindowAttribute(
            windll.user32.GetForegroundWindow(),
            20, byref(c_int(1)), 4
        )
    except Exception:
        pass

    app = UpdaterApp(root)
    root.mainloop()
