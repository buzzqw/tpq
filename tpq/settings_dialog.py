from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QSpinBox, QComboBox, QCheckBox, QPushButton,
    QFileDialog, QFormLayout, QGroupBox, QDoubleSpinBox, QDialogButtonBox,
    QSlider, QMessageBox, QColorDialog, QGridLayout, QScrollArea, QFrame,
    QRadioButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette

from tpq.settings import Settings, COLOR_PALETTES


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._settings.load()
        self.setWindowTitle("Preferences - TPQ")
        self.resize(700, 560)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_appearance_tab(), "Appearance")
        tabs.addTab(self._create_colors_tab(), "Colors")
        tabs.addTab(self._create_compatibility_tab(), "Compatibility")
        tabs.addTab(self._create_ai_tab(), "AI")
        tabs.addTab(self._create_notes_tab(), "Notes")
        tabs.addTab(self._create_about_tab(), "About")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_general_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QFormLayout(content)

        layout.addRow(QLabel("<b>Title</b>"))
        self._initial_title = QLineEdit(self._settings.get("tab_title", "Terminal"))
        layout.addRow("Initial title:", self._initial_title)

        self._dynamic_title = QComboBox()
        self._dynamic_title.addItems([
            "Replace initial title",
            "Goes before initial title",
            "Goes after initial title",
            "Isn't displayed",
        ])
        dyn_map = {"replace": 0, "before": 1, "after": 2, "hide": 3}
        self._dynamic_title.setCurrentIndex(
            dyn_map.get(self._settings.get("dynamic_title", "replace"), 0)
        )
        layout.addRow("Dynamically-set title:", self._dynamic_title)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Command</b>"))

        self._login_shell = QCheckBox()
        self._login_shell.setChecked(self._settings.get("login_shell", True))
        layout.addRow("Run command as login shell:", self._login_shell)

        self._shell_edit = QLineEdit(self._settings.get("shell_command", "/bin/bash"))
        layout.addRow("Run custom command:", self._shell_edit)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Scrolling</b>"))

        self._scrollbar_pos = QComboBox()
        self._scrollbar_pos.addItems(["Right side", "Left side", "Disabled"])
        pos_map = {"right": 0, "left": 1, "disabled": 2}
        self._scrollbar_pos.setCurrentIndex(
            pos_map.get(self._settings.get("scrollbar_position", "right"), 0)
        )
        layout.addRow("Scrollbar is:", self._scrollbar_pos)

        self._scrollback_spin = QSpinBox()
        self._scrollback_spin.setRange(0, 100000)
        self._scrollback_spin.setSpecialValueText("Unlimited")
        self._scrollback_spin.setSingleStep(500)
        self._scrollback_spin.setValue(self._settings.get("scrollback_lines", 5000))
        layout.addRow("Scrollback lines:", self._scrollback_spin)

        self._scroll_on_output = QCheckBox()
        self._scroll_on_output.setChecked(
            self._settings.get("scroll_on_output", True)
        )
        layout.addRow("Scroll on output:", self._scroll_on_output)

        self._scroll_on_keystroke = QCheckBox()
        self._scroll_on_keystroke.setChecked(
            self._settings.get("scroll_on_keystroke", True)
        )
        layout.addRow("Scroll on keystroke:", self._scroll_on_keystroke)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Other</b>"))

        self._confirm_close = QCheckBox()
        self._confirm_close.setChecked(self._settings.get("confirm_close", True))
        layout.addRow("Confirm before closing:", self._confirm_close)

        self._auto_copy_sel = QCheckBox()
        self._auto_copy_sel.setChecked(self._settings.get("auto_copy_selection", True))
        layout.addRow("Auto-copy selection:", self._auto_copy_sel)

        self._unsafe_paste = QCheckBox()
        self._unsafe_paste.setChecked(
            self._settings.get("show_unsafe_paste_dialog", True)
        )
        layout.addRow("Show unsafe paste dialog:", self._unsafe_paste)

        fm_layout = QHBoxLayout()
        self._file_manager = QLineEdit(self._settings.get("file_manager", ""))
        self._file_manager.setPlaceholderText("auto-detect")
        fm_layout.addWidget(self._file_manager)
        layout.addRow("File manager:", fm_layout)

        scroll.setWidget(content)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    def _create_appearance_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        layout.addRow(QLabel("<b>Font</b>"))

        self._font_family = QLineEdit(self._settings.get("font_family", "Monospace"))
        layout.addRow("Font:", self._font_family)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 48)
        self._font_size.setValue(self._settings.get("font_size", 12))
        layout.addRow("Size:", self._font_size)

        self._allow_bold = QCheckBox()
        self._allow_bold.setChecked(self._settings.get("allow_bold_text", True))
        layout.addRow("Allow bold text:", self._allow_bold)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Colors</b>"))

        self._fg_color = self._make_color_button(
            self._settings.get("foreground_color", "#ffffff")
        )
        self._bg_color = self._make_color_button(
            self._settings.get("background_color", "#0a0a0a")
        )
        self._cursor_color = self._make_color_button(
            self._settings.get("cursor_color", "#ffffff")
        )
        self._highlight_color = self._make_color_button(
            self._settings.get("highlight_color", "#ffffff")
        )
        self._highlight_bg = self._make_color_button(
            self._settings.get("highlight_bg_color", "#446688")
        )

        color_grid = QGridLayout()
        for row, (label, btn) in enumerate([
            ("Foreground:", self._fg_color), ("Background:", self._bg_color),
            ("Cursor:", self._cursor_color), ("Highlight text:", self._highlight_color),
        ]):
            color_grid.addWidget(QLabel(label), row // 2, (row % 2) * 2)
            color_grid.addWidget(btn, row // 2, (row % 2) * 2 + 1)
        color_grid.addWidget(QLabel("Highlight bg:"), 2, 0)
        color_grid.addWidget(self._highlight_bg, 2, 1)
        layout.addRow("", color_grid)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Tab colors</b>"))

        tab_grid = QGridLayout()
        tab_grid.addWidget(QLabel("Tab title:"), 0, 0)
        self._tab_title_color = QLineEdit(self._settings.get("tab_title_color", "#ffffff"))
        tab_grid.addWidget(self._tab_title_color, 0, 1)
        tab_grid.addWidget(QLabel("Active tab:"), 0, 2)
        self._tab_active_color = QLineEdit(self._settings.get("tab_active_title_color", "#ffffff"))
        tab_grid.addWidget(self._tab_active_color, 0, 3)
        layout.addRow("", tab_grid)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Cursor</b>"))

        self._cursor_shape = QComboBox()
        self._cursor_shape.addItems(["block", "underline", "beam"])
        self._cursor_shape.setCurrentText(self._settings.get("cursor_shape", "block"))
        layout.addRow("Cursor shape:", self._cursor_shape)

        self._cursor_blink = QCheckBox()
        self._cursor_blink.setChecked(self._settings.get("cursor_blink", True))
        layout.addRow("Cursor blinking:", self._cursor_blink)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Transparency</b>"))

        self._opacity = QDoubleSpinBox()
        self._opacity.setRange(0.3, 1.0)
        self._opacity.setSingleStep(0.05)
        self._opacity.setValue(self._settings.get("opacity", 1.0))
        layout.addRow("Opacity:", self._opacity)

        self._transparency = QCheckBox()
        self._transparency.setChecked(self._settings.get("enable_transparency", False))
        layout.addRow("Enable transparency:", self._transparency)

        return w

    def _make_color_button(self, hex_color: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(60, 28)
        color = QColor(hex_color)
        self._update_btn_color(btn, color)
        btn._color = color
        btn.clicked.connect(lambda checked, b=btn: self._pick_color(b))
        return btn

    def _update_btn_color(self, btn, color):
        btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #555; border-radius: 3px;"
        )
        btn._color = color

    def _pick_color(self, btn):
        color = QColorDialog.getColor(btn._color, self, "Choose color")
        if color.isValid():
            self._update_btn_color(btn, color)

    def _create_colors_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)

        layout.addWidget(QLabel("<b>Palette</b>"))

        saved = self._settings.get("custom_palette", None)
        scheme = self._settings.get("color_scheme", "dark")
        palette = saved if saved else COLOR_PALETTES.get(scheme, COLOR_PALETTES["dark"])

        grid = QGridLayout()
        grid.setSpacing(4)

        self._palette_btns = {}
        labels_16 = [
            ("Black", "Red", "Green", "Yellow"),
            ("Blue", "Magenta", "Cyan", "White"),
            ("B.Black", "B.Red", "B.Green", "B.Yellow"),
            ("B.Blue", "B.Magenta", "B.Cyan", "B.White"),
        ]
        keys_16 = [
            ("black", "red", "green", "yellow"),
            ("blue", "magenta", "cyan", "white"),
            ("brightblack", "brightred", "brightgreen", "brightyellow"),
            ("brightblue", "brightmagenta", "brightcyan", "brightwhite"),
        ]

        for row in range(4):
            for col in range(4):
                key = keys_16[row][col]
                label = labels_16[row][col]
                btn = self._make_color_button(palette.get(key, "#000000"))
                btn.setFixedSize(48, 24)
                self._palette_btns[key] = btn
                cell = QVBoxLayout()
                lbl = QLabel(label)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("font-size: 10px; color: #888;")
                cell.addWidget(lbl)
                cell.addWidget(btn)
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addLayout(cell, row, col)

        layout.addLayout(grid)

        btns_layout = QHBoxLayout()
        load_btn = QPushButton("Load Preset...")
        load_btn.clicked.connect(self._load_palette_preset)
        save_btn = QPushButton("Save As...")
        save_btn.clicked.connect(self._save_palette)
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self._reset_palette)
        btns_layout.addWidget(load_btn)
        btns_layout.addWidget(save_btn)
        btns_layout.addWidget(reset_btn)
        layout.addLayout(btns_layout)
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    def _load_palette_preset(self):
        menu = QDialog(self)
        menu.setWindowTitle("Load Palette")
        menu.resize(300, 100)
        ml = QVBoxLayout(menu)
        combo = QComboBox()
        combo.addItems(["Dark (default)", "Light", "Solarized Dark", "Solarized Light",
                         "Monokai", "Gruvbox Dark", "Nord"])
        ml.addWidget(combo)
        btn = QPushButton("Load")
        btn.clicked.connect(lambda: self._apply_preset(combo.currentText(), menu))
        ml.addWidget(btn)
        menu.exec()

    def _apply_preset(self, name: str, dialog: QDialog):
        presets = {
            "Dark (default)": COLOR_PALETTES["dark"],
            "Light": COLOR_PALETTES["light"],
            "Solarized Dark": {
                "black": "#002b36", "red": "#dc322f", "green": "#859900",
                "yellow": "#b58900", "blue": "#268bd2", "magenta": "#d33682",
                "cyan": "#2aa198", "white": "#eee8d5",
                "brightblack": "#073642", "brightred": "#cb4b16",
                "brightgreen": "#586e75", "brightyellow": "#657b83",
                "brightblue": "#839496", "brightmagenta": "#6c71c4",
                "brightcyan": "#93a1a1", "brightwhite": "#fdf6e3",
            },
            "Monokai": {
                "black": "#272822", "red": "#f92672", "green": "#a6e22e",
                "yellow": "#f4bf75", "blue": "#66d9ef", "magenta": "#ae81ff",
                "cyan": "#a1efe4", "white": "#f8f8f2",
                "brightblack": "#75715e", "brightred": "#f92672",
                "brightgreen": "#a6e22e", "brightyellow": "#f4bf75",
                "brightblue": "#66d9ef", "brightmagenta": "#ae81ff",
                "brightcyan": "#a1efe4", "brightwhite": "#f9f8f5",
            },
            "Nord": {
                "black": "#3b4252", "red": "#bf616a", "green": "#a3be8c",
                "yellow": "#ebcb8b", "blue": "#81a1c1", "magenta": "#b48ead",
                "cyan": "#88c0d0", "white": "#e5e9f0",
                "brightblack": "#4c566a", "brightred": "#bf616a",
                "brightgreen": "#a3be8c", "brightyellow": "#ebcb8b",
                "brightblue": "#81a1c1", "brightmagenta": "#b48ead",
                "brightcyan": "#8fbcbb", "brightwhite": "#eceff4",
            },
        }
        palette = presets.get(name, COLOR_PALETTES["dark"])
        for key, btn in self._palette_btns.items():
            if key in palette:
                self._update_btn_color(btn, QColor(palette[key]))
        dialog.accept()

    def _save_palette(self):
        QMessageBox.information(self, "Save Palette",
                                "Set your colors in the palette fields above and click OK.\n"
                                "The custom palette will be saved with your preferences.")

    def _reset_palette(self):
        scheme = "dark"
        palette = COLOR_PALETTES.get(scheme, COLOR_PALETTES["dark"])
        for key, btn in self._palette_btns.items():
            if key in palette:
                self._update_btn_color(btn, QColor(palette[key]))

    def _create_compatibility_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        layout.addRow(QLabel("<b>Keyboard</b>"))

        self._backspace_bind = QComboBox()
        self._backspace_bind.addItems([
            "Auto-detect", "ASCII DEL (127)", "Escape sequence", "Control-H (8)"
        ])
        bs_map = {"auto": 0, "ascii-del": 1, "escape-sequence": 2, "control-h": 3}
        self._backspace_bind.setCurrentIndex(
            bs_map.get(self._settings.get("backspace_binding", "ascii-del"), 1)
        )
        layout.addRow("Backspace key generates:", self._backspace_bind)

        self._delete_bind = QComboBox()
        self._delete_bind.addItems([
            "Auto-detect", "Escape sequence", "ASCII DEL (127)", "Control-H (8)"
        ])
        del_map = {"auto": 0, "escape-sequence": 1, "ascii-del": 2, "control-h": 3}
        self._delete_bind.setCurrentIndex(
            del_map.get(self._settings.get("delete_binding", "escape-sequence"), 1)
        )
        layout.addRow("Delete key generates:", self._delete_bind)

        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Encoding</b>"))

        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems([
            "UTF-8", "ISO-8859-1", "ISO-8859-15", "UTF-16",
            "CP1252", "CP850", "ASCII", "KOI8-R", "Shift_JIS", "EUC-JP", "GBK",
        ])
        self._encoding_combo.setCurrentText(self._settings.get("encoding", "UTF-8"))
        layout.addRow("Default encoding:", self._encoding_combo)

        layout.addRow(QLabel(""))
        reset_btn = QPushButton("Reset Compatibility Options to Defaults")
        reset_btn.clicked.connect(self._reset_compatibility)
        layout.addRow("", reset_btn)

        return w

    def _reset_compatibility(self):
        self._backspace_bind.setCurrentIndex(1)
        self._delete_bind.setCurrentIndex(1)
        self._encoding_combo.setCurrentText("UTF-8")

    def _create_ai_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        group = QGroupBox("AI Providers")
        gl = QFormLayout(group)

        self._ai_providers = {}
        keys = self._settings.get("ai_keys", {})
        models = self._settings.get("ai_models", {})
        urls = self._settings.get("ai_urls", {})

        all_providers = ["openai", "claude", "gemini", "deepseek", "ollama", "custom"]

        for provider in all_providers:
            key_edit = QLineEdit(keys.get(provider, ""))
            if provider in ("ollama", "custom"):
                key_edit.setPlaceholderText("(optional)")
            else:
                key_edit.setEchoMode(QLineEdit.EchoMode.Password)
                key_edit.setPlaceholderText(f"{provider.upper()}_API_KEY")
            gl.addRow(f"{provider.title()} API Key:", key_edit)

            model_edit = QLineEdit(models.get(provider, ""))
            model_edit.setPlaceholderText("default model")
            gl.addRow(f"{provider.title()} Model:", model_edit)

            self._ai_providers[provider] = (key_edit, model_edit)

            if provider in ("ollama", "custom"):
                url_edit = QLineEdit(urls.get(provider, ""))
                if provider == "ollama":
                    url_edit.setPlaceholderText("http://localhost:11434/v1/chat/completions")
                else:
                    url_edit.setPlaceholderText("http://localhost:8080/v1/chat/completions")
                gl.addRow(f"{provider.title()} URL:", url_edit)
                self._ai_providers[provider + "_url"] = url_edit

        layout.addWidget(group)
        layout.addStretch()
        return w

    def _create_notes_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        notes_dir_layout = QHBoxLayout()
        self._notes_dir = QLineEdit(self._settings.get("notes_dir", ""))
        self._notes_dir.setPlaceholderText("Default: ~/")
        notes_dir_btn = QPushButton("Browse...")
        notes_dir_btn.clicked.connect(lambda: self._browse_dir(self._notes_dir, "Notes Directory"))
        notes_dir_layout.addWidget(self._notes_dir)
        notes_dir_layout.addWidget(notes_dir_btn)
        layout.addRow("Notes directory:", notes_dir_layout)

        notes_file_layout = QHBoxLayout()
        self._notes_file = QLineEdit(self._settings.get("notes_file", ""))
        self._notes_file.setPlaceholderText("Default: notes.md")
        notes_file_btn = QPushButton("Browse...")
        notes_file_btn.clicked.connect(lambda: self._browse_file(self._notes_file, "Notes File"))
        notes_file_layout.addWidget(self._notes_file)
        notes_file_layout.addWidget(notes_file_btn)
        layout.addRow("Default notes file:", notes_file_layout)

        self._editor_cmd = QLineEdit(self._settings.get("editor_command", "nano"))
        layout.addRow("Editor command:", self._editor_cmd)

        return w

    def _create_about_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("TPQ Terminal")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        author = QLabel("Andres Zanzani")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)

        license_lbl = QLabel("Licensed under EUPL 1.2")
        license_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc = QLabel(
            "Terminale Python Qt — Advanced Terminal Emulator\n"
            "Python + PyQt6 + pyte"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)

        features = QLabel(
            "Features:\n"
            "- Full terminal emulation (ANSI/xterm-256color)\n"
            "- Command history with interactive search (Ctrl+R)\n"
            "- AI chat (OpenAI, Claude, Gemini, DeepSeek, Ollama, Custom)\n"
            "- /history, /ai, /connect, /wnotes, /onotes\n"
            "- Tab autocompletion for TPQ commands\n"
            "- Tabs with detach, move, reorder\n"
            "- 16-color palette editor with presets\n"
            "- Full menu bar, toolbar, scrollbar\n"
            "- Send signals, Set encoding, File manager integration"
        )
        features.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(author)
        layout.addWidget(license_lbl)
        layout.addWidget(desc)
        layout.addSpacing(20)
        layout.addWidget(features)
        return w

    def _browse_dir(self, line_edit: QLineEdit, title: str):
        path = QFileDialog.getExistingDirectory(self, title, line_edit.text() or "")
        if path:
            line_edit.setText(path)

    def _browse_file(self, line_edit: QLineEdit, title: str):
        path, _ = QFileDialog.getSaveFileName(self, title, line_edit.text() or "",
                                               "Markdown (*.md);;All (*)")
        if path:
            line_edit.setText(path)

    def _save_and_close(self):
        s = self._settings
        s.set("tab_title", self._initial_title.text())
        dyn_map = {0: "replace", 1: "before", 2: "after", 3: "hide"}
        s.set("dynamic_title", dyn_map.get(self._dynamic_title.currentIndex(), "replace"))
        s.set("login_shell", self._login_shell.isChecked())
        s.set("shell_command", self._shell_edit.text())

        pos_map = {0: "right", 1: "left", 2: "disabled"}
        s.set("scrollbar_position", pos_map.get(self._scrollbar_pos.currentIndex(), "right"))
        s.set("scrollback_lines", self._scrollback_spin.value())
        s.set("scroll_on_output", self._scroll_on_output.isChecked())
        s.set("scroll_on_keystroke", self._scroll_on_keystroke.isChecked())
        s.set("confirm_close", self._confirm_close.isChecked())
        s.set("auto_copy_selection", self._auto_copy_sel.isChecked())
        s.set("show_unsafe_paste_dialog", self._unsafe_paste.isChecked())
        s.set("file_manager", self._file_manager.text())

        s.set("font_family", self._font_family.text())
        s.set("font_size", self._font_size.value())
        s.set("allow_bold_text", self._allow_bold.isChecked())
        s.set("foreground_color", self._fg_color._color.name())
        s.set("background_color", self._bg_color._color.name())
        s.set("cursor_color", self._cursor_color._color.name())
        s.set("highlight_color", self._highlight_color._color.name())
        s.set("highlight_bg_color", self._highlight_bg._color.name())
        s.set("tab_title_color", self._tab_title_color.text())
        s.set("tab_active_title_color", self._tab_active_color.text())
        s.set("cursor_shape", self._cursor_shape.currentText())
        s.set("cursor_blink", self._cursor_blink.isChecked())
        s.set("opacity", self._opacity.value())
        s.set("enable_transparency", self._transparency.isChecked())

        palette = {}
        for key, btn in self._palette_btns.items():
            palette[key] = btn._color.name()
        s.set("custom_palette", palette)

        bs_map = {0: "auto", 1: "ascii-del", 2: "escape-sequence", 3: "control-h"}
        s.set("backspace_binding", bs_map.get(self._backspace_bind.currentIndex(), "ascii-del"))
        del_map = {0: "auto", 1: "escape-sequence", 2: "ascii-del", 3: "control-h"}
        s.set("delete_binding", del_map.get(self._delete_bind.currentIndex(), "escape-sequence"))
        s.set("encoding", self._encoding_combo.currentText())

        new_keys = {}
        new_models = {}
        new_urls = {}
        for key, val in self._ai_providers.items():
            if key.endswith("_url"):
                provider_name = key.replace("_url", "")
                new_urls[provider_name] = val.text()
            else:
                key_edit, model_edit = val
                new_keys[key] = key_edit.text()
                new_models[key] = model_edit.text()
        s.set("ai_urls", new_urls)
        s.set("ai_keys", new_keys)
        s.set("ai_models", new_models)

        s.set("notes_dir", self._notes_dir.text())
        s.set("notes_file", self._notes_file.text())
        s.set("editor_command", self._editor_cmd.text())

        QMessageBox.information(
            self, "Preferences",
            "Settings saved.\nSome changes may require restarting TPQ to take effect."
        )
        self.accept()
