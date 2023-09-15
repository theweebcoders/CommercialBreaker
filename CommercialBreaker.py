import tkinter as tk
from ComBreak.CommercialBreakerGUI import CommercialBreakerGUI
from config import *

if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap(icon_path)
    app = CommercialBreakerGUI(root)
    root.mainloop()