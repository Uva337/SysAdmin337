# sysadmin_actions.py
"""
Слой бизнес-логики. Отвечает за выполнение команд.

Этот модуль принимает интент и параметры, рендерит финальную команду
из шаблона и запускает ее в отдельном процессе.
"""
import subprocess
import shlex
import platform
from typing import Dict, Any

# ИСПРАВЛЕНИЕ: Импортируем psutil для надежного сбора данных
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Импортируем класс напрямую, так как он теперь в корне
from command_templates import CommandTemplates


# --- Специальные обработчики для надежности ---

def _get_disk_usage():
    """Возвращает информацию об использовании диска с помощью psutil."""
    if not PSUTIL_AVAILABLE:
        return "ERROR: Библиотека psutil не найдена. Пожалуйста, установите ее: pip install psutil"

    partitions = psutil.disk_partitions()
    header = f"{'Device':<15} {'Total (GB)':>12} {'Used (GB)':>12} {'Free (GB)':>12} {'Use%':>8}  {'Mountpoint'}\n"
    separator = "-" * len(header) + "\n"
    output = header + separator

    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            total = f"{usage.total / (1024 ** 3):.2f}"
            used = f"{usage.used / (1024 ** 3):.2f}"
            free = f"{usage.free / (1024 ** 3):.2f}"
            percent = f"{usage.percent}%"
            output += f"{p.device:<15} {total:>12} {used:>12} {free:>12} {percent:>8}  {p.mountpoint}\n"
        except Exception:
            # Пропускаем ошибки для съемных носителей, которые могут быть недоступны
            continue
    return output


def _list_processes():
    """Возвращает список процессов с помощью psutil."""
    if not PSUTIL_AVAILABLE:
        return "ERROR: Библиотека psutil не найдена."

    header = f"{'PID':<8} {'Name':<25} {'Username':<20} {'CPU%':<8} {'Memory%':<10}\n"
    separator = "-" * (len(header) + 5) + "\n"
    output = header + separator

    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
        try:
            pid = proc.info['pid']
            name = proc.info['name'] or 'N/A'
            user = proc.info['username'] or 'N/A'
            cpu = f"{proc.info['cpu_percent']:.1f}"
            mem = f"{proc.info['memory_percent']:.1f}"
            output += f"{pid:<8} {name[:24]:<25} {user[:19]:<20} {cpu:<8} {mem:<10}\n"
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return output


def _get_system_load():
    """Возвращает информацию о загрузке CPU и RAM с помощью psutil."""
    if not PSUTIL_AVAILABLE:
        return "ERROR: Библиотека psutil не найдена."

    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()

    mem_total_gb = f"{mem.total / (1024 ** 3):.2f} GB"
    mem_used_gb = f"{mem.used / (1024 ** 3):.2f} GB"
    mem_percent = f"{mem.percent}%"

    output = "--- System Load ---\n"
    output += f"CPU Usage: {cpu_percent}%\n"
    output += f"Memory Usage: {mem_percent} ({mem_used_gb} / {mem_total_gb})\n"

    return output


def _list_disks():
    """Возвращает список дисков и разделов с помощью psutil."""
    if not PSUTIL_AVAILABLE:
        return "ERROR: Библиотека psutil не найдена."

    header = f"{'Device':<20} {'Mountpoint':<25} {'FSType':<10} {'Opts'}\n"
    separator = "-" * 80 + "\n"
    output = header + separator

    for p in psutil.disk_partitions():
        output += f"{p.device:<20} {p.mountpoint:<25} {p.fstype:<10} {p.opts}\n"

    return output


# Словарь для специальных, надежных обработчиков
SPECIAL_HANDLERS = {
    "disk.usage": _get_disk_usage,
    "process.list": _list_processes,
    "system.get_load": _get_system_load,
    "disk.list": _list_disks,
    # Сюда можно добавлять другие интенты, требующие особой обработки
}


# --- Основная функция выполнения ---

def execute_intent(intent: str, params: Dict[str, Any], command_templates: CommandTemplates,
                   on_output: callable) -> None:
    """
    Основная функция для выполнения действия по интенту.
    Сначала проверяет наличие специального обработчика, затем использует шаблоны.
    """
    try:
        # Шаг 1: Проверка на наличие специального обработчика
        if intent in SPECIAL_HANDLERS:
            handler = SPECIAL_HANDLERS[intent]
            result = handler()
            on_output(result)
            return

        # Шаг 2: Если специального обработчика нет, используем стандартный путь через шаблоны
        os_type = "win" if platform.system().lower() == "windows" else "astro"
        final_command = command_templates.render_command(intent, os_type, params)
        on_output(f"$ {final_command}\n")

        is_shell_needed = os_type == 'win'
        encoding = 'cp866' if os_type == 'win' else 'utf-8'

        process = subprocess.Popen(
            final_command if is_shell_needed else shlex.split(final_command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=encoding,
            errors='replace',
            shell=is_shell_needed,
            creationflags=subprocess.CREATE_NO_WINDOW if os_type == 'win' else 0
        )

        # Потоковая передача вывода
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                on_output(output)

        stderr_output = process.stderr.read()
        if stderr_output:
            on_output(f"\nERROR:\n{stderr_output}")

    except (KeyError, ValueError) as e:
        error_message = f"ERROR: Ошибка подготовки команды '{intent}': {e}\n"
        on_output(error_message)
        print(error_message)
    except FileNotFoundError as e:
        error_message = f"ERROR: Команда не найдена: {e}. Установлена ли программа и есть ли она в системной переменной PATH?\n"
        on_output(error_message)
        print(error_message)
    except Exception as e:
        error_message = f"ERROR: Произошла непредвиденная ошибка во время выполнения: {e}\n"
        on_output(error_message)
        print(error_message)

