import tkinter as tk
from ComBreak.CommercialBreakerGUI import CommercialBreakerGUI
import config


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(config.icon_path)
    except Exception as ex:
        print(f'Error showing icon: {ex!r}')
    app = CommercialBreakerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
