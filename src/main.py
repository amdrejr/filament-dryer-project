from machine import I2C, Pin
from time import sleep, time
import sys

from libs.servo import Servo
from libs.ssd1306 import SSD1306_I2C
import libs.DFRobot_AHT20 as DFRobot_AHT20

# Params
TEMP_ON = 42.0
TEMP_OFF = 47.0
TEMP_MEDIO = 45.0

HUM_ON = 23
HUM_OFF = 18

EXAUSTOR_MAX_TIME = 45  # segundos

SERVO_OPEN = 50
SERVO_CLOSE = 148

ptc_ligado = False
exaustor_ligado = False
exaustor_inicio = 0

# Servo motor
servo=Servo(pin=15)

# Animação
spinner_frames = ["|", "/", "-", "\\"]
spinner_idx = 0


# Functions de controle
def ligar_ptc():
    ptc.value(1)


def desligar_ptc():
    ptc.value(0)


def ligar_exaustor():
    servo.move(SERVO_OPEN) # abrir duto
    sleep(1)
    exaustor.value(1)


def desligar_exaustor():
    exaustor.value(0)
    servo.move(SERVO_CLOSE) # fechar duto
    sleep(1)


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

try:
    servo.move(SERVO_CLOSE)  # iniciar fechado
    inicio = time()
    while True:

        temperatura, umidade = read_AHT20()

        if temperatura is None:
            sleep(1)
            continue
    
        if temperatura > 55:
            print("Finalizando por segurança, temperatura acima de 55C")
            desligar_ptc()

            if exaustor_ligado:
                desligar_exaustor()

            break

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

        if not exaustor_ligado and umidade >= HUM_ON and temperatura >= TEMP_MEDIO:
            ligar_exaustor()
            exaustor_ligado = True
            exaustor_inicio = agora

            print("EXAUSTOR LIGADO")

        elif exaustor_ligado:

            tempo_ligado = agora - exaustor_inicio

            if umidade <= HUM_OFF or tempo_ligado >= EXAUSTOR_MAX_TIME:
                desligar_exaustor()

                exaustor_ligado = False

                print("EXAUSTOR DESLIGADO")

        # --------------------
        # OLED
        # --------------------

        oled.text(f"PTC: {'ON' if ptc_ligado else 'OFF'}", 0, 25)
        oled.text(f"Exaustor: {'ON' if exaustor_ligado else 'OFF'}", 0, 35)

        # marcar tempo total de execução aplicação formato HH:MM:SS
        tempo_total = time() - inicio
        horas = int(tempo_total // 3600)
        minutos = int((tempo_total % 3600) // 60)
        segundos = int(tempo_total % 60)
        oled.text(f"Tempo: {horas:02d}:{minutos:02d}:{segundos:02d}", 0, 45)

        # Animação
        oled.text(spinner_frames[spinner_idx], 120, 54)
        spinner_idx = (spinner_idx + 1) % len(spinner_frames)

        oled.show()

        sleep(1)

finally:
    print("Desligando PTC e Exaustor...")
    if ptc_ligado:
        desligar_ptc()
        print("PTC DESLIGADO")
    if exaustor_ligado:
        desligar_exaustor()
        print("EXAUSTOR DESLIGADO")
    servo.move(SERVO_CLOSE)
    servo.stop()