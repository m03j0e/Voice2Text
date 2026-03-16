import tkinter as tk
import threading
import time

def start_hotkeys():
    print("Starting hotkeys...")
    def run_listener():
        try:
            from pynput import keyboard
            print("Imported pynput")
        except Exception as e:
            print("Error:", e)
    threading.Thread(target=run_listener, daemon=True).start()

root = tk.Tk()
root.after(1000, start_hotkeys)
root.after(3000, root.destroy)
root.mainloop()
