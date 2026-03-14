import tkinter as tk
import os
from PIL import Image, ImageTk
from src.utils.logger import logger

class FloatingIndicator:
    def __init__(self, root):
        self.root = root
        self.window = None
        self.image = None
        self.photo = None
        self._load_image()

    def _load_image(self):
        try:
            # Look for the asset in the expected directory
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            image_path = os.path.join(base_path, "assets", "floating_mic.png")

            if os.path.exists(image_path):
                # Load and resize for UI
                self.image = Image.open(image_path)
                self.image = self.image.resize((150, 80), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(self.image)
            else:
                logger.warning(f"Floating indicator image not found at {image_path}")
        except Exception as e:
            logger.error(f"Error loading floating indicator image: {e}")

    def show(self):
        if self.window is not None:
            return

        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True) # Borderless
        self.window.attributes('-topmost', True) # Always on top
        # Make transparent if possible on Mac (can use 'alpha' or transparentcolor)
        self.window.attributes('-alpha', 0.9)

        if self.photo:
            label = tk.Label(self.window, image=self.photo, bg='systemTransparent')
            label.pack()
        else:
            # Fallback text if image missing
            label = tk.Label(self.window, text="🎙️ Recording (AI)", font=("Arial", 16, "bold"), fg="white", bg="red", padx=10, pady=5)
            label.pack()

        # Position at bottom right
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # 50px padding from edges
        x = screen_width - width - 50
        y = screen_height - height - 50

        self.window.geometry(f'+{x}+{y}')

    def hide(self):
        if self.window is not None:
            self.window.destroy()
            self.window = None
