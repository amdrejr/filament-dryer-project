from machine import I2C, Pin
from time import sleep, time
import sys

from libs.ssd1306 import SSD1306_I2C
import libs.DFRobot_AHT20 as DFRobot_AHT20

# Params
TEMP_ON = 42.0
TEMP_OFF = 47.0

HUM_ON = 25.0
HUM_OFF = 20.0

EXAUSTOR_MIN_TIME = 30  # segundos

ptc_ligado = False
exaustor_ligado = False
exaustor_inicio = 0

# Animação
spinner_frames = ["|", "/", "-", "\\"]
spinner_idx = 0


# Functions de controle
def ligar_ptc():
    ptc.value(1)


def desligar_ptc():
    ptc.value(0)


def ligar_exaustor():
    exaustor.value(1)


def desligar_exaustor():
    exaustor.value(0)


i2c = I2C(0, sda=Pin(16), scl=Pin(17))
print("Scan i2c:", i2c.scan())
pin = Pin("LED", Pin.OUT)

exaustor = Pin(22, Pin.OUT)
ptc = Pin(20, Pin.OUT)


# Iniciar display
try:
    oled = SSD1306_I2C(width=128, height=64, i2c=i2c)
except Exception as e:
    print("Erro ao iniciar o display:", e)
    sys.exit(1)


# Iniciar sensor AHT20
try:
    sensor_AHT20 = DFRobot_AHT20.DFRobot_AHT20(i2c)

    if sensor_AHT20.begin() != True:
        print("Failed to start sensor")
        sys.exit(1)
except Exception as e:
    print("Erro ao iniciar o sensor AHT20:", e)
    sys.exit(1)


# Função para ler o sensor AHT20 e atualizar o display
def read_AHT20():
    try:
        sensor_AHT20.start_measurement_ready()

        temperature = sensor_AHT20.get_temperature_C()
        humidity = sensor_AHT20.get_humidity_RH()

        oled.fill(0)
        oled.text(f"Temp: {temperature:.1f}C", 0, 0)
        oled.text(f"Umid: {humidity:.1f}%", 0, 10)
        print(f"Temperatura: {temperature:.1f}C, Umidade: {humidity:.1f}%")
        oled.show()

        return temperature, humidity

    except Exception as e:
        print("Erro leitura sensor:", e)
        raise e


while True:

    temperatura, umidade = read_AHT20()

    if temperatura is None:
        sleep(3)
        continue

    # --------------------
    # CONTROLE DO PTC
    # --------------------

    if not ptc_ligado and temperatura <= TEMP_ON:
        ligar_ptc()
        ptc_ligado = True
        print("PTC LIGADO")

    elif ptc_ligado and temperatura >= TEMP_OFF:
        desligar_ptc()
        ptc_ligado = False
        print("PTC DESLIGADO")

    # --------------------
    # CONTROLE EXAUSTOR
    # --------------------

    agora = time()

    if not exaustor_ligado and umidade >= HUM_ON and temperatura >= TEMP_ON:
        ligar_exaustor()
        exaustor_ligado = True
        exaustor_inicio = agora

        print("EXAUSTOR LIGADO")

    elif exaustor_ligado:

        tempo_ligado = agora - exaustor_inicio

        if umidade <= HUM_OFF and tempo_ligado >= EXAUSTOR_MIN_TIME:
            desligar_exaustor()

            exaustor_ligado = False

            print("EXAUSTOR DESLIGADO")

    # --------------------
    # OLED
    # --------------------

    oled.text(f"PTC: {'ON' if ptc_ligado else 'OFF'}", 0, 25)
    oled.text(f"Exaustor: {'ON' if exaustor_ligado else 'OFF'}", 0, 35)

    # Animação
    oled.text(spinner_frames[spinner_idx], 120, 54)
    spinner_idx = (spinner_idx + 1) % len(spinner_frames)

    oled.show()

    sleep(3)
