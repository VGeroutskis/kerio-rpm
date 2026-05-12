import sys
import os
import traceback

def main():
    try:
        from app import KerioApp
        app = KerioApp()
        # Passing empty list to avoid "can not open files" error
        return app.run([])
    except Exception as e:
        log_path = os.path.expanduser("~/.kerio-rpm-error.log")
        with open(log_path, "a") as f:
            f.write(f"\n--- Error at {os.popen('date').read()} ---\n")
            traceback.print_exc(file=f)
            f.flush()
        print(f"Failed to start. Check {log_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
