import os
import time
from datetime import datetime
from hashlib import md5
import win32print
import win32con
import win32ui
from PIL import Image, ImageDraw, ImageFont, ImageWin


class ImageCard:
    """Класс для создания и редактирования открыток"""
    def __init__(self, image_path: str):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Изображение не найдено: {image_path}")
        self.image_path = image_path
        self.image = Image.open(image_path).convert("RGBA")
        self.draw = ImageDraw.Draw(self.image)
        self.font_path = "./fonts/arialmt.ttf"
        self.font_size = 40

    def get_font(self):
        try:
            return ImageFont.truetype(self.font_path, self.font_size) if os.path.exists(self.font_path) else ImageFont.load_default(self.font_size)
        except Exception:
            return ImageFont.load_default(self.font_size)

    def add_text(self, text: str, position: tuple = None, color: str = "white", font_size: int = 40):
        self.font_size = font_size
        if position is None:
            bbox = self.draw.textbbox((0, 0), text, font=self.get_font())
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            width, height = self.image.size
            position = ((width - text_width) // 2, (height - text_height) // 2)
        self.draw.text(position, text, font=self.get_font(), fill=color)

    def save(self, temp_dir: str = "./temp"):
        os.makedirs(temp_dir, exist_ok=True)
        filename = f"temp_{md5(datetime.now().isoformat().encode()).hexdigest()}.png"
        output_path = os.path.join(temp_dir, filename)
        self.image.save(output_path, "PNG")
        print(f"Сохранено: {output_path}")
        return output_path


class Printer:
    """Класс для печати открыток"""

    def __init__(self, printer_name=None):
        self.printer_name = printer_name or win32print.GetDefaultPrinter()
        self.printdefaults = {"DesiredAccess": win32print.PRINTER_ALL_ACCESS}

    def print(self, card: ImageCard):
        # 1. Сохраняем изображение
        try:
            filename = card.save()
            print(f"Файл для печати: {filename}")
        except Exception as e:
            print(f"Ошибка сохранения изображения: {e}")
            return

        # 2. Проверяем, доступен ли принтер
        try:
            printer_handle = win32print.OpenPrinter(self.printer_name, self.printdefaults)
            print(f"Принтер '{self.printer_name}' найден и доступен.")
            win32print.ClosePrinter(printer_handle)
        except Exception as e:
            print(f"Принтер недоступен: {e}")
            return

        # 3. Создаём DC и пытаемся начать печать
        try:
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(self.printer_name)

            # Получаем размеры страницы
            printer_width = hDC.GetDeviceCaps(win32con.PHYSICALWIDTH)
            printer_height = hDC.GetDeviceCaps(win32con.PHYSICALHEIGHT)

            # Открываем изображение
            bmp = Image.open(filename)

            # Поворачиваем при необходимости
            if bmp.size[0] > bmp.size[1] and printer_width < printer_height:
                bmp = bmp.rotate(90, expand=True)

            # Масштабирование
            width_ratio = printer_width / bmp.size[0]
            height_ratio = printer_height / bmp.size[1]
            scale_ratio = min(width_ratio, height_ratio)
            scaled_width = int(bmp.size[0] * scale_ratio)
            scaled_height = int(bmp.size[1] * scale_ratio)

            # Начинаем документ
            hDC.StartDoc(filename)  # ← вот здесь ошибка может возникнуть!
            hDC.StartPage()

            dib = ImageWin.Dib(bmp)
            dib.draw(hDC.GetHandleOutput(), (0, 0, scaled_width, scaled_height))

            hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()

            print("Документ отправлен на печать.")

            # Опционально: удаляем временный файл
            time.sleep(0.5)
            os.remove(filename)

        except win32ui.error as e:
            print(f"Ошибка win32ui: {e}")
            print("Возможные причины:")
            print("  - Принтер выключен или не готов")
            print("  - Проблемы с драйвером")
            print("  - Принтер приостановлен в системе")
            print("  - Недостаточно прав")
        except Exception as e:
            print(f"Неизвестная ошибка печати: {e}")


# === Пример использования ===
if __name__ == "__main__":
    input_image = "./images/открытка 1.png"
    try:
        card = ImageCard(input_image)
        card.add_text("С Рождеством!", position=(100, 500), color="red", font_size=100)
        card.add_text("Счастья и мира!", position=(100, 600), color="yellow", font_size=40)
        printer = Printer()
        printer.print(card)
    except Exception as e:
        print(f"Ошибка: {e}")