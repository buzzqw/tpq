import os
import pty
import signal
import struct
import fcntl
import termios
from collections import deque

from PyQt6.QtWidgets import QWidget, QScrollBar
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QPoint, QEvent
from PyQt6.QtGui import (
    QPainter, QFont, QColor, QFontMetrics, QFontDatabase,
    QKeyEvent, QMouseEvent, QWheelEvent, QPixmap
)

import pyte

from tpq.settings import Settings
from tpq.history import HistoryManager


TO_SPECIAL = {
    Qt.Key.Key_Up: b'\x1b[A',
    Qt.Key.Key_Down: b'\x1b[B',
    Qt.Key.Key_Right: b'\x1b[C',
    Qt.Key.Key_Left: b'\x1b[D',
    Qt.Key.Key_Home: b'\x1b[H',
    Qt.Key.Key_End: b'\x1b[F',
    Qt.Key.Key_Insert: b'\x1b[2~',
    Qt.Key.Key_Delete: b'\x1b[3~',
    Qt.Key.Key_PageUp: b'\x1b[5~',
    Qt.Key.Key_PageDown: b'\x1b[6~',
    Qt.Key.Key_F1: b'\x1bOP',
    Qt.Key.Key_F2: b'\x1bOQ',
    Qt.Key.Key_F3: b'\x1bOR',
    Qt.Key.Key_F4: b'\x1bOS',
    Qt.Key.Key_F5: b'\x1b[15~',
    Qt.Key.Key_F6: b'\x1b[17~',
    Qt.Key.Key_F7: b'\x1b[18~',
    Qt.Key.Key_F8: b'\x1b[19~',
    Qt.Key.Key_F9: b'\x1b[20~',
    Qt.Key.Key_F10: b'\x1b[21~',
    Qt.Key.Key_F11: b'\x1b[23~',
    Qt.Key.Key_F12: b'\x1b[24~',
}


CLIPBOARD = None


def _get_clipboard():
    global CLIPBOARD
    if CLIPBOARD is None:
        from PyQt6.QtWidgets import QApplication
        CLIPBOARD = QApplication.clipboard()
    return CLIPBOARD


