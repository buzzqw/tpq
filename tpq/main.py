import sys
import os
import shutil
import subprocess
import signal

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMessageBox, QInputDialog, QMenu, QScrollBar, QSplitter,
    QToolBar, QStyle, QLabel
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QColor

from tpq.settings import Settings
from tpq.terminal import TerminalWidget
from tpq.settings_dialog import SettingsDialog
from tpq.menus import create_menubar


class MainWindow(QMainWindow):
    def __init__(self, standalone: bool = True):
        super().__init__()
        self._standalone = standalone
        self._settings = Settings()
        self._settings.load()

        self.setWindowTitle("TPQ Terminal")
        self.resize(900, 550)

        self._tabs = QTabWidget(self)
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._on_tab_close)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.setMovable(True)
        self._tabs.setUsesScrollButtons(True)
        self._tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self._tabs.setDocumentMode(True)

        self._tabs_menu = None
        self._action_show_tabs = None
        self._action_show_menubar = None
        self._action_show_scrollbar = None
        self._action_read_only = None
        self._encoding_actions = []
        self._read_only = False

        self.setCentralWidget(self._tabs)

        self._toolbar = QToolBar("Main Toolbar")
        self._toolbar.setIconSize(QSize(20, 20))
        self._toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        tb_new_tab = self._toolbar.addAction("New Tab")
        tb_new_tab.triggered.connect(self.new_tab)

        tb_new_win = self._toolbar.addAction("New Window")
        tb_new_win.triggered.connect(self.new_window)

        self._toolbar.addSeparator()

        tb_copy = self._toolbar.addAction("Copy")
        tb_copy.triggered.connect(self.terminal_copy)

        tb_paste = self._toolbar.addAction("Paste")
        tb_paste.triggered.connect(self.terminal_paste)

        self._toolbar.addSeparator()

        self._toolbar_title = QLabel("", self)
        self._toolbar_title.setStyleSheet("color: #aaa; padding: 0 10px;")
        self._toolbar.addWidget(self._toolbar_title)

        self._toolbar.setVisible(self._settings.get("show_toolbar", False))

        self._add_new_tab()
        self._apply_tab_colors()

        self.setMenuBar(create_menubar(self, self._current_terminal()))
        self._storage_menubar = self.menuBar()
        self._apply_window_opacity()

    def _current_terminal(self) -> TerminalWidget:
        w = self._tabs.currentWidget()
        if isinstance(w, TerminalWidget):
            return w
        return None

    def _add_new_tab(self, cwd: str = None):
        term = TerminalWidget(self)
        term.command_executed.connect(self._on_command)
        term.title_changed.connect(self._on_title_changed)
        term.shell_exited.connect(lambda code: self._on_shell_exit(term))

        idx = self._tabs.addTab(term, "Terminal")
        self._tabs.setCurrentIndex(idx)
        term.setFocus()
        self._update_tabs_menu()

    def _on_command(self, cmd: str):
        pass

    def _on_title_changed(self, title: str):
        if title and self._tabs.count() == 1:
            self.setWindowTitle(f"TPQ - {title}")

    def _on_tab_close(self, index: int):
        w = self._tabs.widget(index)
        if isinstance(w, TerminalWidget):
            w.close_terminal()
        self._tabs.removeTab(index)
        self._update_tabs_menu()
        if self._tabs.count() == 0:
            self.close()

    def _on_shell_exit(self, term: TerminalWidget):
        idx = self._tabs.indexOf(term)
        if idx >= 0:
            self._on_tab_close(idx)

    def _on_tab_changed(self, index: int):
        term = self._current_terminal()
        if term:
            term.setFocus()
            self._toolbar_title.setText(f"TPQ — {self._tabs.tabText(index)}")
            if self._action_read_only:
                self._action_read_only.setChecked(self._read_only)
        self._update_tabs_menu()

    def _update_tabs_menu(self):
        if self._tabs_menu is None:
            return
        self._tabs_menu.clear()
        for i in range(self._tabs.count()):
            title = self._tabs.tabText(i)
            action = QAction(f"{i + 1}. {title}", self)
            action.triggered.connect(lambda checked, idx=i: self._tabs.setCurrentIndex(idx))
            if i == self._tabs.currentIndex():
                action.setCheckable(True)
                action.setChecked(True)
            self._tabs_menu.addAction(action)

        if self._tabs.count() == 0:
            no_tabs = QAction("(no tabs)", self)
            no_tabs.setEnabled(False)
            self._tabs_menu.addAction(no_tabs)

    def new_tab(self):
        self._add_new_tab()

    def new_window(self):
        import subprocess
        subprocess.Popen([sys.executable, "-m", "tpq"], start_new_session=True)

    def close_tab(self):
        idx = self._tabs.currentIndex()
        self._on_tab_close(idx)

    def terminal_copy(self):
        term = self._current_terminal()
        if term:
            term.copy()

    def terminal_paste(self):
        term = self._current_terminal()
        if term:
            term.paste()

    def terminal_paste_selection(self):
        term = self._current_terminal()
        if term:
            term.paste_selection()

    def terminal_select_all(self):
        term = self._current_terminal()
        if term:
            term._sel_start = (0, 0)
            end_abs = len(term._scrollback) + term._screen.lines - 1
            term._sel_end = (term._screen.columns - 1, end_abs)
            term.update()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()
        self._apply_window_opacity()

    def _apply_window_opacity(self):
        if self._settings.get("enable_transparency", False):
            self.setWindowOpacity(self._settings.get("opacity", 1.0))

    def zoom_in(self):
        s = self._settings
        current = s.get("font_size", 12)
        new_size = min(48, current + 1)
        s.set("font_size", new_size)

    def zoom_out(self):
        s = self._settings
        current = s.get("font_size", 12)
        new_size = max(6, current - 1)
        s.set("font_size", new_size)

    def zoom_reset(self):
        self._settings.set("font_size", 12)

    def toggle_fullscreen(self, checked: bool):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def reset_terminal(self):
        term = self._current_terminal()
        if term:
            term._send_to_child(b'\x1bc')
            term._send_to_child(b'\n')

    def reset_and_clear(self):
        term = self._current_terminal()
        if term:
            term._send_to_child(b'\x1bc')

    def prev_tab(self):
        count = self._tabs.count()
        if count > 1:
            idx = self._tabs.currentIndex()
            self._tabs.setCurrentIndex((idx - 1) % count)

    def next_tab(self):
        count = self._tabs.count()
        if count > 1:
            idx = self._tabs.currentIndex()
            self._tabs.setCurrentIndex((idx + 1) % count)

    def move_tab_left(self):
        idx = self._tabs.currentIndex()
        if idx > 0:
            self._tabs.tabBar().moveTab(idx, idx - 1)
            self._tabs.setCurrentIndex(idx - 1)

    def move_tab_right(self):
        idx = self._tabs.currentIndex()
        if idx < self._tabs.count() - 1:
            self._tabs.tabBar().moveTab(idx, idx + 1)
            self._tabs.setCurrentIndex(idx + 1)

    def detach_tab(self):
        if self._tabs.count() <= 1:
            return
        idx = self._tabs.currentIndex()
        w = self._tabs.widget(idx)
        if not isinstance(w, TerminalWidget):
            return

        self._tabs.removeTab(idx)
        self._update_tabs_menu()

        new_win = DetachedWindow(w)
        new_win.setWindowTitle(self._tabs.tabText(idx))
        new_win.resize(self.width(), self.height())
        new_win.show()

    def toggle_read_only(self, checked: bool):
        self._read_only = checked
        term = self._current_terminal()
        if term:
            if checked:
                term._send_to_child(b'\x1b[2J\x1b[H')
                term._stream.feed(
                    "\x1b[1;33m=== READ-ONLY MODE ===\x1b[0m\r\n"
                    "\x1b[37mTerminal is read-only. Input is disabled.\x1b[0m\r\n"
                )
                term.update()
            else:
                term._send_to_child(b'\n')

    def toggle_tabs_visibility(self, visible: bool):
        self._tabs.tabBar().setVisible(visible)

    def toggle_menubar_visibility(self, visible: bool):
        if visible:
            self.setMenuBar(self._storage_menubar)
        else:
            self._storage_menubar = self.menuBar()
            self.setMenuBar(None)

    def toggle_scrollbar_visibility(self, visible: bool):
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, TerminalWidget):
                w.set_scrollbar_visible(visible)

    def toggle_toolbar_visibility(self, visible: bool):
        self._toolbar.setVisible(visible)
        self._settings.set("show_toolbar", visible)

    def set_title_dialog(self):
        current = self.windowTitle()
        title, ok = QInputDialog.getText(self, "Set Title", "Terminal title:", text=current)
        if ok and title:
            self.setWindowTitle(title)
            idx = self._tabs.currentIndex()
            if idx >= 0:
                self._tabs.setTabText(idx, title)

    def show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self, "About TPQ",
            "<h2>TPQ Terminal v1.0.0</h2>"
            "<p><b>Terminale Python Qt</b></p>"
            "<p>Advanced terminal emulator with built-in AI chat, "
            "command history search, and notes system.</p>"
            "<p>Built with Python, PyQt6, and pyte.</p>"
            "<hr>"
            "<p><b>Author:</b> Andres Zanzani</p>"
            "<p><b>License:</b> EUPL 1.2 (European Union Public License)</p>"
            "<p><a href='https://github.com/buzzqw/tpq'>github.com/buzzqw/tpq</a></p>"
        )

    def closeEvent(self, event):
        if self._settings.get("confirm_close", True) and self._tabs.count() > 1:
            reply = QMessageBox.question(
                self, "Confirm Close",
                f"Close all {self._tabs.count()} tabs?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, TerminalWidget):
                w.close_terminal()

        event.accept()

    def _detect_file_manager(self) -> str:
        fm = self._settings.get("file_manager", "")
        if fm and shutil.which(fm):
            return fm
        for candidate in ["nemo", "thunar", "dolphin", "nautilus", "pcmanfm",
                          "caja", "nemo-desktop", "spacefm"]:
            if shutil.which(candidate):
                return candidate
        return ""

    def open_file_manager(self):
        fm = self._detect_file_manager()
        if not fm:
            QMessageBox.warning(self, "File Manager",
                                "No file manager found.\nInstall nemo, thunar, dolphin, or nautilus.")
            return
        term = self._current_terminal()
        cwd = term.get_cwd() if term else os.path.expanduser("~")
        subprocess.Popen([fm, cwd], start_new_session=True)

    def set_encoding(self, encoding: str):
        term = self._current_terminal()
        if term:
            term.set_encoding(encoding)
            idx = self._tabs.currentIndex()
            if idx >= 0:
                current = self._tabs.tabText(idx).split(" [")[0]
                self._tabs.setTabText(idx, f"{current} [{encoding}]")
            self._settings.set("encoding", encoding)

    def send_signal(self, sig: int):
        term = self._current_terminal()
        if term:
            term.kill_process(sig)
            sig_names = {
                signal.SIGTERM: "SIGTERM",
                signal.SIGKILL: "SIGKILL",
                signal.SIGHUP: "SIGHUP",
                signal.SIGINT: "SIGINT",
                signal.SIGQUIT: "SIGQUIT",
            }
            name = sig_names.get(sig, f"signal {sig}")
            term._stream.feed(f"\r\n\x1b[33mSent {name} to process {term._child_pid}\x1b[0m\r\n")
            term._send_to_child(b'\n')
            term.update()

    def _apply_tab_colors(self):
        color = self._settings.get("tab_title_color", "#ffffff")
        active_color = self._settings.get("tab_active_title_color", "#ffffff")
        self._tabs.setStyleSheet(
            f"QTabBar::tab {{ color: {color}; }}"
            f"QTabBar::tab:selected {{ color: {active_color}; font-weight: bold; }}"
        )


class DetachedWindow(QMainWindow):
    def __init__(self, terminal: TerminalWidget):
        super().__init__()
        self._settings = Settings()
        self._terminal = terminal
        self._terminal.setParent(self)
        self._tabs_menu = None
        self._action_show_tabs = None
        self._action_show_menubar = None
        self._action_show_scrollbar = None
        self._action_read_only = None
        self._encoding_actions = []
        self.setCentralWidget(self._terminal)
        self.setMenuBar(create_menubar(self, self._terminal))

    def _current_terminal(self):
        return self._terminal

    def new_tab(self):
        pass

    def new_window(self):
        pass

    def close_tab(self):
        self.close()

    def terminal_copy(self):
        self._terminal.copy()

    def terminal_paste(self):
        self._terminal.paste()

    def terminal_paste_selection(self):
        self._terminal.paste_selection()

    def terminal_select_all(self):
        self._terminal._sel_start = (0, 0)
        end_abs = len(self._terminal._scrollback) + self._terminal._screen.lines - 1
        self._terminal._sel_end = (self._terminal._screen.columns - 1, end_abs)
        self._terminal.update()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def zoom_in(self):
        s = self._settings
        s.set("font_size", min(48, s.get("font_size", 12) + 1))

    def zoom_out(self):
        s = self._settings
        s.set("font_size", max(6, s.get("font_size", 12) - 1))

    def zoom_reset(self):
        self._settings.set("font_size", 12)

    def toggle_fullscreen(self, checked: bool):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def reset_terminal(self):
        self._terminal._send_to_child(b'\x1bc')
        self._terminal._send_to_child(b'\n')

    def reset_and_clear(self):
        self._terminal._send_to_child(b'\x1bc')

    def prev_tab(self):
        pass

    def next_tab(self):
        pass

    def move_tab_left(self):
        pass

    def move_tab_right(self):
        pass

    def detach_tab(self):
        pass

    def toggle_read_only(self, checked: bool):
        pass

    def toggle_tabs_visibility(self, visible: bool):
        pass

    def toggle_menubar_visibility(self, visible: bool):
        pass

    def toggle_scrollbar_visibility(self, visible: bool):
        pass

    def set_title_dialog(self):
        title, ok = QInputDialog.getText(self, "Set Title", "Terminal title:", text=self.windowTitle())
        if ok and title:
            self.setWindowTitle(title)

    def show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(self, "About TPQ",
            "<h2>TPQ Terminal v1.0.0</h2>"
            "<p><b>Author:</b> Andres Zanzani</p>"
            "<p><b>License:</b> EUPL 1.2</p>"
            "<p>github.com/buzzqw/tpq</p>"
        )

    def open_file_manager(self):
        pass

    def set_encoding(self, encoding: str):
        pass

    def send_signal(self, sig: int):
        pass

    def _update_tabs_menu(self):
        pass

    def closeEvent(self, event):
        self._terminal.close_terminal()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("tpq")
    app.setOrganizationName("tpq")
    app.setApplicationVersion("1.0.0")

    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
