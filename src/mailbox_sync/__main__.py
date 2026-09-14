import sys
from PySide6.QtWidgets import QApplication
from .ui import Window


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Mailbox Synchroniseur")
    app.setOrganizationName("MailboxSynchroniseur")
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
