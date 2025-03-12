import logging
from tkinterdnd2 import TkinterDnD
from gui import AppGUI

logging.basicConfig(
    filename='app.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(message)s'
)

def main():
    global root
    try:
        root = TkinterDnD.Tk()
        app = AppGUI(root)
        try:
            root.mainloop()
        except Exception as e:
            logging.error(f"Ошибка в главном цикле событий: {str(e)}", exc_info=True)
            raise
    except ImportError as e:
        logging.error(f"Ошибка импорта модулей: {str(e)}", exc_info=True)
        print("Критическая ошибка: Не удалось загрузить необходимые модули. Проверьте зависимости.")
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {str(e)}", exc_info=True)
        print(f"Произошла ошибка при запуске приложения: {str(e)}")
    finally:
        try:
            if 'root' in locals():
                root.quit()
        except Exception as e:
            logging.error(f"Ошибка при завершении приложения: {str(e)}", exc_info=True)

if __name__ == '__main__':
    main()