"""Open the standalone English training dashboard: python train.py"""
import sys


def main():
    try:
        import tkinter as tk
        from gui.style import setup
        from gui.training_window import TrainingWindow
        root = tk.Tk()
    except Exception as exc:
        print("A desktop session and Python with Tkinter are required.\n" + str(exc))
        return 1
    setup(root)
    TrainingWindow(root, standalone=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
