import tkinter as tk
import threading

def start_hotkeys():
    print("Starting hotkeys...")
    try:
        from pynput import keyboard
        print("Imported pynput on main thread")
    except Exception as e:
        print("Error:", e)

    def run_listener():
        try:
            print("Starting listener thread")
        except Exception as e:
            print("Error:", e)
    threading.Thread(target=run_listener, daemon=True).start()

root = tk.Tk()
root.after(1000, start_hotkeys)
root.after(2000, root.destroy)
root.mainloop()
