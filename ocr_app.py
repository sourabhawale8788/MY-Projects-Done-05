"""
=============================================================
  OCR - Optical Character Recognition System
  Digital Image Processing Project
=============================================================
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageTk
import os
import threading

# ─── Tesseract Path ──────────────────────────────────────────────────────────
# WINDOWS USERS: Uncomment and fix the line below if you get TesseractNotFound
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ─── Color Palette ──────────────────────────────────────────────────────────
BG      = "#0d1117"
PANEL   = "#161b22"
CARD    = "#21262d"
ACCENT  = "#58a6ff"
GREEN   = "#3fb950"
ORANGE  = "#f78166"
TEXT    = "#c9d1d9"
SUBTEXT = "#8b949e"
BORDER  = "#30363d"
WHITE   = "#ffffff"


# ════════════════════════════════════════════════════════════════════════════
#  PREPROCESSING PIPELINE
# ════════════════════════════════════════════════════════════════════════════

def preprocess_image(img_path, method="adaptive"):
    """
    Full preprocessing pipeline:
    1. Load image  2. Grayscale  3. Denoise  4. Threshold  5. Morphology
    """
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Cannot read image: {img_path}\nCheck the file path.")

    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    if method == "adaptive":
        processed = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 2
        )
    elif method == "otsu":
        _, processed = cv2.threshold(
            denoised, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    elif method == "global":
        _, proceussed = cv2.threshold(denoised, 127, 255, cv2.THRESH_BINARY)
    else:
        processed = denoised

    kernel    = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)

    return img, gray, processed


def extract_text(processed_img, lang="eng", psm=3):
    """Run Tesseract OCR on a preprocessed (numpy) image."""
    config  = f"--oem 3 --psm {psm}"
    pil_img = Image.fromarray(processed_img)
    text    = pytesseract.image_to_string(pil_img, lang=lang, config=config)
    return text.strip()


# ════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION GUI
# ════════════════════════════════════════════════════════════════════════════

class OCRApp(tk.Tk):
    def __init__(self):
        super().__init__()                          # ← Tk root created HERE first

        # ── Apply ttk styles AFTER Tk() is alive (fixes the blank popup bug) ──
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox",
                         fieldbackground=CARD, background=CARD,
                         foreground=TEXT, selectbackground=ACCENT)
        style.configure("TProgressbar", troughcolor=CARD, background=ACCENT)

        self.title("OCR System — Digital Image Processing")
        self.geometry("1280x800")
        self.minsize(960, 640)
        self.configure(bg=BG)

        self.img_path  = None
        self.extracted = ""
        self._tk_orig  = None   # keep PhotoImage references alive
        self._tk_proc  = None

        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg=PANEL, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍  OCR Engine",
                 font=("Courier New", 20, "bold"),
                 bg=PANEL, fg=ACCENT).pack(side="left", padx=20)
        tk.Label(hdr, text="Optical Character Recognition — Digital Image Processing",
                 font=("Courier New", 10), bg=PANEL, fg=SUBTEXT).pack(side="left")

        # ── Toolbar ──
        toolbar = tk.Frame(self, bg=CARD, pady=8, padx=12)
        toolbar.pack(fill="x")

        self._btn(toolbar, "📂  Open Image", self.open_image, ACCENT ).pack(side="left", padx=4)
        self._btn(toolbar, "⚡  Run OCR",    self.run_ocr,    GREEN  ).pack(side="left", padx=4)
        self._btn(toolbar, "💾  Save Text",  self.save_text,  ORANGE ).pack(side="left", padx=4)
        self._btn(toolbar, "🔄  Reset",      self.reset,      SUBTEXT).pack(side="left", padx=4)

        tk.Label(toolbar, text="  Method:", font=("Courier New", 10),
                 bg=CARD, fg=SUBTEXT).pack(side="left", padx=(20, 4))
        self.method_var = tk.StringVar(value="adaptive")
        ttk.Combobox(toolbar, textvariable=self.method_var, width=12,
                     values=["adaptive", "otsu", "global", "none"],
                     state="readonly").pack(side="left")

        tk.Label(toolbar, text="  PSM:", font=("Courier New", 10),
                 bg=CARD, fg=SUBTEXT).pack(side="left", padx=(14, 4))
        self.psm_var = tk.StringVar(value="3")
        ttk.Combobox(toolbar, textvariable=self.psm_var, width=5,
                     values=["3", "6", "7", "11", "13"],
                     state="readonly").pack(side="left")

        self.status_var = tk.StringVar(value="● Idle — load an image to begin")
        tk.Label(toolbar, textvariable=self.status_var,
                 font=("Courier New", 9), bg=CARD, fg=SUBTEXT).pack(side="right", padx=12)

        # ── Progress bar (hidden until needed) ──
        self.progress = ttk.Progressbar(self, mode="indeterminate")

        # ── Stats bar ──
        self.stats_var = tk.StringVar(value="Words: 0   |   Characters: 0   |   Lines: 0")
        tk.Label(self, textvariable=self.stats_var,
                 font=("Courier New", 9), bg=PANEL, fg=SUBTEXT, pady=4
                 ).pack(fill="x", side="bottom")

        # ── Main 3-panel layout ──
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=8)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.columnconfigure(2, weight=2)
        main.rowconfigure(0, weight=1)

        self.orig_panel = self._image_panel(main, "📷  Original Image",    col=0)
        self.proc_panel = self._image_panel(main, "🔧  Preprocessed Image", col=1)

        # Text panel
        right = tk.Frame(main, bg=CARD, bd=0,
                         highlightthickness=1, highlightbackground=BORDER)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        tk.Label(right, text="📝  Extracted Text",
                 font=("Courier New", 11, "bold"),
                 bg=CARD, fg=TEXT, pady=8).pack()
        self.text_box = scrolledtext.ScrolledText(
            right, wrap=tk.WORD, font=("Courier New", 11),
            bg=BG, fg=TEXT, insertbackground=ACCENT,
            selectbackground=ACCENT, relief="flat", padx=10, pady=8
        )
        self.text_box.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _btn(self, parent, label, cmd, color):
        fg = BG if color == SUBTEXT else WHITE
        return tk.Button(parent, text=label, command=cmd,
                         font=("Courier New", 10, "bold"),
                         bg=color, fg=fg, activebackground=color,
                         relief="flat", padx=10, pady=5, cursor="hand2")

    def _image_panel(self, parent, title, col):
        frame = tk.Frame(parent, bg=CARD, bd=0,
                         highlightthickness=1, highlightbackground=BORDER)
        frame.grid(row=0, column=col, sticky="nsew",
                   padx=(0 if col == 0 else 4, 0))
        tk.Label(frame, text=title, font=("Courier New", 11, "bold"),
                 bg=CARD, fg=TEXT, pady=8).pack()
        lbl = tk.Label(frame, bg=BG,
                       text="No image\nloaded", fg=SUBTEXT,
                       font=("Courier New", 10))
        lbl.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        return lbl

    def _set_status(self, msg, color=SUBTEXT):
        self.status_var.set(f"● {msg}")

    # ── Core Actions ─────────────────────────────────────────────────────────
    def open_image(self):
        # FIX: pass parent=self so the dialog is attached to our window,
        #      not a new implicit Tk root.
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.webp"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        self.img_path = path
        self._set_status(f"Loaded: {os.path.basename(path)}", ACCENT)

        # FIX: open with PIL directly (works for all formats) instead of cv2
        try:
            pil_img = Image.open(path).convert("RGB")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image:\n{e}", parent=self)
            return

        # Use after() so the window has finished drawing before we measure it
        self.after(50, lambda: self._show_image(pil_img, self.orig_panel, "_tk_orig"))

        # Clear previous results
        self.text_box.delete("1.0", tk.END)
        self.proc_panel.config(image="", text="Run OCR to\npreprocess", fg=SUBTEXT)
        self.stats_var.set("Words: 0   |   Characters: 0   |   Lines: 0")

    def run_ocr(self):
        if not self.img_path:
            messagebox.showwarning("No Image", "Please load an image first!", parent=self)
            return
        self._set_status("Processing…",ORANGE)
        self.progress.pack(fill="x", padx=10, pady=(0, 4))
        self.progress.start(10)
        threading.Thread(target=self._ocr_worker, daemon=True).start()

    def _ocr_worker(self):
        try:
            method = self.method_var.get()
            psm    = int(self.psm_var.get())
            _orig, _gray, processed = preprocess_image(self.img_path, method)
            text = extract_text(processed, psm=psm)
            self.after(0, lambda: self._update_results(processed, text))
        except Exception as e:
            self.after(0, lambda err=e: self._ocr_error(str(err)))

    def _update_results(self, processed, text):
        self.progress.stop()
        self.progress.pack_forget()

        proc_pil = Image.fromarray(processed)
        self.after(50, lambda: self._show_image(proc_pil, self.proc_panel, "_tk_proc"))

        self.extracted = text
        self.text_box.delete("1.0", tk.END)
        if text:
            self.text_box.insert(tk.END, text)
        else:
            self.text_box.insert(tk.END,
                "⚠  No text detected.\n\n"
                "Tips:\n"
                "  • Try Method = adaptive\n"
                "  • Try PSM = 6 or 11\n"
                "  • Use a higher-resolution image\n"
                "  • Ensure good contrast")

        words = len(text.split())
        chars = len(text)
        lines = len(text.splitlines())
        self.stats_var.set(f"Words: {words}   |   Characters: {chars}   |   Lines: {lines}")
        self._set_status("OCR complete ✓", GREEN)

    def _ocr_error(self, err):
        self.progress.stop()
        self.progress.pack_forget()
        self._set_status(f"Error: {err}", ORANGE)
        messagebox.showerror(
            "OCR Error",
            f"{err}\n\n"
            "Common fixes:\n"
            "• Install Tesseract OCR (see README)\n"
            "• Windows: uncomment tesseract_cmd line at top of ocr_app.py\n"
            "• Linux: sudo apt install tesseract-ocr\n"
            "• Mac:   brew install tesseract",
            parent=self
        )

    def save_text(self):
        if not self.extracted:
            messagebox.showinfo("Nothing to Save", "Run OCR first to extract text.",
                                parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.extracted)
            messagebox.showinfo("Saved", f"Text saved to:\n{path}", parent=self)

    def reset(self):
        self.img_path  = None
        self.extracted = ""
        self._tk_orig  = None
        self._tk_proc  = None
        self.orig_panel.config(image="", text="No image\nloaded", fg=SUBTEXT)
        self.proc_panel.config(image="", text="No image\nloaded", fg=SUBTEXT)
        self.text_box.delete("1.0", tk.END)
        self.stats_var.set("Words: 0   |   Characters: 0   |   Lines: 0")
        self._set_status("Reset — load an image to begin")

    # ── Image display helper ──────────────────────────────────────────────────
    def _show_image(self, pil_img, label, ref_attr):
        """
        FIX: measure panel size AFTER the window is drawn, then scale the image.
        ref_attr is the instance attribute name used to keep the PhotoImage alive.
        """
        label.update_idletasks()
        w = label.winfo_width()
        h = label.winfo_height()

        # Reliable fallback if window not yet fully drawn
        if w < 20:
            w = 360
        if h < 20:
            h = 520

        ratio = min(w / pil_img.width, h / pil_img.height, 1.0)
        new_w = max(1, int(pil_img.width  * ratio))
        new_h = max(1, int(pil_img.height * ratio))

        resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        tk_img  = ImageTk.PhotoImage(resized)

        # Store reference on self so it doesn't get garbage-collected
        setattr(self, ref_attr, tk_img)

        label.config(image=tk_img, text="")
        label.image = tk_img   # belt-and-braces second reference


# ════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # FIX: create OCRApp FIRST (which calls tk.Tk()), then style is applied
    #      inside __init__.  Never call ttk.Style() before tk.Tk() exists —
    #      that auto-creates a hidden root and causes the blank "tk" popup.
    app = OCRApp()
    app.mainloop()