import pygame
import cv2
import random
import os
import threading

from postcard_print.main import Printer, ImageCard
from serial_button import SerialButton, BUTTON_PRESSED_EVENT


# ==========================
# Настройки
# ==========================

# Окно
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 800
FULLSCREEN = False

# Звук
MUSIC_BG_PATH = "./sounds/SBER_CAT_LoFi_1.5_no sfx.wav"
MUSIC_BG_VOLUME = 0.4 # изменяется от 0 до 1
DOORBELL_SOUND_PATH = "./sounds/doorbell.wav"
DOORBELL_SOUND_VOLUME = 0.9 # изменяется от 0 до 1

# Видео
VIDEO_WRITE_PATH = "./videos/Видео 1_СберКот_подпись открыток.mp4"
VIDEO_SEND_PATH  = "./videos/Видео 2_СберКот_отправка открыток.mp4"

# Кнопка (звонок) на Arduino
ARDUINO_BUTTON_PORT = "COM3"  # <- поменяйте порт если нужно

# Печать
IMAGE_DIR = './images'

# Настройка: задержка перед печатью (в секундах) после старта видео "sending"
PRINT_DELAY_SECONDS = 3.0  # измените значение по необходимости



# ==========================
# Инициализация Pygame
# ==========================

pygame.init()

if FULLSCREEN:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

pygame.mixer.music.load(MUSIC_BG_PATH)
pygame.mixer.music.set_volume(MUSIC_BG_VOLUME)
doorbell_sound = pygame.mixer.Sound(DOORBELL_SOUND_PATH)
doorbell_sound.set_volume(DOORBELL_SOUND_VOLUME)

# ==========================
# Инициализация принтера и COM-кнопки
# ==========================

printer = Printer()
button = SerialButton(port=ARDUINO_BUTTON_PORT, baudrate=9600)  # <- поменяйте порт если нужно
button.open()  # открываем порт при старте

# ==========================
# Загрузка видео
# ==========================

video_write = cv2.VideoCapture(VIDEO_WRITE_PATH)
video_send  = cv2.VideoCapture(VIDEO_SEND_PATH)

# ==========================
# Загрузка писем
# ==========================
with open("texts/letters.txt", encoding="utf-8") as f:
    letters = [line.strip() for line in f if line.strip() != "==="]

IMAGES_PATHS = [os.path.join(IMAGE_DIR, img_name)  for img_name in os.listdir(IMAGE_DIR)]

# ==========================
# Состояния
# ==========================
STATE_WRITING   = "writing"   # проигрывается первое видео
STATE_WAIT_SEND = "wait_send" # ждём окончания первого видео
STATE_SENDING   = "sending"   # проигрывается второе видео

# runtime-переменные состояний
state = STATE_WRITING
current_video = video_write

letter_to_print = None
# время старта видео отправки в миллисекундах (pygame.time.get_ticks())
send_start_time = None
# флаг: уже отправляли печать во время текущего прогона видео отправки
printed_during_send = False


# ==========================
# Функции
# ==========================
def play_video_frame(video):
    ret, frame = video.read()
    if not ret:
        video.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = video.read()

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
    frame = pygame.transform.scale(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(frame, (0, 0))


def video_finished(video):
    return int(video.get(cv2.CAP_PROP_POS_FRAMES)) >= int(video.get(cv2.CAP_PROP_FRAME_COUNT)) - 1


def get_random_card():
    card = ImageCard(random.choice(IMAGES_PATHS))
    return card

def print_job(printer: Printer, card: ImageCard):
    try:
        printer.print(card)
    except Exception as e:
        print(f"Ошибка печати открытки: {e}")


def start_print_deamon(printer: Printer, card: ImageCard):
    thread = threading.Thread(target=print_job, args=(printer, card), daemon=True)
    thread.start()


# ==========================
# Главный цикл
# ==========================

pygame.mixer.music.play(-1)  # зацикленная фоновая музыка
running = True
try:
    while running:

        # События
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # ЛКМ → запрос отправки
                if state == STATE_WRITING:
                    doorbell_sound.play()
                    state = STATE_WAIT_SEND

            elif event.type == BUTTON_PRESSED_EVENT:
                # COM-кнопка → запрос отправки
                if state == STATE_WRITING:
                    doorbell_sound.play()
                    state = STATE_WAIT_SEND
                    print("→ COM-button triggered state change")

        # --------------------------
        # Логика состояний
        # --------------------------

        if state == STATE_WRITING:
            play_video_frame(video_write)

        elif state == STATE_WAIT_SEND:
            play_video_frame(video_write)

            if video_finished(video_write):
                letter_to_print = random.choice(letters)
                current_video = video_send
                video_send.set(cv2.CAP_PROP_POS_FRAMES, 0)
                state = STATE_SENDING
                send_start_time = pygame.time.get_ticks()
                printed_during_send = False

        elif state == STATE_SENDING:
            play_video_frame(video_send)

            # Печать по таймеру после старта видео отправки
            if not printed_during_send:
                if send_start_time is None:
                    send_start_time = pygame.time.get_ticks()
                elapsed_ms = pygame.time.get_ticks() - send_start_time
                if elapsed_ms >= PRINT_DELAY_SECONDS * 1000:
                    card = get_random_card()
                    start_print_deamon(printer=printer, card=card)
                    print(f"Печатается письмо:\n{card.image_path}\n")
                    printed_during_send = True

            # Если видео отправки закончилось
            if video_finished(video_send):
                if not printed_during_send:
                    card = get_random_card()
                    start_print_deamon(printer=printer, card=card)
                    print(f"Печатается письмо:\n{card.image_path}\n")
                    

                current_video = video_write
                video_write.set(cv2.CAP_PROP_POS_FRAMES, 0)
                state = STATE_WRITING
                send_start_time = None
                printed_during_send = False

        pygame.display.flip()
        clock.tick(30)

finally:
    # Гарантируем закрытие порта при выходе
    button.close()
    pygame.quit()