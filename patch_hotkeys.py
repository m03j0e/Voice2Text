with open("src/input/hotkeys.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "logger.info(\"Starting Reliable Toggle Hotkey Listener (pynput) in background thread...\")" in line:
        new_lines.append(line)
        new_lines.append("        try:\n")
        new_lines.append("            import pynput\n")
        new_lines.append("            from pynput import keyboard\n")
        new_lines.append("        except Exception as e:\n")
        new_lines.append("            logger.error(f\"Failed to import pynput on main thread: {e}\")\n")
        new_lines.append("            return\n")
    else:
        new_lines.append(line)

with open("src/input/hotkeys.py", "w") as f:
    f.writelines(new_lines)
