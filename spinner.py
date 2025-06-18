# spinner.py
"""
Модуль для анимированного виджета загрузки (спиннера).
Версия, совместимая с PyQt5 и с исправленными данными.
"""
import base64
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import QSize, QByteArray, QBuffer, QIODevice

# ИСПРАВЛЕНО: Новая, корректная base64-строка для GIF-анимации
SPINNER_B64 = b'R0lGODlhEAAQAPIAAP///wAAAMLCwkJCQgAAAGJiYoKCgpKSkiH+GkNyZWF0ZWQgd2l0aCBhamF4bG9hZC5pbmZvACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADMwi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyMAThGnEcCxNo2ASiOkFABRBlAEACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADNAi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyGANkFRBVRgwV8MSGkUh1IYYkMLvYYACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADNAi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyGANkFRBVRgwV8MSGkUh1IYYkMLvYYACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADNAi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyGANkFRBVRgwV8MSGkUh1IYYkMLvYYACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADNAi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyGANkFRBVRgwV8MSGkUh1IYYkMLvYYACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADNAi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyGANkFRBVRgwV8MSGkUh1IYYkMLvYYACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADNAi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyGANkFRBVRgwV8MSGkUh1IYYkMLvYYACH5BAAKAAAAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAEAAQAAADNAi63P4wyklrE2MIOggZnAdOmEVJorpW0zVHyGANkFRBVRgwV8MSGkUh1IYYkMLvYYADs='


class SpinnerWidget(QWidget):
    """Виджет, отображающий анимированный GIF загрузки."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spinner_label = QLabel(self)

        spinner_data = QByteArray(base64.b64decode(SPINNER_B64))
        buffer = QBuffer(spinner_data, self)
        buffer.open(QIODevice.ReadOnly)

        self.movie = QMovie(self)
        self.movie.setDevice(buffer)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)

        self.spinner_label.setMovie(self.movie)
        layout.addWidget(self.spinner_label)
        self.setFixedSize(16, 16)  # Уменьшил размер под новую иконку

    def start(self):
        """Запускает анимацию."""
        self.movie.start()
        self.show()

    def stop(self):
        """Останавливает анимацию."""
        self.movie.stop()
        self.hide()
