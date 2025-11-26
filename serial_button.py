import serial
import pygame
import threading

# Кастомное событие pygame
BUTTON_PRESSED_EVENT = pygame.USEREVENT + 1


class SerialButton:
    """
    Управляет COM-портом и посылает pygame event при получении "BUTTON_PRESSED".
    Работает в отдельном потоке, чтобы не блокировать основной цикл.
    """

    def __init__(self, port="COM3", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.thread = None

    def open(self):
        """Открыть COM-порт и запустить поток чтения"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"✓ Serial opened: {self.port}@{self.baudrate}")
            return True
        except Exception as e:
            print(f"✗ Не удалось открыть serial {self.port}: {e}")
            self.ser = None
            return False

    def _read_loop(self):
        """Поток: читаем данные и посылаем события"""
        while self.running and self.ser:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line == "BUTTON_PRESSED":
                    # Посылаем кастомное событие в очередь pygame
                    event = pygame.event.Event(BUTTON_PRESSED_EVENT)
                    pygame.event.post(event)
                    print("→ BUTTON_PRESSED event posted")
            except Exception as e:
                if self.running:
                    print(f"✗ Ошибка чтения serial: {e}")
                break

    def close(self):
        """Закрыть порт и остановить поток"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.ser:
            try:
                self.ser.close()
                print("✓ Serial closed")
            except:
                pass
        self.ser = None