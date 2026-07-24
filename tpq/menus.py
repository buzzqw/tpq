import signal
from PyQt6.QtWidgets import QMenuBar, QMenu, QApplication
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt


SIGNALS = [
    ("SIGTERM (15)", signal.SIGTERM),
    ("SIGKILL (9)", signal.SIGKILL),
    ("SIGHUP (1)", signal.SIGHUP),
    ("SIGINT (2)", signal.SIGINT),
    ("SIGQUIT (3)", signal.SIGQUIT),
    ("SIGSTOP (19)", signal.SIGSTOP),
    ("SIGCONT (18)", signal.SIGCONT),
    ("SIGUSR1 (10)", signal.SIGUSR1),
    ("SIGUSR2 (12)", signal.SIGUSR2),
]

ENCODINGS = [
    "UTF-8",
    "ISO-8859-1 (Latin-1)",
    "ISO-8859-15 (Latin-9)",
    "UTF-16",
    "UTF-16BE",
    "UTF-16LE",
    "CP1252 (Windows-1252)",
    "CP850 (DOS Latin-1)",
    "ASCII",
    "KOI8-R",
    "Shift_JIS",
    "EUC-JP",
    "GBK",
]


def create_menubar(parent, terminal_widget):
    menubar = QMenuBar(parent)

    file_menu = menubar.addMenu("&File")

    new_tab_action = QAction("New &Tab", parent)
    new_tab_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
    new_tab_action.triggered.connect(parent.new_tab)
    file_menu.addAction(new_tab_action)

    new_window_action = QAction("New &Window", parent)
    new_window_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
    new_window_action.triggered.connect(parent.new_window)
    file_menu.addAction(new_window_action)

    file_menu.addSeparator()

    open_fm_action = QAction("Open File Manager &Here", parent)
    open_fm_action.triggered.connect(parent.open_file_manager)
    file_menu.addAction(open_fm_action)

    file_menu.addSeparator()

    close_tab_action = QAction("Close Tab", parent)
    close_tab_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
    close_tab_action.triggered.connect(parent.close_tab)
    file_menu.addAction(close_tab_action)

    close_window_action = QAction("Close &Window", parent)
    close_window_action.setShortcut(QKeySequence("Ctrl+Shift+Q"))
    close_window_action.triggered.connect(parent.close)
    file_menu.addAction(close_window_action)

    file_menu.addSeparator()

    quit_action = QAction("&Quit", parent)
    quit_action.setShortcut(QKeySequence("Ctrl+Q"))
    quit_action.triggered.connect(parent.close)
    file_menu.addAction(quit_action)

    edit_menu = menubar.addMenu("&Edit")

    copy_action = QAction("&Copy", parent)
    copy_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
    copy_action.triggered.connect(parent.terminal_copy)
    edit_menu.addAction(copy_action)

    paste_action = QAction("&Paste", parent)
    paste_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
    paste_action.triggered.connect(parent.terminal_paste)
    edit_menu.addAction(paste_action)

    paste_sel_action = QAction("Paste &Selection", parent)
    paste_sel_action.triggered.connect(parent.terminal_paste_selection)
    edit_menu.addAction(paste_sel_action)

    edit_menu.addSeparator()

    select_all_action = QAction("Select &All", parent)
    select_all_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
    select_all_action.triggered.connect(parent.terminal_select_all)
    edit_menu.addAction(select_all_action)

    edit_menu.addSeparator()

    preferences_action = QAction("&Preferences...", parent)
    preferences_action.triggered.connect(parent.open_settings)
    edit_menu.addAction(preferences_action)

    view_menu = menubar.addMenu("&View")

    show_tabs_action = QAction("Always Show &Tabs", parent)
    show_tabs_action.setCheckable(True)
    show_tabs_action.setChecked(parent._tabs.isVisible())
    show_tabs_action.triggered.connect(parent.toggle_tabs_visibility)
    view_menu.addAction(show_tabs_action)
    parent._action_show_tabs = show_tabs_action

    show_menubar_action = QAction("Always Show &Menu Bar", parent)
    show_menubar_action.setCheckable(True)
    show_menubar_action.setChecked(True)
    show_menubar_action.triggered.connect(parent.toggle_menubar_visibility)
    view_menu.addAction(show_menubar_action)
    parent._action_show_menubar = show_menubar_action

    show_scrollbar_action = QAction("Always Show &Scrollbar", parent)
    show_scrollbar_action.setCheckable(True)
    show_scrollbar_action.setChecked(True)
    show_scrollbar_action.triggered.connect(parent.toggle_scrollbar_visibility)
    view_menu.addAction(show_scrollbar_action)
    parent._action_show_scrollbar = show_scrollbar_action

    show_toolbar_action = QAction("Always Show &Toolbar", parent)
    show_toolbar_action.setCheckable(True)
    show_toolbar_action.setChecked(parent._toolbar.isVisible())
    show_toolbar_action.triggered.connect(parent.toggle_toolbar_visibility)
    view_menu.addAction(show_toolbar_action)
    parent._action_show_toolbar = show_toolbar_action

    view_menu.addSeparator()

    fullscreen_action = QAction("&Full Screen", parent)
    fullscreen_action.setShortcut(QKeySequence("F11"))
    fullscreen_action.setCheckable(True)
    fullscreen_action.triggered.connect(parent.toggle_fullscreen)
    view_menu.addAction(fullscreen_action)

    view_menu.addSeparator()

    zoom_in_action = QAction("Zoom &In", parent)
    zoom_in_action.setShortcut(QKeySequence("Ctrl+Plus"))
    zoom_in_action.triggered.connect(parent.zoom_in)
    view_menu.addAction(zoom_in_action)

    zoom_out_action = QAction("Zoom &Out", parent)
    zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
    zoom_out_action.triggered.connect(parent.zoom_out)
    view_menu.addAction(zoom_out_action)

    zoom_reset_action = QAction("Zoom &Reset", parent)
    zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
    zoom_reset_action.triggered.connect(parent.zoom_reset)
    view_menu.addAction(zoom_reset_action)

    terminal_menu = menubar.addMenu("&Terminal")

    set_title_action = QAction("Set &Title...", parent)
    set_title_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
    set_title_action.triggered.connect(parent.set_title_dialog)
    terminal_menu.addAction(set_title_action)

    terminal_menu.addSeparator()

    encoding_menu = terminal_menu.addMenu("Set &Encoding")
    enc_group = QAction("enc_group", parent)
    enc_group.setVisible(False)
    for label in ENCODINGS:
        enc_name = label.split(" ")[0]
        enc_action = QAction(label, parent)
        enc_action.setCheckable(True)
        enc_action.triggered.connect(
            lambda checked, e=enc_name: parent.set_encoding(e)
        )
        encoding_menu.addAction(enc_action)
    parent._encoding_actions = encoding_menu.actions()

    terminal_menu.addSeparator()

    signal_menu = terminal_menu.addMenu("Send &Signal")
    for label, sig in SIGNALS:
        sig_action = QAction(label, parent)
        sig_action.triggered.connect(
            lambda checked, s=sig: parent.send_signal(s)
        )
        signal_menu.addAction(sig_action)

    terminal_menu.addSeparator()

    reset_action = QAction("&Reset", parent)
    reset_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
    reset_action.triggered.connect(parent.reset_terminal)
    terminal_menu.addAction(reset_action)

    reset_clear_action = QAction("Reset and &Clear", parent)
    reset_clear_action.setShortcut(QKeySequence("Ctrl+Shift+X"))
    reset_clear_action.triggered.connect(parent.reset_and_clear)
    terminal_menu.addAction(reset_clear_action)

    terminal_menu.addSeparator()

    read_only_action = QAction("&Read-Only", parent)
    read_only_action.setCheckable(True)
    read_only_action.triggered.connect(parent.toggle_read_only)
    terminal_menu.addAction(read_only_action)
    parent._action_read_only = read_only_action

    terminal_menu.addSeparator()

    prev_tab_action = QAction("Previous Tab", parent)
    prev_tab_action.setShortcut(QKeySequence("Ctrl+Page Up"))
    prev_tab_action.triggered.connect(parent.prev_tab)
    terminal_menu.addAction(prev_tab_action)

    next_tab_action = QAction("Next Tab", parent)
    next_tab_action.setShortcut(QKeySequence("Ctrl+Page Down"))
    next_tab_action.triggered.connect(parent.next_tab)
    terminal_menu.addAction(next_tab_action)

    move_tab_left_action = QAction("Move Tab &Left", parent)
    move_tab_left_action.setShortcut(QKeySequence("Ctrl+Shift+Page Up"))
    move_tab_left_action.triggered.connect(parent.move_tab_left)
    terminal_menu.addAction(move_tab_left_action)

    move_tab_right_action = QAction("Move Tab &Right", parent)
    move_tab_right_action.setShortcut(QKeySequence("Ctrl+Shift+Page Down"))
    move_tab_right_action.triggered.connect(parent.move_tab_right)
    terminal_menu.addAction(move_tab_right_action)

    detach_tab_action = QAction("&Detach Tab", parent)
    detach_tab_action.triggered.connect(parent.detach_tab)
    terminal_menu.addAction(detach_tab_action)

    tabs_menu = menubar.addMenu("&Tabs")
    parent._tabs_menu = tabs_menu
    parent._update_tabs_menu()

    help_menu = menubar.addMenu("&Help")

    about_action = QAction("&About", parent)
    about_action.triggered.connect(parent.show_about)
    help_menu.addAction(about_action)

    return menubar
