import sys
from PySide6.QtWidgets import QApplication
from . import __version__
from .theme import apply as apply_theme
from .ui import Window


def main():
    # A packaged build must be checkable without a display; the CI smoke test
    # runs the executable with --version and expects this exact line.
    if "--version" in sys.argv[1:]:
        print(f"Mailbox Synchroniseur {__version__}")
        return 0
    app = QApplication(sys.argv)
    apply_theme(app)
    app.setApplicationName("Mailbox Synchroniseur")
    app.setOrganizationName("MailboxSynchroniseur")
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
