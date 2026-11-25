"""Start the full application: python play.py"""
import sys


def main():
    try:
        import tkinter as tk
        from gui.app import App
        root = tk.Tk()
    except (ImportError, RuntimeError) as exc:
        print("Tkinter is required. Install Python with Tcl/Tk support.\n"
              "Linux (Debian/Ubuntu): sudo apt install python3-tk\n" + str(exc))
        return 1
    except Exception as exc:
        print("Cannot open a desktop window. Run in a graphical session.\n" + str(exc))
        return 1
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
