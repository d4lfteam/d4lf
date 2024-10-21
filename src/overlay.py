import logging
import threading
import tkinter as tk

LOGGER = logging.getLogger(__name__)

LOCK = threading.Lock()


class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")
        self.root.attributes("-alpha", 1.0)
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.config(height=self.root.winfo_screenheight(), width=self.root.winfo_screenwidth())

    def run(self):
        self.root.mainloop()
