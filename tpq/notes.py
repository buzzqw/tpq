import os
import datetime
import subprocess

from tpq.settings import Settings


class NotesManager:
    def __init__(self):
        self._settings = Settings()

    def _get_notes_path(self, filename: str = None):
        if filename:
            if os.path.isabs(filename):
                return filename
            notes_dir = self._settings.get("notes_dir", os.path.expanduser("~"))
            return os.path.join(notes_dir, filename)

        configured = self._settings.get("notes_file", "")
        if configured and os.path.isfile(configured):
            return configured

        notes_dir = self._settings.get("notes_dir", os.path.expanduser("~"))
        configured_name = configured if configured else "notes.md"
        if not configured_name.endswith(".md"):
            configured_name += ".md"
        return os.path.join(notes_dir, configured_name)

    def write_note(self, text: str, filename: str = None):
        path = self._get_notes_path(filename)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## {ts}\n\n{text}\n"

        with open(path, "a") as f:
            f.write(entry)

        return path

    def open_notes(self, filename: str = None):
        path = self._get_notes_path(filename)
        editor = self._settings.get("editor_command", "nano")

        if not os.path.isfile(path):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write("# TPQ Notes\n\n")

        subprocess.Popen([editor, path], start_new_session=True)

        return path
