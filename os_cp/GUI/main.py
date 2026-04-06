# main.py
import customtkinter as ctk
from ui.app_window import MainView

# Set the global appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class CacheSimGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Cache Simulator Workbench")
        self.geometry("1300x820")
        self.minsize(1100, 720)

        # Inject the MainView UI
        self.main_view = MainView(self)
        self.main_view.pack(fill="both", expand=True)

        # Default to full screen on launch.
        self.after(50, self._enable_default_fullscreen)
        self.bind("<Escape>", lambda _event: self.attributes("-fullscreen", False))
        self.bind("<F11>", self._toggle_fullscreen)

    def _enable_default_fullscreen(self):
        try:
            self.attributes("-fullscreen", True)
        except Exception:
            try:
                self.state("zoomed")
            except Exception:
                pass

    def _toggle_fullscreen(self, _event=None):
        try:
            is_fullscreen = bool(self.attributes("-fullscreen"))
            self.attributes("-fullscreen", not is_fullscreen)
        except Exception:
            pass

if __name__ == "__main__":
    app = CacheSimGUI()
    app.mainloop()