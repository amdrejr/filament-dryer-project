'''!
  @file DFRobot_AHT20.py
  @brief This AHT20 temperature & humidity sensor employs digital output and I2C interface, through which users can read the measured temperature and humidity. Based on the AHT20 chip, it offers the following features:
  @n 1. Collect ambient temperature, unit Celsius (℃), range -40-85℃, resolution: 0.01, error: ±0.3-±1.6℃
  @n 2. Collect ambient relative humidity, unit: %RH, range 0-100%RH, resolution 0.024%RH, error: when the temprature is 25℃, error range is ±2-±5%RH
  @n 3. Use I2C interface, I2C address is default to be 0x38
  @n 4. uA level sensor, the measuring current supply is less than 200uA
  @n 5. Power supply range 3.3-5V
  @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license     The MIT License (MIT)
  @author [Arya](xue.peng@dfrobot.com)
  @author [Joep Weijers](joep.weijers@gmail.com)
  @version  V1.1
  @date  2023-06-06
  @url https://github.com/DFRobot/DFRobot_AHT20
  @url https://github.com/joepweijers/DFRobot_AHT20_MicroPython
'''

import time
from machine import I2C

class DFRobot_AHT20:
  ## Default I2C address of AHT20 sensor 
  AHT20_DEF_I2C_ADDR           = 0x38
  ## Init command
  CMD_INIT 	                   = '\xBE\x08\x00'
  ## Waiting time for init completion: 0.01s
  CMD_INIT_TIME                = 0.01 
  ## Trigger measurement command
  CMD_MEASUREMENT              = b'\xAC\x33\x00'
  ## Measurement command completion time：0.08s
  CMD_MEASUREMENT_TIME         = 0.08
  ## Return data length when the measurement command is without CRC check.
  CMD_MEASUREMENT_DATA_LEN     = 6
  ## Return data length when the measurement command is with CRC check.
  CMD_MEASUREMENT_DATA_CRC_LEN = 7
  ## Soft reset command
  CMD_SOFT_RESET               = b'\xBA'
  ## Soft reset time: 0.02s
  CMD_SOFT_RESET_TIME          = 0.02
  ## Get status word command
  CMD_STATUS                   = b'\x71'

  _humidity = 0.0
  _temperature = 0.0
  
  def __init__(self, i2c: I2C):
    self._addr = self.AHT20_DEF_I2C_ADDR
    self._i2c = i2c

  def begin(self):
    '''!
      @brief   Initialize AHT20 sensor
      @return  Return init status
      @retval True  Init succeeded
      @retval False Init failed
    '''
    if self._init() != True:
      return False
    return True
  
  def reset(self):
    '''!
      @brief   Sensor soft reset, restore the sensor to the initial status
      @return  NONE
    '''
    self._write_command(self.CMD_SOFT_RESET)
    time.sleep(self.CMD_SOFT_RESET_TIME)
  
  def start_measurement_ready(self, crc_en = False):
    '''!
      @brief   Start measurement and determine if it's completed.
      @param crc_en Whether to enable check during measurement
      @n     True  If the measurement is completed, call a related function such as get* to obtain the measured data.
      @n     False If the measurement failed, the obtained data is the data of last measurement or the initial value 0 if the related function such as get* is called at this time.
      @return  Whether the measurement is done
      @retval True  If the measurement is completed, call a related function such as get* to obtain the measured data.
      @retval False If the measurement failed, the obtained data is the data of last measurement or the initial value 0 if the related function such as get* is called at this time.
    '''
    recv_len = self.CMD_MEASUREMENT_DATA_LEN
    if self._ready() == False:
      print("Not calibrated")
      return False
    if crc_en:
      recv_len = self.CMD_MEASUREMENT_DATA_CRC_LEN
    self._write_command(self.CMD_MEASUREMENT)
    time.sleep(self.CMD_MEASUREMENT_TIME)
    l_data = self._read_data(recv_len)
    if l_data[0] & 0x80:
      print("AHT20 is busy!")
      return False
    if crc_en and self._check_crc8(l_data[6], l_data[:6]) == False:
      print("crc8 check failed.")
      return False
    temp = l_data[1]
    temp <<= 8
    temp |= l_data[2]
    temp <<= 4
    temp = temp | (l_data[3] >> 4)
    temp = (temp & 0xFFFFF) * 100.0
    self._humidity = temp / 0x100000

    temp = l_data[3] & 0x0F
    temp <<= 8
    temp |= l_data[4]
    temp <<= 8
    temp |= l_data[5]
    temp = (temp & 0xFFFFF) * 200.0
    self._temperature = temp / 0x100000 - 50
    return True


  def get_temperature_F(self):
    '''!
      @brief   Get ambient temperature, unit: Fahrenheit (F).
      @return  Temperature in F
      @note  AHT20 can't directly get the temp in F, the temp in F is calculated according to the algorithm: F = C x 1.8 + 32
      @n  Users must call the start_measurement_ready function once before calling the function to start the measurement so as to get the real-time measured data,
      @n  otherwise what they obtained is the initial data or the data of last measurement.
    '''
    return self._temperature * 1.8 + 32

  def get_temperature_C(self):
    '''!
      @brief   Get ambient temperature, unit: Celsius (℃).
      @return  Temperature in ℃, it's normal data within the range of -40-85℃, otherwise it's wrong data
      @note  Users must call the start_measurement_ready function once before calling the function to start the measurement so as to get the real-time measured data,
      @n  otherwise what they obtained is the initial data or the data of last measurement.
    '''
    return self._temperature
  
  def get_humidity_RH(self):
    '''!
      @brief   Get ambient relative humidity, unit: %RH.
      @return  Relative humidity, range 0-100
      @note  Users must call the start_measurement_ready function once before calling the function to start the measurement so as to get the real-time measured data,
      @n  otherwise what they obtained is the initial data or the data of last measurement.
    '''
    return self._humidity

  def _check_crc8(self, crc8, data):
    # CRC initial value: 0xFF
    # CRC8 check polynomial: CRC[7: 0] = X8 + X5 + X4 + 1  -  0x1 0011 0001 - 0x131
    crc = 0xFF
    pos = 0
    size = len(data)
    while pos < size:
      i = 8
      crc ^= data[pos]
      while i > 0:
        if crc & 0x80:
          crc <<= 1
          crc ^= 0x31
        else:
          crc <<= 1
        i -= 1
      pos += 1
    crc &= 0xFF
    if crc8 == crc:
      return True
    return False

  def _ready(self):
    status = self._get_status_data()
    if status & 0x08:
      return True
    return False

  def _init(self):
    status = self._get_status_data()
    if status & 0x08:
      return True
    self._write_command(self.CMD_INIT)
    time.sleep(self.CMD_INIT_TIME)
    status = self._get_status_data()
    if status & 0x08:
      return True
    return False
  
  def _get_status_data(self):
    self._i2c.writeto(self._addr, self.CMD_STATUS)
    status = self._read_data(1)
    if len(status):
      return status[0]
    else:
      return 0
  
  def _read_data(self, len):
    try:
      return self._i2c.readfrom(self._addr, len)
    except Exception as e:
      print("Error in _read_data")
      print(e)
      return []
  
  def _write_command(self, cmd):
    self._i2c.writeto(self._addr, cmd)