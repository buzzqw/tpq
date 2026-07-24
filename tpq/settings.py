import os
import json
import shutil

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "tpq")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULTS = {
    "font_family": "Monospace",
    "font_size": 12,
    "color_scheme": "dark",
    "foreground_color": "#ffffff",
    "background_color": "#0a0a0a",
    "cursor_shape": "block",
    "cursor_blink": True,
    "scrollback_lines": 5000,
    "opacity": 1.0,
    "shell_command": os.environ.get("SHELL", "/bin/bash"),
    "notes_file": "",
    "notes_dir": os.path.expanduser("~"),
    "editor_command": os.environ.get("EDITOR", "nano"),
    "ai_provider": "",
    "ai_models": {
        "openai": "",
        "claude": "",
        "gemini": "",
        "deepseek": "",
        "ollama": "",
        "custom": "",
    },
    "ai_urls": {
        "ollama": "http://localhost:11434/v1/chat/completions",
        "custom": "",
    },
    "ai_keys": {
        "openai": "",
        "claude": "",
        "gemini": "",
        "deepseek": "",
        "ollama": "",
        "custom": "",
    },
    "ai_last_provider": "",
    "enable_transparency": False,
    "confirm_close": True,
    "tab_title": "Terminal",
    "encoding": "UTF-8",
    "auto_copy_selection": True,
    "file_manager": "",
    "tab_title_color": "#ffffff",
    "tab_active_title_color": "#ffffff",
    "scrollbar_position": "right",
    "cursor_color": "#ffffff",
    "highlight_color": "#ffffff",
    "highlight_bg_color": "#446688",
    "backspace_binding": "ascii-del",
    "delete_binding": "escape-sequence",
    "show_toolbar": False,
    "show_unsafe_paste_dialog": True,
    "scroll_on_output": True,
    "scroll_on_keystroke": True,
    "allow_bold_text": True,
    "dynamic_title": "replace",
    "login_shell": True,
}

COLOR_PALETTES = {
    "dark": {
        "black": "#0a0a0a",
        "red": "#cc0000",
        "green": "#4e9a06",
        "yellow": "#c4a000",
        "blue": "#3465a4",
        "magenta": "#75507b",
        "purple": "#75507b",
        "cyan": "#06989a",
        "white": "#d3d7cf",
        "brightblack": "#555753",
        "brightred": "#ef2929",
        "brightgreen": "#8ae234",
        "brightyellow": "#fce94f",
        "brightblue": "#729fcf",
        "brightmagenta": "#ad7fa8",
        "brightpurple": "#ad7fa8",
        "brightcyan": "#34e2e2",
        "brightwhite": "#eeeeec",
    },
    "light": {
        "black": "#2e3436",
        "red": "#cc0000",
        "green": "#4e9a06",
        "yellow": "#c4a000",
        "blue": "#3465a4",
        "magenta": "#75507b",
        "purple": "#75507b",
        "cyan": "#06989a",
        "white": "#d3d7cf",
        "brightblack": "#555753",
        "brightred": "#ef2929",
        "brightgreen": "#8ae234",
        "brightyellow": "#fce94f",
        "brightblue": "#729fcf",
        "brightmagenta": "#ad7fa8",
        "brightpurple": "#ad7fa8",
        "brightcyan": "#34e2e2",
        "brightwhite": "#eeeeec",
    },
}


class Settings:
    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = dict(DEFAULTS)
        return cls._instance

    def load(self):
        if self._loaded:
            return
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                for key in DEFAULTS:
                    if key in data:
                        self._data[key] = data[key]
            except (json.JSONDecodeError, OSError):
                self.save()
        else:
            self.save()
        self._loaded = True

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self.save()

    def get_palette(self):
        scheme = self._data.get("color_scheme", "dark")
        return COLOR_PALETTES.get(scheme, COLOR_PALETTES["dark"])

    def get_fg_color(self):
        return self._data.get("foreground_color", "#ffffff")

    def get_bg_color(self):
        return self._data.get("background_color", "#0a0a0a")
