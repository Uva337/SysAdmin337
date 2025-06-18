# app_new_ui.py
"""
Главный файл приложения SysAdmin Assistant с графическим интерфейсом на PyQt5.
Версия с улучшенным UI/UX.
"""
import sys
import os
import re
from functools import partial

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QLabel, QSplitter, QTreeWidget,
    QTreeWidgetItem, QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
    QInputDialog, QComboBox
)
from PyQt5.QtCore import (
    Qt, QThread, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve,
    pyqtProperty
)
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCursor, QTextCharFormat

# --- Импорт компонентов ---
from auth_rbac import AuthManager, Role
from command_templates import CommandTemplates, ParamSpec
from logging_audit import AuditLogger
from utils import AdvancedNLUParser
from sysadmin_actions import execute_intent
import icon
from spinner import SpinnerWidget # Импорт нашего спиннера

# --- Константы ---
COMMANDS_FILE = "commands.json"
DISCORD_STYLESHEET = """
    QMainWindow, QDialog { background-color: #36393f; }
    QWidget { color: #dcddde; font-family: "Segoe UI", "Cantarell", sans-serif; font-size: 10pt; }
    QTreeWidget {
        background-color: #2f3136; border: none; font-size: 11pt; outline: 0;
    }
    QTreeWidget::item { padding: 8px 10px; border-radius: 4px; }
    QTreeWidget::item:hover { background-color: #3a3c43; }
    QTreeWidget::item:selected { background-color: #40444b; color: #ffffff; }
    QTreeWidget::branch {
        /* Оставляем пустым, чтобы использовались системные стрелки */
    }
    QLineEdit, QComboBox {
        background-color: #202225; border: 1px solid #202225;
        border-radius: 4px; padding: 8px; color: #dcddde;
    }
    QLineEdit:focus, QComboBox:focus { border-color: #7289da; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView {
        background-color: #2f3136; border: 1px solid #40444b;
        selection-background-color: #40444b; outline: 0;
    }
    QTextEdit {
        background-color: #202225; border: 1px solid #40444b;
        border-radius: 4px; color: #dcddde;
        font-family: "Consolas", "Courier New", monospace;
    }
    QSplitter::handle { background-color: #202225; }
    QSplitter::handle:hover { background-color: #7289da; }
    QScrollBar:vertical { background: #2f3136; width: 10px; margin: 0; }
    QScrollBar::handle:vertical { background: #202225; min-height: 20px; border-radius: 5px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
    QLabel { padding-top: 4px; }
    QMessageBox { background-color: #36393f; }
    QDialogButtonBox QPushButton {
        background-color: #5865f2;
        color: #ffffff;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: 500;
        min-width: 60px;
    }
    QDialogButtonBox QPushButton:hover {
        background-color: #4752c4;
    }
    QDialogButtonBox QPushButton:pressed {
        background-color: #3b45a0;
    }
"""

CATEGORY_TRANSLATIONS = {
    "Network": "Сеть", "System": "Система", "Process": "Процессы",
    "Disk": "Диски", "Software": "Программы", "Users": "Пользователи",
    "Services": "Службы", "Logs": "Логи и Журналы", "Fs": "Файловая система",
    "Power": "Питание",
}

INTENT_ICONS = {
    'network.get_ip_config': 'network-wired', 'network.change_ip_static': 'preferences-system-network',
    'network.set_ip_dhcp': 'network-wired', 'network.show_dns_cache': 'help-faq',
    'network.clear_dns_cache': 'edit-clear', 'network.set_dns': 'document-edit',
    'network.ping': 'network-transmit-receive', 'network.traceroute': 'go-next-skip',
    'network.show_connections': 'network-server', 'network.firewall_status': 'security-high',
    'network.toggle_firewall': 'security-medium', 'network.allow_port': 'list-add',
    'network.deny_port': 'list-remove', 'network.show_routing_table': 'view-list-tree',
    'network.add_route': 'go-jump', 'network.del_route': 'edit-delete',
    'network.check_port': 'system-search', 'network.get_external_ip': 'weather-clear-night',
    'system.info': 'dialog-information', 'system.uptime': 'appointment-new',
    'system.logged_in_users': 'system-users', 'system.get_load': 'utilities-system-monitor',
    'system.env_vars': 'text-x-generic', 'system.get_datetime': 'office-calendar',
    'system.set_datetime': 'document-edit-date', 'system.set_hostname': 'computer',
    'process.list': 'view-process-tree', 'process.kill': 'process-stop',
    'process.find_by_port': 'edit-find', 'disk.usage': 'drive-harddisk',
    'disk.list': 'drive-multidisk', 'disk.smart_status': 'drive-harddisk-warning',
    'software.install': 'system-software-install', 'software.uninstall': 'system-software-uninstall',
    'software.update_list': 'system-software-update', 'software.upgrade_all': 'go-up',
    'software.list': 'view-list-details', 'software.find': 'edit-find-replace',
    'users.add': 'user-identity', 'users.delete': 'user-trash',
    'users.change_password': 'dialog-password', 'users.add_to_group': 'list-add-user',
    'users.remove_from_group': 'list-remove-user', 'users.list': 'system-users',
    'users.list_groups': 'preferences-desktop-sharing', 'services.start': 'media-playback-start',
    'services.stop': 'media-playback-stop', 'services.restart': 'view-refresh',
    'services.status': 'dialog-question', 'services.list': 'preferences-system-windows-services',
    'logs.show_system': 'text-x-log', 'logs.search': 'system-search',
    'fs.find_files': 'edit-find', 'fs.view_file': 'document-open', 'fs.checksum': 'document-properties',
    'power.reboot': 'system-reboot', 'power.shutdown': 'system-shutdown'
}

