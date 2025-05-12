# run_ariana_launcher.py
import sys
import subprocess

# The arguments to this script will be the command that ariana needs to run,
# e.g., ["python", "-m", "albumexplore.gui.app"] or ["python", "your_script.py"]
ariana_target_command = sys.argv[1:]

# Construct the full command: ariana python -m albumexplore.gui.app
command_to_run = ["ariana"] + ariana_target_command

print(f"[ArianaLauncher] Executing: {' '.join(command_to_run)}", flush=True)

try:
    # Execute the command. Output will go to the console.
    # check=True will raise a CalledProcessError if ariana returns a non-zero exit code.
    process_result = subprocess.run(command_to_run, check=False, text=True, capture_output=False) # Let output flow

    if process_result.returncode != 0:
        print(f"[ArianaLauncher] Error: '{' '.join(command_to_run)}' failed with exit code {process_result.returncode}.", file=sys.stderr, flush=True)
        sys.exit(process_result.returncode)
    else:
        print(f"[ArianaLauncher] '{' '.join(command_to_run)}' completed successfully.", flush=True)

except FileNotFoundError:
    print(f"[ArianaLauncher] Error: The 'ariana' command was not found. Please ensure it is installed and in your system's PATH.", file=sys.stderr, flush=True)
    sys.exit(1)
except subprocess.CalledProcessError as e: # Should be caught by check=False and returncode check now
    print(f"[ArianaLauncher] Error: '{' '.join(command_to_run)}' failed with exit code {e.returncode}.", file=sys.stderr, flush=True)
    if e.stdout:
        print(f"[ArianaLauncher] STDOUT:\n{e.stdout}", flush=True)
    if e.stderr:
        print(f"[ArianaLauncher] STDERR:\n{e.stderr}", file=sys.stderr, flush=True)
    sys.exit(e.returncode)
except Exception as e:
    print(f"[ArianaLauncher] An unexpected error occurred: {e}", file=sys.stderr, flush=True)
    sys.exit(1)
