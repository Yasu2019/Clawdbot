
import os
import pty
import time

code = "nhPCQ00c4O2FIzXJQXQtSZN7gFk7EF67dtPMjwiGAAKkKH6I#aExDdtJPngOIotFkrkrZeFX4Z9V6scuV4CYJ8U0EVdU"

def master_read(fd):
    data = os.read(fd, 1024)
    return data

print("Starting claude auth login with PTY...")

pid, fd = pty.fork()

if pid == 0:
    # Child process
    os.execlp("claude", "claude", "auth", "login")
else:
    # Parent process
    time.sleep(5) # Wait for "Visit..." prompt
    
    print(f"Sending code to fd {fd}...")
    os.write(fd, (code + "\n").encode())
    
    # Read output for a bit to ensure it processed
    try:
        while True:
            data = os.read(fd, 1024)
            if not data:
                break
            print(data.decode(), end="")
            if b"Success" in data or b"Successfully" in data:
                break
            time.sleep(0.1)
    except OSError:
        pass
        
    print("\nDone.")