class Worker(QObject):
    finished = pyqtSignal()
    output = pyqtSignal(str)
    def __init__(self, intent, params, command_templates):
        super().__init__()
        self.intent, self.params, self.command_templates = intent, params, command_templates
    def run(self):
        execute_intent(self.intent, self.params, self.command_templates, self.output.emit)
        self.finished.emit()

class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._color, self.hover_color, self.default_color, self.disabled_color = QColor("#5865f2"), QColor("#4752c4"), QColor("#5865f2"), QColor("#4f545c")
        self.animation = QPropertyAnimation(self, b"buttonColor", self)
        self.animation.setDuration(200); self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.buttonColor = self.default_color
    def enterEvent(self, event):
        if self.isEnabled(): self.animation.setEndValue(self.hover_color); self.animation.start()
        super().enterEvent(event)
    def leaveEvent(self, event):
        if self.isEnabled(): self.animation.setEndValue(self.default_color); self.animation.start()
        super().leaveEvent(event)
    def setEnabled(self, enabled):
        super().setEnabled(enabled); self.animation.stop()
        self.buttonColor = self.default_color if enabled else self.disabled_color
    @pyqtProperty(QColor)
    def buttonColor(self): return self._color
    @buttonColor.setter
    def buttonColor(self, color):
        self._color = color
        self.setStyleSheet(f"background-color: {color.name()}; color: #ffffff; border: none; padding: 8px 16px; border-radius: 4px; font-weight: 500;")

class LoginDialog(QDialog):
    def __init__(self, auth_manager: AuthManager, parent=None):
        super().__init__(parent)
        self.auth_manager, self.user_role, self.username = auth_manager, None, ""
        self.setWindowTitle("Вход в SysAdmin Assistant"); self.setMinimumWidth(350)
        layout, form_layout = QVBoxLayout(self), QFormLayout()
        self.username_input, self.password_input = QLineEdit(self), QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.username_input.setPlaceholderText("Имя пользователя")
        self.password_input.setPlaceholderText("Пароль")
        form_layout.addRow("Пользователь:", self.username_input)
        form_layout.addRow("Пароль:", self.password_input)
        layout.addLayout(form_layout)
        self.status_label = QLabel(""); self.status_label.setStyleSheet("color: #f04747;")
        layout.addWidget(self.status_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.handle_login); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.password_input.returnPressed.connect(self.handle_login)
    def handle_login(self):
        self.username, password = self.username_input.text().strip(), self.password_input.text()
        if not self.username or not password:
            self.status_label.setText("Имя пользователя и пароль не могут быть пустыми."); return
        role = self.auth_manager.verify_user(self.username, password)
        if role:
            self.user_role = role
            self.accept()
        else:
            self.status_label.setText("Неверное имя пользователя или пароль.")

