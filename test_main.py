import subprocess
import time
import os
import signal

# Make sure X11 is running
os.system("Xvfb :2 -screen 0 1024x768x24 &")
os.environ["DISPLAY"] = ":2"

print("Starting Voice2Text...")
proc = subprocess.Popen(["./run.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

start_time = time.time()
output = []
success = False

while time.time() - start_time < 10:
    line = proc.stdout.readline()
    if line:
        print(line.strip())
        output.append(line.strip())
        if "Starting Reliable Toggle Hotkey Listener" in line:
            # wait a bit more to see if it crashes
            time.sleep(2)
            if proc.poll() is None:
                success = True
            break
    if proc.poll() is not None:
        break

if proc.poll() is None:
    proc.terminate()
    proc.wait()

for line in proc.stdout.readlines():
    print(line.strip())
    output.append(line.strip())

if any("Trace/BPT trap" in line for line in output):
    print("FAILED: BPT trap still present")
elif success:
    print("SUCCESS: Started without BPT trap")
else:
    print("FAILED: Did not see hotkey listener start or process exited early")
