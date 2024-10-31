from tkinterdnd2 import TkinterDnD
from gui import AppGUI

def main():
    root = TkinterDnD.Tk()
    app = AppGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