class TerminalWidget(QWidget):
    title_changed = pyqtSignal(str)
    command_executed = pyqtSignal(str)
    shell_exited = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._settings.load()
        self._history = HistoryManager()
        self._init_font()
        self._init_colors()
        self._init_screen()
        self._init_state()
        self._init_pty()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(200, 100)

    def _init_font(self):
        family = self._settings.get("font_family", "Monospace")
        size = self._settings.get("font_size", 12)
        self._font = QFont(family, size)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._bold_font = QFont(self._font)
        self._bold_font.setBold(True)
        self._fm = QFontMetrics(self._font)
        self._cell_w = self._fm.horizontalAdvance('W')
        self._cell_h = self._fm.lineSpacing()

    def _init_colors(self):
        palette = self._settings.get_palette()
        self._palette = {}
        for name, hex_color in palette.items():
            self._palette[name] = QColor(hex_color)
        self._default_fg = QColor(self._settings.get_fg_color())
        self._default_bg = QColor(self._settings.get_bg_color())

    def _init_screen(self):
        cols = max(1, self.width() // self._cell_w) if self.width() > 0 else 80
        rows = max(1, self.height() // self._cell_h) if self.height() > 0 else 24
        self._screen = pyte.Screen(cols, rows)
        self._stream = pyte.Stream(self._screen)
        self._stream.attach(self._screen)

    def _init_state(self):
        self._master_fd = None
        self._child_pid = None
        self._encoding = self._settings.get("encoding", "UTF-8")
        self._read_timer = QTimer(self)
        self._read_timer.timeout.connect(self._read_from_child)
        self._read_timer.start(10)
        self._cursor_visible = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)
        if self._settings.get("cursor_blink", True):
            self._cursor_timer.start(530)
        self._input_shadow = ""
        self._scrollback = []
        self._scroll_offset = 0
        self._ai_mode = False
        self._ai_client = None
        self._ai_input = ""
        self._read_buffer = bytearray()
        self._pre_feed_snapshot = None
        self._selecting = False
        self._sel_start = None
        self._sel_end = None
        self._history_search_mode = False
        self._history_search_query = ""
        self._history_search_index = 0
        self._history_search_results = []
        self._history_show_results = []
        self._model_list = []
        self._provider_list = []
        self._connect_provider = None
        self._connect_key = ""
        self._connect_url = ""
        self._connect_model = ""
        self._tpq_input_mode = False
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.timeout.connect(self._auto_scroll)
        self._auto_scroll_delta = 0
        self._last_mouse_pos = None
        self._mouse_tracking = False
        self._scrollbar_visible = True

        self._scrollbar = QScrollBar(Qt.Orientation.Vertical, self)
        self._scrollbar.setRange(0, 0)
        self._scrollbar.setVisible(False)
        self._scrollbar.valueChanged.connect(self._on_scrollbar_changed)
        self._scrollbar.sliderMoved.connect(self._on_scrollbar_slider)
        self._scrollbar_w = 12

    def _init_pty(self):
        try:
            pid, master_fd = pty.fork()
        except OSError as e:
            self._stream.feed(f"\r\n\x1b[31mFailed to start shell: {e}\x1b[0m\r\n")
            return

        if pid == 0:
            self._child_setup()
        else:
            self._child_pid = pid
            self._master_fd = master_fd
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self._update_size()

    def _child_setup(self):
        shell = self._settings.get("shell_command", os.environ.get("SHELL", "/bin/bash"))
        os.environ["TERM"] = "xterm-256color"
        os.environ["COLORTERM"] = "truecolor"
        os.environ["LANG"] = os.environ.get("LANG", "en_US.UTF-8")
        try:
            os.execvpe(shell, [shell], os.environ)
        except OSError:
            os.execvpe("/bin/sh", ["/bin/sh"], os.environ)

    def _snapshot_buffer(self):
        snap = {}
        for row in range(self._screen.lines):
            if row in self._screen.buffer:
                snap[row] = dict(self._screen.buffer[row])
        return snap

    def _detect_scroll(self, old_buf: dict, new_buf: dict):
        if not old_buf or not new_buf:
            return
        max_lines = self._screen.lines

        old_count = sum(1 for r in old_buf if r < max_lines)
        new_count = sum(1 for r in new_buf if r < max_lines)
        if old_count == 0 or new_count == 0:
            return

        for shift in range(1, max_lines + 1):
            match = True
            pairs = 0
            for r in range(shift, max_lines):
                if r not in old_buf and (r - shift) not in new_buf:
                    continue
                pairs += 1
                old_row = old_buf.get(r, {})
                new_row = new_buf.get(r - shift, {})
                if old_row != new_row:
                    match = False
                    break
            if pairs > 0 and match:
                for s in range(shift):
                    if s in old_buf and old_buf[s]:
                        line = [old_buf[s].get(c, self._screen.default_char)
                                for c in range(self._screen.columns)]
                        self._scrollback.append(line)
                return

    def _read_from_child(self):
        if self._master_fd is None:
            return
        try:
            data = os.read(self._master_fd, 65536)
        except (OSError, BlockingIOError):
            return

        if not data:
            self._on_child_exit()
            return

        self._read_buffer.extend(data)
        try:
            text = self._read_buffer.decode(self._encoding)
            self._read_buffer.clear()
        except (UnicodeDecodeError, UnicodeEncodeError):
            for cut in range(1, 5):
                try:
                    text = self._read_buffer[:-cut].decode(self._encoding)
                    self._read_buffer = self._read_buffer[-cut:]
                    break
                except (UnicodeDecodeError, UnicodeEncodeError):
                    continue
            else:
                text = self._read_buffer.decode(self._encoding, errors='replace')
                self._read_buffer.clear()

        if not text:
            return

        if self._ai_mode:
            return

        old_buf = self._snapshot_buffer()
        self._stream.feed(text)
        new_buf = self._snapshot_buffer()
        self._detect_scroll(old_buf, new_buf)
        self._scroll_offset = 0

        max_scroll = self._settings.get("scrollback_lines", 5000)
        if max_scroll > 0 and len(self._scrollback) > max_scroll:
            excess = len(self._scrollback) - max_scroll
            self._scrollback = self._scrollback[excess:]

        self._update_scrollbar()

        if self._screen.title:
            self.title_changed.emit(self._screen.title)

        self.update()

    def _on_child_exit(self):
        if self._child_pid is not None:
            try:
                _, exit_status = os.waitpid(self._child_pid, os.WNOHANG)
            except ChildProcessError:
                exit_status = 0
            status = exit_status if isinstance(exit_status, int) else 0
            self._stream.feed(f"\r\n\x1b[33m[Process exited with code {status}]\x1b[0m\r\n")
            self._child_pid = None
            self._master_fd = None
            self.shell_exited.emit(status)
            self.update()

    def _send_to_child(self, data: bytes):
        if self._master_fd is None:
            return
        try:
            while data:
                n = os.write(self._master_fd, data)
                data = data[n:]
        except OSError:
            pass

    def _update_size(self):
        if self._master_fd is None:
            return
        w = self.width()
        h = self.height()
        cols = max(1, w // self._cell_w)
        rows = max(1, h // self._cell_h)
        if cols != self._screen.columns or rows != self._screen.lines:
            self._screen.resize(rows, cols)
            try:
                winsize = struct.pack("HHHH", rows, cols, w, h)
                fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
                os.kill(self._child_pid, signal.SIGWINCH)
            except (OSError, ProcessLookupError):
                pass

    def _toggle_cursor(self):
        self._cursor_visible = not self._cursor_visible
        self.update()

    def _get_cell_rect(self, col: int, row_on_screen: int) -> QRect:
        return QRect(
            col * self._cell_w,
            row_on_screen * self._cell_h,
            self._cell_w,
            self._cell_h,
        )

    def _pos_to_cell(self, pos: QPoint):
        col = max(0, pos.x() // self._cell_w)
        total_lines = self._total_lines()
        visible_rows = max(1, self.height() // self._cell_h)
        start_abs = total_lines - visible_rows - self._scroll_offset
        abs_row = pos.y() // self._cell_h + start_abs
        return col, abs_row

    def _abs_row_to_screen(self, abs_row: int) -> int:
        total_lines = self._total_lines()
        visible_rows = max(1, self.height() // self._cell_h)
        start_abs = total_lines - visible_rows - self._scroll_offset
        return abs_row - start_abs

    def _total_lines(self) -> int:
        return len(self._scrollback) + self._screen.lines

    def _resolve_color(self, color_str, default: QColor) -> QColor:
        if not color_str or color_str == "default":
            return default
        if color_str.startswith("#") and len(color_str) >= 7:
            return QColor(color_str[:7])
        return self._palette.get(color_str, default)

    def _get_line(self, abs_row: int):
        if abs_row < len(self._scrollback):
            return self._scrollback[abs_row]
        srow = abs_row - len(self._scrollback)
        if 0 <= srow < self._screen.lines:
            return [
                self._screen.buffer[srow].get(c, self._screen.default_char)
                for c in range(self._screen.columns)
            ]
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self._font)
        bg = self._default_bg

        if self._settings.get("enable_transparency", False):
            opacity = self._settings.get("opacity", 1.0)
            bg = QColor(bg.red(), bg.green(), bg.blue(), int(opacity * 255))

        painter.fillRect(event.rect(), bg)

        clip_rect = event.rect()
        visible_rows = max(1, self.height() // self._cell_h)
        total_lines = self._total_lines()
        max_offset = max(0, total_lines - visible_rows)
        if self._scroll_offset > max_offset:
            self._scroll_offset = max_offset
        start_abs = total_lines - visible_rows - self._scroll_offset

        start_y = max(0, clip_rect.top() // self._cell_h)
        end_y = min(visible_rows, clip_rect.bottom() // self._cell_h + 1)

        for screen_row in range(start_y, end_y):
            abs_row = start_abs + screen_row
            line_data = self._get_line(abs_row)

            if line_data is None:
                continue

            y = screen_row * self._cell_h
            for col in range(min(len(line_data), self._screen.columns)):
                ch = line_data[col]
                x = col * self._cell_w

                fg = self._resolve_color(ch.fg, self._default_fg)
                cell_bg = self._resolve_color(ch.bg, self._default_bg)

                if ch.reverse:
                    fg, cell_bg = cell_bg, fg

                cell_rect = QRect(x, y, self._cell_w, self._cell_h)
                painter.fillRect(cell_rect, cell_bg)

                data = ch.data
                if data and data != ' ':
                    font = self._bold_font if ch.bold else self._font
                    if ch.italics:
                        font = QFont(font)
                        font.setItalic(True)

                    painter.setFont(font)
                    painter.setPen(fg)
                    painter.drawText(
                        cell_rect,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        data,
                    )

                    if ch.underscore:
                        painter.drawLine(
                            x, y + self._cell_h - 2,
                            x + self._cell_w, y + self._cell_h - 2,
                        )

                if ch.strikethrough:
                    my = y + self._cell_h // 2
                    painter.drawLine(x, my, x + self._cell_w, my)

        if self._selecting and self._sel_start and self._sel_end:
            self._draw_selection(painter)

        if not self._history_search_mode:
            self._draw_cursor(painter)

        if self._history_search_mode:
            self._draw_search_bar(painter)

        painter.end()

    def _draw_selection(self, painter):
        start_col, start_abs = self._sel_start
        end_col, end_abs = self._sel_end

        if (end_abs, end_col) < (start_abs, start_col):
            start_col, end_col = end_col, start_col
            start_abs, end_abs = end_abs, start_abs

        painter.setPen(Qt.PenStyle.NoPen)
        hlbg = QColor(self._settings.get("highlight_bg_color", "#446688"))
        hlbg.setAlpha(120)
        painter.setBrush(hlbg)

        for abs_row in range(start_abs, end_abs + 1):
            srow = self._abs_row_to_screen(abs_row)
            if srow < 0 or srow >= (self.height() // self._cell_h):
                continue
            y = srow * self._cell_h

            if abs_row == start_abs and abs_row == end_abs:
                x1 = start_col * self._cell_w
                w = max(1, (end_col - start_col)) * self._cell_w
            elif abs_row == start_abs:
                x1 = start_col * self._cell_w
                w = max(1, (self._screen.columns - start_col)) * self._cell_w
            elif abs_row == end_abs:
                x1 = 0
                w = max(1, end_col) * self._cell_w
            else:
                x1 = 0
                w = self._screen.columns * self._cell_w

            painter.drawRect(QRect(x1, y, w, self._cell_h))

    def _draw_cursor(self, painter):
        if self._screen.cursor.hidden:
            return
        if not self._cursor_visible and self._settings.get("cursor_blink", True):
            return

        cy = self._screen.cursor.y
        cx = self._screen.cursor.x

        abs_cursor = cy + len(self._scrollback)
        screen_row = self._abs_row_to_screen(abs_cursor)
        if screen_row < 0 or screen_row >= (self.height() // self._cell_h):
            return

        cursor_rect = self._get_cell_rect(cx, screen_row)
        cursor_shape = self._settings.get("cursor_shape", "block")
        cursor_color = QColor(self._settings.get("cursor_color", "#ffffff"))

        if cursor_shape == "underline":
            painter.fillRect(
                QRect(cursor_rect.x(), cursor_rect.bottom() - 3, cursor_rect.width(), 3),
                cursor_color,
            )
        elif cursor_shape == "beam":
            painter.fillRect(
                QRect(cursor_rect.x(), cursor_rect.y(), 2, cursor_rect.height()),
                cursor_color,
            )
        else:
            painter.fillRect(cursor_rect, cursor_color)

    def _draw_search_bar(self, painter):
        h = self.height()
        bar_h = self._cell_h + 4
        y = h - bar_h
        painter.fillRect(0, y, self.width(), bar_h, QColor(0, 0, 180, 220))
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(self._font)
        count = len(self._history_search_results)
        idx_str = f"{self._history_search_index + 1}/{count}" if count > 0 else "0/0"
        text = f"(reverse-i-search)`{self._history_search_query}`: {idx_str}"
        painter.drawText(6, y + self._cell_h, text)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        if self._history_search_mode:
            self._handle_history_search_key(event)
            return

        if key == Qt.Key.Key_R and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._start_history_search()
            return

        if key == Qt.Key.Key_L and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._send_to_child(b'\x0c')
            return

        if key == Qt.Key.Key_C and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self._send_to_child(b'\x03')
            self._input_shadow = ""
            self._tpq_input_mode = False
            self._provider_list = []
            self._model_list = []
            return

        if (modifiers & Qt.KeyboardModifier.AltModifier):
            num = key - Qt.Key.Key_0
            if 1 <= num <= 9:
                self._replay_history_number(num)
                return

        if self._ai_mode:
            self._handle_ai_key(event)
            return

        if self._history_search_mode:
            self._handle_history_search_key(event)
            return

        shift_ctrl = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        if key == Qt.Key.Key_C and (modifiers & shift_ctrl) == shift_ctrl:
            self.copy()
            return
        if key == Qt.Key.Key_V and (modifiers & shift_ctrl) == shift_ctrl:
            self.paste()
            return

        if self._tpq_input_mode:
            self._handle_tpq_input_key(event)
            return

        text = event.text()
        if text == '/' and self._input_shadow == "":
            self._tpq_input_mode = True
            self._input_shadow = '/'
            self._stream.feed('/')
            self.update()
            return

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            shadow = self._input_shadow.strip()
            self._send_to_child(b'\r')
            if shadow:
                self._history.add(shadow, os.getcwd())
                self.command_executed.emit(shadow)
            self._input_shadow = ""
            return

        if key == Qt.Key.Key_Backspace:
            bs = self._settings.get("backspace_binding", "ascii-del")
            if bs == "control-h":
                self._send_to_child(b'\x08')
            elif bs == "escape-sequence":
                self._send_to_child(b'\x1b\x7f')
            else:
                self._send_to_child(b'\x7f')
            if self._input_shadow:
                self._input_shadow = self._input_shadow[:-1]
            return

        if key == Qt.Key.Key_U and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._send_to_child(b'\x15')
            self._input_shadow = ""
            return

        if key == Qt.Key.Key_W and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._send_to_child(b'\x17')
            parts = self._input_shadow.rsplit(' ', 1)
            self._input_shadow = parts[0] if len(parts) > 1 else ""
            return

        if key == Qt.Key.Key_D and (modifiers & Qt.KeyboardModifier.ControlModifier):
            if self._tpq_input_mode or self._provider_list or self._model_list:
                self._tpq_input_mode = False
                self._provider_list = []
                self._model_list = []
                self._input_shadow = ""
            if not self._input_shadow:
                self._send_to_child(b'\x04')
                QTimer.singleShot(800, self._check_child_exit_after_eof)
            return

        seq = TO_SPECIAL.get(key)
        if seq is not None:
            self._send_to_child(seq)
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
                self._input_shadow = ""
            return

        text = event.text()
        if text and len(text) == 1:
            if key == Qt.Key.Key_Tab:
                self._send_to_child(b'\t')
                return
            if ord(text[0]) >= 0x20:
                self._send_to_child(text.encode('utf-8'))
                self._input_shadow += text
                return

    def _check_child_exit_after_eof(self):
        if self._child_pid:
            try:
                pid, status = os.waitpid(self._child_pid, os.WNOHANG)
                if pid == self._child_pid:
                    self._on_child_exit()
            except ChildProcessError:
                self._on_child_exit()

    def _handle_tpq_input_key(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        if self._provider_list or self._model_list or self._history_show_results:
            text = event.text()
            if key == Qt.Key.Key_Escape:
                self._provider_list = []
                self._model_list = []
                self._history_show_results = []
                self._stream.feed("\r\n\x1b[37mSelection cancelled.\x1b[0m\r\n")
                self._tpq_input_mode = False
                self._send_to_child(b'\n')
                self._input_shadow = ""
                self.update()
                return
            if text and text.isdigit():
                num = int(text)
                if 1 <= num <= 9:
                    if self._provider_list:
                        self._select_provider_number(num)
                    elif self._model_list:
                        self._select_model_number(num)
                    elif self._history_show_results:
                        self._replay_history_number(num)
                    self._tpq_input_mode = False
                    self._stream.feed("\r\n")
                    self._send_to_child(b'\n')
                    self.update()
                    return
            self._provider_list = []
            self._model_list = []
            self._history_show_results = []
            self._tpq_input_mode = False
            self._stream.feed("\r\n")
            self._send_to_child(b'\n')
            self._input_shadow = ""
            self.update()
            return

        if not self._input_shadow.startswith('/'):
            self._tpq_input_mode = False
            self._provider_list = []
            self._model_list = []
            self._input_shadow = ""
            self.keyPressEvent(event)
            return

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            cmd = self._input_shadow.strip()
            self._stream.feed("\r\n")
            self._handle_tpq_command(cmd)
            self._input_shadow = ""
            if self._provider_list or self._model_list or self._history_show_results:
                self.update()
                return
            self._tpq_input_mode = False
            if not self._ai_mode:
                self._stream.feed("\r\n")
                self._send_to_child(b'\n')
            self.update()
            return

        if key == Qt.Key.Key_Escape or (
            key == Qt.Key.Key_C and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            self._tpq_input_mode = False
            col = self._screen.cursor.x
            row = self._screen.cursor.y
            for _ in range(len(self._input_shadow)):
                self._stream.feed('\b \b')
            self._input_shadow = ""
            self._send_to_child(b'\n')
            self.update()
            return

        if key == Qt.Key.Key_Backspace:
            if self._input_shadow:
                self._input_shadow = self._input_shadow[:-1]
                self._stream.feed('\b \b')
            self.update()
            return

        if key == Qt.Key.Key_U and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            for _ in range(len(self._input_shadow)):
                self._stream.feed('\b \b')
            self._input_shadow = ""
            self.update()
            return

        if key == Qt.Key.Key_Tab:
            self._autocomplete_tpq()
            return

        if key == Qt.Key.Key_W and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            parts = self._input_shadow.rsplit(' ', 1)
            removed = self._input_shadow[len(parts[0]):] if len(parts) > 1 else self._input_shadow
            self._input_shadow = parts[0] if len(parts) > 1 else ""
            for _ in range(len(removed)):
                self._stream.feed('\b \b')
            self.update()
            return

        if text and len(text) == 1 and ord(text[0]) >= 0x20:
            self._input_shadow += text
            self._stream.feed(text)
            self.update()
            return

    def event(self, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab or event.key() == Qt.Key.Key_Backtab:
                self.keyPressEvent(event)
                return True
        return super().event(event)

    def _handle_tpq_command(self, cmd: str):
        parts = cmd.split(None, 1)
        command = parts[0][1:] if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if command == "history":
            self._cmd_history(args)
        elif command == "ai":
            self._cmd_ai(args)
        elif command == "connect":
            self._cmd_connect(args)
        elif command == "wnotes":
            self._cmd_wnotes(args)
        elif command == "onotes":
            self._cmd_onotes(args)
        elif command == "clear" or command == "cls":
            self._stream.feed("\x1b[2J\x1b[H")
        elif command == "help":
            self._cmd_help()
        else:
            self._stream.feed(f"\x1b[33mUnknown command: /{command}\x1b[0m\r\n")
            self._stream.feed("Type /help for available commands.\r\n")

    def _cmd_history(self, args: str):
        if not args.strip():
            results = self._history.search("", 30)
        else:
            results = self._history.search(args, 30)

        if not results:
            self._stream.feed("\x1b[37mNo matching history entries.\x1b[0m\r\n")
            return

        self._stream.feed("\x1b[1;37m--- History ---\x1b[0m\r\n")
        self._stream.feed("\x1b[37mPress 1..9 to re-execute, Esc to cancel.\x1b[0m\r\n")
        self._history_show_results = []
        for i, row in enumerate(results[:9]):
            rid, command, cwd, ts = row
            display = command[:140] + ("..." if len(command) > 140 else "")
            num = i + 1
            self._stream.feed(f"  \x1b[1;33m[{num}]\x1b[0m \x1b[36m{rid}\x1b[0m  {display}\r\n")
            self._history_show_results.append((num, command))
        self._stream.feed(f"\x1b[37m{len(results)} result(s)\x1b[0m\r\n")

    def _cmd_ai(self, args: str):
        if args.strip().lower() == "off":
            self._exit_ai_mode()
        else:
            self._enter_ai_mode()

    def _cmd_connect(self, args: str):
        provider = args.strip().lower()
        valid = ["openai", "claude", "gemini", "deepseek", "ollama", "custom"]

        if not provider:
            self._show_provider_list()
            return

        if provider not in valid:
            self._stream.feed(f"\x1b[31mInvalid provider: {provider}\x1b[0m\r\n")
            self._stream.feed(f"\x1b[37mUse: /connect [{'|'.join(valid)}]\x1b[0m\r\n")
            return

        self._connect_to_provider(provider)

    def _show_provider_list(self):
        from tpq.ai_client import AIClient
        available = []
        keys = self._settings.get("ai_keys", {})
        models = self._settings.get("ai_models", {})
        urls = self._settings.get("ai_urls", {})

        for provider in ["openai", "claude", "gemini", "deepseek", "ollama", "custom"]:
            info = AIClient.PROVIDERS[provider]
            if provider in ("ollama", "custom"):
                url = urls.get(provider, "") or info["url"]
                if self._ping_provider(provider, url):
                    fetched = self._fetch_models(provider, "", url)
                    model = models.get(provider, "") or (fetched[0] if fetched else info["default_model"])
                    label = f"{info['name']} ({model})"
                    if fetched:
                        label += f" [{len(fetched)} models]"
                    available.append((provider, label, info, fetched))
            else:
                key = keys.get(provider, "")
                if key:
                    model = models.get(provider, "") or info["default_model"]
                    label = f"{info['name']} ({model})"
                    available.append((provider, label, info, []))

        if not available:
            self._stream.feed("\x1b[33mNo providers configured.\x1b[0m\r\n")
            self._stream.feed("\x1b[37mSet API keys in Preferences > AI or in ~/.config/tpq/settings.json\x1b[0m\r\n")
            self._stream.feed("\x1b[37mFor Ollama: install ollama and run 'ollama serve'\x1b[0m\r\n")
            return

        self._stream.feed("\x1b[1;37mAvailable providers:\x1b[0m\r\n")
        self._provider_list = []
        for i, (prov, label, info, fetched) in enumerate(available[:9]):
            num = i + 1
            icon = "\x1b[32m●\x1b[0m" if prov != "custom" or fetched else "\x1b[33m●\x1b[0m"
            self._stream.feed(f"  \x1b[1;33m[{num}]\x1b[0m {icon} {label}\r\n")
            self._provider_list.append((num, prov, fetched))
        self._stream.feed("\x1b[37mPress 1..9 to select a provider, Esc to cancel.\x1b[0m\r\n")

    def _ping_provider(self, provider: str, url: str) -> bool:
        try:
            import requests
            if provider == "ollama":
                u = url.replace("/v1/chat/completions", "").rstrip("/") if url else "http://localhost:11434"
                r = requests.get(f"{u}/api/tags", timeout=3)
                return r.status_code == 200
            elif provider == "custom" and url:
                base = url.rsplit("/chat/completions", 1)[0].rstrip("/")
                if not base:
                    base = url.rstrip("/")
                for test_url in [url, f"{base}/models", base]:
                    try:
                        r = requests.get(test_url, timeout=3)
                        if r.status_code == 200:
                            return True
                    except Exception:
                        continue
                return False
        except Exception:
            pass
        return False

    def _select_provider_number(self, num: int):
        for n, prov, fetched in self._provider_list:
            if n == num:
                self._provider_list = []
                self._connect_to_provider(prov)
                return
        self._provider_list = []

    def _connect_to_provider(self, provider: str):
        from tpq.ai_client import AIClient
        key = self._settings.get("ai_keys", {}).get(provider, "")
        model = self._settings.get("ai_models", {}).get(provider, "")
        base_url = self._settings.get("ai_urls", {}).get(provider, "")
        info = AIClient.PROVIDERS[provider]

        if provider not in ("ollama", "custom") and not key:
            self._stream.feed(f"\x1b[33mNo API key set for {provider}.\x1b[0m\r\n")
            return

        models = self._fetch_models(provider, key, base_url)

        if models and len(models) > 1:
            self._stream.feed(f"\x1b[1;37m{info['name']} — {len(models)} models:\x1b[0m\r\n")
            self._model_list = []
            for i, m in enumerate(models[:9]):
                num = i + 1
                marker = " \x1b[32m(current)\x1b[0m" if m == model else ""
                self._stream.feed(f"  \x1b[1;33m[{num}]\x1b[0m {m}{marker}\r\n")
                self._model_list.append((num, m))
            self._stream.feed("\x1b[37mPress 1..9 to select, any other key for default.\x1b[0m\r\n")
            self._connect_provider = provider
            self._connect_key = key
            self._connect_url = base_url
            self._connect_model = model
        else:
            chosen = models[0] if models else model
            self._do_connect(provider, key, chosen, base_url)

    def _fetch_models(self, provider: str, api_key: str, base_url: str):
        try:
            import requests
            if provider == "ollama":
                url = base_url.replace("/v1/chat/completions", "") if base_url else "http://localhost:11434"
                url = url.rstrip("/") + "/api/tags"
                resp = requests.get(url, timeout=5)
                data = resp.json()
                return [m.get("name", m.get("model", str(m)))
                        for m in data.get("models", [])]
            elif provider == "custom" and base_url:
                base = base_url.rsplit("/chat/completions", 1)[0].rstrip("/")
                if not base:
                    base = base_url.rstrip("/")
                url = f"{base}/models"
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = requests.get(url, headers=headers, timeout=5)
                data = resp.json()
                return [m.get("id", m.get("name", str(m)))
                        for m in data.get("data", [])]
        except Exception:
            pass
        return []

    def _do_connect(self, provider: str, api_key: str, model: str, base_url: str):
        try:
            from tpq.ai_client import AIClient
            self._ai_client = AIClient(provider, api_key, model if model else None, base_url)
            self._settings.set("ai_last_provider", provider)
            if model:
                self._settings.set("ai_models", {
                    **self._settings.get("ai_models", {}), provider: model
                })
            info = self._ai_client.PROVIDERS[provider]
            self._stream.feed(f"\x1b[32m✓ Connected to {info['name']} ({self._ai_client.model})\x1b[0m\r\n")
            self._stream.feed("\x1b[37mType /ai to start chatting.\x1b[0m\r\n")
        except Exception as e:
            self._stream.feed(f"\x1b[31mFailed to connect: {e}\x1b[0m\r\n")

    def _cmd_wnotes(self, args: str):
        filename = None
        text = args
        if args.startswith('-'):
            parts = args.split(None, 1)
            filename = parts[0][1:]
            text = parts[1] if len(parts) > 1 else ""

        if not text.strip():
            self._stream.feed("\x1b[33mUsage: /wnotes [-filename.md] your note text here\x1b[0m\r\n")
            return

        from tpq.notes import NotesManager
        nm = NotesManager()
        try:
            path = nm.write_note(text, filename)
            self._stream.feed(f"\x1b[32mNote saved to: {path}\x1b[0m\r\n")
        except Exception as e:
            self._stream.feed(f"\x1b[31mError saving note: {e}\x1b[0m\r\n")

    def _cmd_onotes(self, args: str):
        filename = None
        if args.startswith('-'):
            filename = args[1:].strip()

        from tpq.notes import NotesManager
        nm = NotesManager()
        try:
            path = nm.open_notes(filename)
            self._stream.feed(f"\x1b[32mOpening notes: {path}\x1b[0m\r\n")
        except Exception as e:
            self._stream.feed(f"\x1b[31mError opening notes: {e}\x1b[0m\r\n")

    def _cmd_help(self):
        help_lines = [
            "\x1b[1;37m=== TPQ Terminal Commands ===\x1b[0m",
            "",
            "\x1b[36m/history [terms]\x1b[0m    Search command history",
            "\x1b[36m/ai\x1b[0m               Enter AI chat mode",
            "\x1b[36m/ai off\x1b[0m           Exit AI chat mode",
            "\x1b[36m/connect <provider>\x1b[0m Connect to AI (openai|claude|gemini|deepseek|ollama|custom)",
            "\x1b[36m/wnotes [-f] text\x1b[0m  Save a note",
            "\x1b[36m/onotes [-f]\x1b[0m       Open notes file",
            "\x1b[36m/help\x1b[0m             Show this help",
            "",
            "\x1b[37mKeyboard shortcuts:\x1b[0m",
            "  Ctrl+R            Interactive history search",
            "  Shift+Ctrl+C      Copy",
            "  Shift+Ctrl+V      Paste",
            "  Ctrl+L            Clear screen",
            "  F11               Fullscreen",
            "",
            "\x1b[37mAI Providers: OpenAI, Claude, Gemini, DeepSeek, Ollama (local), Custom API\x1b[0m",
        ]
        for line in help_lines:
            self._stream.feed(line + "\r\n")

    def _enter_ai_mode(self):
        if self._ai_client is None:
            provider = self._settings.get("ai_last_provider", "")
            if provider:
                self._cmd_connect(provider)
            if self._ai_client is None:
                self._stream.feed("\x1b[33mNo AI provider configured. Use /connect <provider> first.\x1b[0m\r\n")
                self._stream.feed("\x1b[37mThen set your API key in Preferences.\x1b[0m\r\n")
                return

        self._ai_mode = True
        self._ai_input = ""
        self._ai_client.reset()
        info = self._ai_client.PROVIDERS[self._ai_client.provider]
        self._stream.feed(f"\r\n\x1b[1;35m=== AI Chat Mode: {info['name']} ({self._ai_client.model}) ===\x1b[0m\r\n")
        self._stream.feed("\x1b[37mType your message and press Enter. Type /ai off to exit.\x1b[0m\r\n\r\n")
        self._stream.feed("\x1b[35mYou>\x1b[0m ")
        self.update()

    def _exit_ai_mode(self):
        self._ai_mode = False
        self._ai_input = ""
        self._stream.feed("\r\n\x1b[1;35m=== AI Chat Ended ===\x1b[0m\r\n")
        self._send_to_child(b'\n')
        self.update()

    def _handle_ai_key(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            message = self._ai_input.strip()
            self._stream.feed("\r\n")
            if message.lower() == "/ai off":
                self._ai_input = ""
                self._exit_ai_mode()
                self.update()
                return
            if not message:
                self._stream.feed("\x1b[35mYou>\x1b[0m ")
                self.update()
                return
            self._ai_input = ""
            self._process_ai_message(message)
            return

        if key == Qt.Key.Key_Backspace:
            if self._ai_input:
                self._ai_input = self._ai_input[:-1]
                self._stream.feed('\b \b')
            self.update()
            return

        if key == Qt.Key.Key_Escape:
            self._ai_input = ""
            self._stream.feed("\r\n\x1b[35mYou>\x1b[0m ")
            self.update()
            return

        if text and len(text) == 1 and ord(text[0]) >= 0x20:
            self._ai_input += text
            self._stream.feed(text)
            self.update()
            return

    def _process_ai_message(self, message: str):
        from PyQt6.QtWidgets import QApplication

        self._stream.feed("\x1b[36mAI>\x1b[0m \x1b[33m● Thinking\x1b[0m")
        self.update()
        QApplication.processEvents()

        try:
            stream = self._ai_client.chat_stream(message)
            first_token = True
            for token in stream:
                if first_token:
                    first_token = False
                    self._stream.feed(f"\r\x1b[36mAI>\x1b[0m ")
                self._stream.feed(token)
                self.update()
                QApplication.processEvents()
        except Exception as e:
            self._stream.feed(f"\r\x1b[31mError: {e}\x1b[0m\r\n")
            self._stream.feed("\x1b[35mYou>\x1b[0m ")
            self.update()
            return

        self._stream.feed("\r\n\r\n\x1b[35mYou>\x1b[0m ")
        self.update()

    def _start_history_search(self):
        self._history_search_mode = True
        self._history_search_query = ""
        self._history_search_results = self._history.interactive_search("", 100)
        self._history_search_index = 0
        self.update()

    def _handle_history_search_key(self, event: QKeyEvent):
        key = event.key()
        text = event.text()
        mods = event.modifiers()

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._accept_history_search()
            return
        if key == Qt.Key.Key_Escape:
            self._cancel_history_search()
            return
        if key == Qt.Key.Key_Backspace:
            if self._history_search_query:
                self._history_search_query = self._history_search_query[:-1]
                self._history_search_results = self._history.interactive_search(
                    self._history_search_query, 100
                )
                self._history_search_index = 0
                self.update()
            return
        if key == Qt.Key.Key_R and mods == Qt.KeyboardModifier.ControlModifier:
            if self._history_search_results:
                self._history_search_index = (
                    self._history_search_index + 1
                ) % len(self._history_search_results)
                self.update()
            return
        if key == Qt.Key.Key_Up:
            if self._history_search_results:
                self._history_search_index = (
                    self._history_search_index - 1
                ) % len(self._history_search_results)
                self.update()
            return
        if key == Qt.Key.Key_Down:
            if self._history_search_results:
                self._history_search_index = (
                    self._history_search_index + 1
                ) % len(self._history_search_results)
                self.update()
            return

        if text and len(text) == 1 and ord(text[0]) >= 0x20:
            self._history_search_query += text
            self._history_search_results = self._history.interactive_search(
                self._history_search_query, 100
            )
            self._history_search_index = 0
            self.update()
            return

    def _accept_history_search(self):
        if self._history_search_results and self._history_search_index < len(self._history_search_results):
            cmd = self._history_search_results[self._history_search_index][0]
            self._history_search_mode = False
            self._send_to_child(cmd.encode('utf-8'))
            self._send_to_child(b'\r')
            self._input_shadow = cmd
            self.update()

    def _cancel_history_search(self):
        self._history_search_mode = False
        self._history_search_query = ""
        self._history_search_results = []
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            col, abs_row = self._pos_to_cell(event.pos())
            self._sel_start = (col, abs_row)
            self._sel_end = (col, abs_row)
            self._last_mouse_pos = event.pos()
            self._auto_scroll_timer.start(30)
            self.update()
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.paste_selection()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._selecting:
            self._last_mouse_pos = event.pos()
            col, abs_row = self._pos_to_cell(event.pos())
            col = min(self._screen.columns - 1, max(0, col))
            self._sel_end = (col, abs_row)
            self._update_auto_scroll(event.pos())
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = False
            self._auto_scroll_timer.stop()
            self._auto_scroll_delta = 0
            if self._settings.get("auto_copy_selection", True):
                self.copy()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        scroll_lines = max(1, abs(delta) // 120)

        total_lines = self._total_lines()
        visible_rows = max(1, self.height() // self._cell_h)
        max_offset = max(0, total_lines - visible_rows)

        if delta > 0:
            self._scroll_offset = max(0, self._scroll_offset - scroll_lines)
        else:
            self._scroll_offset = min(max_offset, self._scroll_offset + scroll_lines)

        self._scrollbar.blockSignals(True)
        self._scrollbar.setValue(self._scroll_offset)
        self._scrollbar.blockSignals(False)
        self.update()

    def _update_scrollbar(self):
        total_lines = self._total_lines()
        visible_rows = max(1, self.height() // self._cell_h)
        max_offset = max(0, total_lines - visible_rows)
        if self._scroll_offset > max_offset:
            self._scroll_offset = max_offset
        if max_offset > 0:
            self._scrollbar.setRange(0, max_offset)
            self._scrollbar.setPageStep(visible_rows)
            self._scrollbar.setValue(self._scroll_offset)
            self._scrollbar.setVisible(self._scrollbar_visible)
        else:
            self._scrollbar.setRange(0, 0)
            self._scrollbar.setVisible(False)

    def _on_scrollbar_changed(self, value: int):
        self._scroll_offset = value
        self.update()

    def _on_scrollbar_slider(self, value: int):
        self._scroll_offset = value
        self.update()

    def set_scrollbar_visible(self, visible: bool):
        self._scrollbar_visible = visible
        if not visible or len(self._scrollback) == 0:
            self._scrollbar.setVisible(False)
        else:
            self._scrollbar.setVisible(True)

    def _update_auto_scroll(self, pos: QPoint):
        margin = self._cell_h * 2
        y = pos.y()
        h = self.height()
        if y < margin:
            self._auto_scroll_delta = -max(1, (margin - y) // (self._cell_h // 2))
        elif y > h - margin:
            self._auto_scroll_delta = max(1, (y - (h - margin)) // (self._cell_h // 2))
        else:
            self._auto_scroll_delta = 0

    def _auto_scroll(self):
        if not self._selecting or self._auto_scroll_delta == 0:
            return
        total_lines = self._total_lines()
        visible_rows = max(1, self.height() // self._cell_h)
        max_offset = max(0, total_lines - visible_rows)

        new_offset = self._scroll_offset + self._auto_scroll_delta
        new_offset = max(0, min(max_offset, new_offset))
        if new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self._update_scrollbar()
            if self._last_mouse_pos:
                col, abs_row = self._pos_to_cell(self._last_mouse_pos)
                self._sel_end = (min(self._screen.columns - 1, max(0, col)), abs_row)
            self.update()

    def copy(self):
        text = self._selection_to_text()
        if text:
            cb = _get_clipboard()
            if cb:
                cb.setText(text)

    def paste(self):
        cb = _get_clipboard()
        if cb:
            text = cb.text()
            if text:
                self._send_to_child(text.encode('utf-8'))
                self._input_shadow = ""

    def paste_selection(self):
        cb = _get_clipboard()
        if cb:
            text = cb.text(cb.Mode.Selection)
            if text:
                self._send_to_child(text.encode('utf-8'))
                self._input_shadow = ""

    def _selection_to_text(self) -> str:
        if not self._sel_start or not self._sel_end:
            return ""

        start_col, start_abs = self._sel_start
        end_col, end_abs = self._sel_end

        if (end_abs, end_col) < (start_abs, start_col):
            start_col, end_col = end_col, start_col
            start_abs, end_abs = end_abs, start_abs

        lines = []
        for abs_row in range(start_abs, end_abs + 1):
            line_data = self._get_line(abs_row)
            if line_data is None:
                continue

            if abs_row == start_abs and abs_row == end_abs:
                chars = [ch.data for ch in line_data[start_col:end_col]]
            elif abs_row == start_abs:
                chars = [ch.data for ch in line_data[start_col:]]
            elif abs_row == end_abs:
                chars = [ch.data for ch in line_data[:end_col]]
            else:
                chars = [ch.data for ch in line_data]

            lines.append(''.join(chars).rstrip())

        return '\n'.join(lines)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_size()
        sb_w = self._scrollbar_w
        self._scrollbar.setGeometry(self.width() - sb_w, 0, sb_w, self.height())
        self._update_scrollbar()

    def _show_context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        copy_act = menu.addAction("Copy")
        copy_act.triggered.connect(self.copy)
        paste_act = menu.addAction("Paste")
        paste_act.triggered.connect(self.paste)
        menu.addSeparator()
        fm_act = menu.addAction("Open File Manager Here")
        fm_act.triggered.connect(self._context_open_fm)
        menu.addSeparator()
        sel_act = menu.addAction("Select All")
        sel_act.triggered.connect(self._context_select_all)
        menu.exec(self.mapToGlobal(pos))

    def _context_open_fm(self):
        w = self.window()
        if hasattr(w, 'open_file_manager'):
            w.open_file_manager()

    def _context_select_all(self):
        self._sel_start = (0, 0)
        end_abs = len(self._scrollback) + self._screen.lines - 1
        self._sel_end = (self._screen.columns - 1, end_abs)
        self.update()

    def _replay_history_number(self, num: int):
        for n, cmd in self._history_show_results:
            if n == num:
                self._send_to_child(cmd.encode('utf-8'))
                self._send_to_child(b'\r')
                self._input_shadow = cmd
                self._history_show_results = []
                self.update()
                return

    def _autocomplete_tpq(self):
        TPQ_COMMANDS = [
            "history", "ai", "connect", "wnotes", "onotes", "help", "clear",
        ]
        shadow = self._input_shadow
        if not shadow.startswith('/'):
            return
        cmd = shadow[1:]
        matches = [c for c in TPQ_COMMANDS if c.startswith(cmd)]
        if len(matches) == 1:
            suffix = matches[0][len(cmd):]
            self._input_shadow += suffix
            self._stream.feed(suffix)
            self.update()
        elif len(matches) > 1:
            common = os.path.commonprefix(matches)
            if len(common) > len(cmd):
                suffix = common[len(cmd):]
                self._input_shadow += suffix
                self._stream.feed(suffix)
                self.update()
            else:
                self._stream.feed("\r\n")
                for m in matches:
                    self._stream.feed(f"  /{m}\r\n")
                self._stream.feed(f"\x1b[35m{chr(0x2500) * 20}\x1b[0m\r\n")
                self._stream.feed(self._input_shadow)
                self.update()

    def _select_model_number(self, num: int):
        for n, model in self._model_list:
            if n == num:
                self._do_connect(self._connect_provider, self._connect_key, model, self._connect_url)
                self._model_list = []
                return
        self._select_model_default()

    def _select_model_default(self):
        if self._connect_provider:
            self._do_connect(self._connect_provider, self._connect_key,
                             self._connect_model, self._connect_url)
        self._model_list = []

    def get_cwd(self) -> str:
        if self._child_pid:
            try:
                cwd_link = f"/proc/{self._child_pid}/cwd"
                if os.path.exists(cwd_link):
                    return os.readlink(cwd_link)
            except OSError:
                pass
        return os.path.expanduser("~")

    def set_encoding(self, encoding: str):
        self._encoding = encoding

    def kill_process(self, sig: int):
        if self._child_pid:
            try:
                os.kill(self._child_pid, sig)
            except (ProcessLookupError, OSError):
                pass

    def close_terminal(self):
        self._cursor_timer.stop()
        self._read_timer.stop()
        self._auto_scroll_timer.stop()
        if self._child_pid:
            try:
                os.kill(self._child_pid, signal.SIGHUP)
            except (ProcessLookupError, OSError):
                pass
            try:
                os.waitpid(self._child_pid, os.WNOHANG)
            except ChildProcessError:
                pass
            self._child_pid = None
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

    def kill_shell(self):
        if self._child_pid:
            try:
                os.kill(self._child_pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
