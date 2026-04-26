import os
import subprocess
import time

audio_dir = r"D:\Clawdbot_Docker_20260125\data\workspace\iatf_training\audio\tpm"
remotion_dir = r"D:\Clawdbot_Docker_20260125\data\workspace\iatf_training\tpm_video"
expected_files = 14

def check_files():
    files = [f for f in os.listdir(audio_dir) if f.endswith(".wav")]
    return len(files)

def run_render():
    print("All audio files ready. Updating scenes.json...")
    subprocess.run(["python", r"D:\Clawdbot_Docker_20260125\scratch\generate_scenes_json.py"], check=True)
    
    print("Starting Remotion render...")
    # Using 'start /low' to ensure it runs at idle priority
    cmd = f"npx remotion render src/index.ts TPMAudit out/tpm_audit.mp4"
    print(f"Executing: {cmd}")
    
    # We use subprocess.run with idle priority if possible, or just normal and let the OS handle it
    # On Windows, we can use 'start /low /wait'
    full_cmd = f"start /low /wait cmd /c \"{cmd}\""
    subprocess.run(full_cmd, shell=True, cwd=remotion_dir)
    
    print("Render complete!")

def main():
    while True:
        count = check_files()
        print(f"Progress: {count}/{expected_files} files generated.")
        if count >= expected_files:
            run_render()
            break
        time.sleep(30)

if __name__ == "__main__":
    main()
