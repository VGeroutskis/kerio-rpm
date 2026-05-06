import sys
from app import KerioApp

def main():
    app = KerioApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    main()
