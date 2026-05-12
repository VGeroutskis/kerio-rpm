import sys
import os
import traceback

def main():
    try:
        from gi.repository import Gio
        from app import KerioApp
        app = KerioApp(flags=Gio.ApplicationFlags.FLAGS_NONE)
        return app.run(sys.argv)
    except Exception as e:
        log_path = os.path.expanduser("~/.kerio-rpm-error.log")
        with open(log_path, "a") as f:
            f.write("\n--- Error Report ---\n")
            traceback.print_exc(file=f)
        print(f"Application failed to start. Error logged to {log_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