class MainWindow(QMainWindow):
    def __init__(self, username: str, user_role: Role, auth_manager: AuthManager):
        super().__init__()
        self.username, self.user_role, self.auth_manager = username, user_role, auth_manager
        self.command_templates = CommandTemplates()
        try: self.command_templates.load_from_json(COMMANDS_FILE)
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Не удалось загрузить '{COMMANDS_FILE}':\n{e}"); sys.exit(1)
        self.nlu_parser, self.logger = AdvancedNLUParser(self.command_templates), AuditLogger()
        self.current_intent, self.param_widgets = None, {}
        self.thread, self.worker = None, None
        self.init_ui()
    def init_ui(self):
        self.setWindowTitle("SysAdmin Assistant"); self.setGeometry(100, 100, 1200, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        self.function_tree = QTreeWidget(); self.function_tree.setHeaderHidden(True)
        splitter.addWidget(self.function_tree)
        self.populate_function_tree()
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 10, 20, 10); right_layout.setSpacing(15)
        nlu_area_layout = QHBoxLayout()
        self.nlu_input = QLineEdit(); self.nlu_input.setPlaceholderText("Введите команду...")
        self.nlu_execute_button = AnimatedButton("Выполнить")
        self.nlu_execute_button.setIcon(QIcon.fromTheme("system-run"))
        self.spinner = SpinnerWidget(); self.spinner.hide()
        nlu_area_layout.addWidget(self.nlu_input); nlu_area_layout.addWidget(self.spinner)
        nlu_area_layout.addWidget(self.nlu_execute_button)
        right_layout.addLayout(nlu_area_layout)
        self.param_form_layout = QFormLayout()
        self.param_form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        right_layout.addLayout(self.param_form_layout)
        self.form_execute_button = AnimatedButton("Выполнить команду")
        self.form_execute_button.setIcon(QIcon.fromTheme("media-playback-start"))
        right_layout.addWidget(self.form_execute_button); self.form_execute_button.hide()
        right_layout.addStretch(1)
        self.output_console = QTextEdit(); self.output_console.setReadOnly(True)
        right_layout.addWidget(self.output_console, 2)
        splitter.addWidget(right_panel); splitter.setSizes([280, 920]); splitter.setHandleWidth(1)
        self.function_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.nlu_execute_button.clicked.connect(self.execute_from_nlu)
        self.nlu_input.returnPressed.connect(self.execute_from_nlu)
        self.form_execute_button.clicked.connect(self.execute_from_form)
    def populate_function_tree(self):
        self.function_tree.clear(); categories = {}
        for intent, template in self.command_templates.intents.items():
            category_key = intent.split('.')[0].capitalize()
            if category_key not in categories: categories[category_key] = []
            categories[category_key].append(template)
        for category_key, templates in sorted(categories.items()):
            category_name = CATEGORY_TRANSLATIONS.get(category_key, category_key)
            category_item = QTreeWidgetItem(self.function_tree, [category_name])
            category_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
            for template in sorted(templates, key=lambda t: t.description):
                child_item = QTreeWidgetItem(category_item, [template.description])
                icon_name = INTENT_ICONS.get(template.intent, 'application-x-executable')
                child_item.setIcon(0, QIcon.fromTheme(icon_name))
                child_item.setData(0, Qt.UserRole, template.intent)
                child_item.setToolTip(0, f"Интент: {template.intent}")
    def clear_param_form(self):
        for i in reversed(range(self.param_form_layout.count())):
            layout_item = self.param_form_layout.takeAt(i)
            if layout_item and layout_item.widget(): layout_item.widget().deleteLater()
        self.param_widgets.clear(); self.form_execute_button.hide()
    def on_tree_item_clicked(self, item, column):
        intent = item.data(0, Qt.UserRole)
        if not intent: self.clear_param_form(); self.current_intent = None; return
        template = self.command_templates.get_intent_template(intent)
        if not template: return
        if not template.params:
            self.clear_param_form(); self.current_intent = None
            self.run_execution(intent, {})
        else: self.current_intent = intent; self.create_param_form(intent)
    def create_param_form(self, intent: str):
        self.clear_param_form(); template = self.command_templates.get_intent_template(intent)
        if not template or not template.params: return
        for name, spec in template.params.items():
            label_text, widget = f"{name.capitalize()}{' *' if spec.required else ''}:", None
            label = QLabel(label_text)
            if spec.type == "choice" and spec.choices: widget = QComboBox(); widget.addItems(spec.choices)
            elif spec.type == "password": widget = QLineEdit(); widget.setEchoMode(QLineEdit.Password)
            else: widget = QLineEdit()
            if widget:
                tooltip = f"Параметр: {name}\nТип: {spec.type}" + (f"\nПример: {spec.example}" if spec.example else "")
                widget.setToolTip(tooltip)
                if spec.example: widget.setPlaceholderText(spec.example)
                self.param_form_layout.addRow(label, widget); self.param_widgets[name] = widget
        self.form_execute_button.show()
    def execute_from_form(self):
        if not self.current_intent: return
        params, template = {}, self.command_templates.get_intent_template(self.current_intent)
        for name, widget in self.param_widgets.items():
            value = widget.text().strip() if isinstance(widget, QLineEdit) else widget.currentText()
            if value: params[name] = value
            elif template.params[name].required:
                QMessageBox.warning(self, "Ошибка ввода", f"Параметр '{name}' является обязательным."); return
        self.run_execution(self.current_intent, params)
    def execute_from_nlu(self):
        text = self.nlu_input.text().strip()
        if not text: return
        parsed_data = self.nlu_parser.parse(text)
        intent, params = parsed_data.get("intent"), parsed_data.get("params", {})
        if not intent:
            self.log_to_console("Команда не распознана.\n", "error"); return
        template = self.command_templates.get_intent_template(intent)
        if template:
            for p_name, p_spec in template.params.items():
                if p_spec.required and p_name not in params:
                    value, ok = QInputDialog.getText(self, "Требуется параметр", f"Введите '{p_name}':")
                    if ok and value: params[p_name] = value
                    else: self.log_to_console(f"Отмена. Нет параметра '{p_name}'.\n", "error"); return
        self.run_execution(intent, params)
    def run_execution(self, intent: str, params: dict):
        if self.thread and self.thread.isRunning():
            self.log_to_console("! Предыдущая команда еще выполняется...\n", "warning"); return
        self.output_console.clear()
        self.log_to_console(f"----- Запуск: {intent} -----\n", "header")
        masked_params = {k: '******' if 'password' in k.lower() else v for k, v in params.items()}
        self.log_to_console(f"> Параметры: {masked_params}\n", "info")
        self.logger.info(self.username, intent, params, "Execution started.")
        self.toggle_ui_for_execution(True)
        self.thread, self.worker = QThread(), Worker(intent, params, self.command_templates)
        self.worker.moveToThread(self.thread)
        self.worker.output.connect(self.handle_worker_output)
        self.worker.finished.connect(self.on_execution_finished)
        self.thread.started.connect(self.worker.run)
        self.thread.start()
    def on_execution_finished(self):
        self.log_to_console("\n----- Выполнение завершено -----\n", "success")
        self.toggle_ui_for_execution(False)
        if self.thread:
            self.thread.quit(); self.thread.wait()
            self.thread.deleteLater(); self.worker.deleteLater()
            self.thread, self.worker = None, None
    def toggle_ui_for_execution(self, is_running: bool):
        self.nlu_execute_button.setEnabled(not is_running); self.form_execute_button.setEnabled(not is_running)
        self.function_tree.setEnabled(not is_running)
        if is_running: self.spinner.start()
        else: self.spinner.stop()
    def handle_worker_output(self, text: str):
        if text.strip().startswith("ERROR:"): self.log_to_console(text, "error")
        else: self.log_to_console(text, "stdout")
    def log_to_console(self, text: str, msg_type: str = "stdout"):
        cursor = self.output_console.textCursor(); cursor.movePosition(QTextCursor.End)
        char_format = QTextCharFormat()
        color = {"stdout": QColor("#dcddde"), "header": QColor("#7289da"), "error": QColor("#f04747"),
                 "warning": QColor("#faa61a"), "success": QColor("#43b581"), "info": QColor("#8e9297")
                }.get(msg_type, QColor("#dcddde"))
        char_format.setForeground(color)
        if msg_type in ["header", "error"]: char_format.setFontWeight(QFont.Bold)
        else: char_format.setFontWeight(QFont.Normal)
        cursor.insertText(text, char_format)
        self.output_console.verticalScrollBar().setValue(self.output_console.verticalScrollBar().maximum())
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.quit(); self.thread.wait()
        self.logger.close(); self.auth_manager.close(); super().closeEvent(event)

def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyleSheet(DISCORD_STYLESHEET)
    icon_path = icon.create_app_icon_if_not_exists()
    if icon_path and os.path.exists(icon_path): app.setWindowIcon(QIcon(icon_path))
    if os.name == 'nt':
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                 QMessageBox.warning(None, "Требуются права администратора", "Для корректной работы некоторых команд рекомендуется перезапустить приложение от имени администратора.")
        except Exception as e: print(f"Could not check for admin rights: {e}")
    try:
        auth_manager = AuthManager()
    except Exception as e:
        QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось инициализировать AuthManager: {e}"); return
    login_dialog = LoginDialog(auth_manager)
    if login_dialog.exec_() == QDialog.Accepted:
        main_window = MainWindow(username=login_dialog.username, user_role=login_dialog.user_role, auth_manager=auth_manager)
        main_window.show()
        sys.exit(app.exec_())
    else:
        auth_manager.close(); sys.exit(0)

if __name__ == "__main__":
    main()
