import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import requests
import hashlib
import json
from pathlib import Path
import threading

BASE = "https://lrclib.net"


# ===== LRCLib API =====
def get_challenge():
    r = requests.post(f"{BASE}/api/request-challenge", timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["prefix"], data["target"]


def solve_pow(prefix, target, status_cb):
    target_int = int(target, 16)
    nonce = 0
    while True:
        if nonce % 4000 == 0:
            status_cb(f"⚙️ Proof-of-Work… {nonce}")
        h = hashlib.sha256(f"{prefix}{nonce}".encode("utf-8")).hexdigest()
        if int(h, 16) < target_int:
            return nonce
        nonce += 1


# ===== UI =====
class SpotifyUploader(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("LRCLIB Lyrics Upload Helper")
        self.geometry("600x800")
        self.configure(bg="#121212")
        self.resizable(False, False)

        self.lrc_path = None

        self._style()
        self._ui()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "TEntry",
            fieldbackground="#1e1e1e",
            foreground="white",
            borderwidth=0,
            padding=10
        )

        style.configure(
            "TButton",
            background="#1DB954",
            foreground="black",
            font=("Segoe UI", 10, "bold"),
            padding=12
        )

        style.map(
            "TButton",
            background=[("active", "#1ed760")]
        )

        style.configure(
            "TLabel",
            background="#121212",
            foreground="#b3b3b3",
            font=("Segoe UI", 10)
        )

    def _ui(self):
        main = tk.Frame(self, bg="#121212")
        main.pack(fill="both", expand=True, padx=30, pady=30)

        tk.Label(
            main,
            text="LRCLIB Lyrics Upload Helper",
            font=("Segoe UI", 22, "bold"),
            fg="white",
            bg="#121212"
        ).pack(anchor="w", pady=(0, 25))

        self.entries = {}
        for label in ["Track Name", "Artist Name", "Album Name", "Duration (sec)"]:
            tk.Label(main, text=label, bg="#121212", fg="#b3b3b3").pack(anchor="w")
            e = ttk.Entry(main)
            e.pack(fill="x", pady=(5, 15))
            self.entries[label] = e

        # Drag & Drop / Click Field
        self.drop = tk.Label(
            main,
            text="Drag & Drop LRC here\nor click to browse",
            bg="#1e1e1e",
            fg="#1DB954",
            font=("Segoe UI", 12),
            height=5,
            cursor="hand2"
        )
        self.drop.pack(fill="x", pady=20)

        self.drop.drop_target_register(DND_FILES)
        self.drop.dnd_bind("<<Drop>>", self.on_drop)
        self.drop.bind("<Button-1>", self.open_file_dialog)

        self.status = tk.Label(
            main,
            text="",
            fg="#1DB954",
            bg="#121212",
            font=("Segoe UI", 10)
        )
        self.status.pack(anchor="w", pady=10)

        ttk.Button(
            main,
            text="UPLOAD TO LRCLIB",
            command=self.start_upload
        ).pack(fill="x", pady=10)

    # ===== EVENTS =====
    def open_file_dialog(self, event=None):
        path = filedialog.askopenfilename(
            filetypes=[("LRC Files", "*.lrc")]
        )
        if path:
            self.lrc_path = Path(path)
            self.drop.config(text=f"✅ {self.lrc_path.name}")

    def on_drop(self, event):
        path = event.data.strip("{}")
        if path.lower().endswith(".lrc"):
            self.lrc_path = Path(path)
            self.drop.config(text=f"✅ {self.lrc_path.name}")
        else:
            messagebox.showerror("Error", "Please drop a .lrc file")

    def set_status(self, text):
        self.status.config(text=text)
        self.update_idletasks()

    def start_upload(self):
        threading.Thread(target=self.upload, daemon=True).start()

    def upload(self):
        try:
            if not self.lrc_path:
                messagebox.showerror("Error", "No LRC file selected")
                return

            track = self.entries["Track Name"].get()
            artist = self.entries["Artist Name"].get()
            album = self.entries["Album Name"].get()
            duration = int(self.entries["Duration (sec)"].get())
            lyrics = self.lrc_path.read_text(encoding="utf-8")

            self.set_status("🔐 Requesting challenge…")
            prefix, target = get_challenge()

            self.set_status("⚙️ Solving Proof-of-Work…")
            nonce = solve_pow(prefix, target, self.set_status)
            token = f"{prefix}:{nonce}"

            payload = {
                "trackName": track,
                "artistName": artist,
                "albumName": album,
                "duration": duration,
                "plainLyrics": "",
                "syncedLyrics": lyrics
            }

            self.set_status("⬆️ Uploading lyrics…")
            r = requests.post(
                f"{BASE}/api/publish",
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-Publish-Token": token
                },
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=30
            )

            if r.status_code == 201:
                self.set_status("✅ Upload successful")
                messagebox.showinfo("Success", "Lyrics uploaded successfully 🎉")
            else:
                raise Exception(f"{r.status_code}\n{r.text}")

        except Exception as e:
            self.set_status("❌ Upload failed")
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    SpotifyUploader().mainloop()
