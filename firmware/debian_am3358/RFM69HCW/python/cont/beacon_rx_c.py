#!/usr/bin/python

# RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX 
#
# RX Beacon for testing semtech chips
#
# RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX RX 

import sys
import time
import Adafruit_BBIO.GPIO as GPIO
from Adafruit_BBIO.SPI import SPI

class ModeError(Exception):
  def __init__(self, value):
        self.value = value
  def __str__(self):
      return repr(self.value)

class NoCallSign(Exception):
  def __init__(self, value):
        self.value = value
  def __str__(self):
      return repr(self.value)

class CheckError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
      return repr(self.value)


# Registers
sx1231_reg = {
        "RegFifo"          : 0x00,
        "RegOpMode"        : 0x01,
        "RegDataModul"     : 0x02,
        "RegBitrateMsb"    : 0x03,
        "RegBitrateLsb"    : 0x04,
        "RegFdevMsb"       : 0x05,
        "RegFdevLsb"       : 0x06,
        "RegFrfMsb"        : 0x07,
        "RegFrfMid"        : 0x08,
        "RegFrfLsb"        : 0x09,
        "RegPaLevel"       : 0x11,
        "RegLna"           : 0x18,
        "RegRxBw"          : 0x19,
        "RegAfcBw"         : 0x1a,
        "RegAfcFei"        : 0x1e,
        "RegAfcMsb"        : 0x1f,
        "RegAfcLsb"        : 0x20,
        "RegRssiConfig"     : 0x23,
        "RegRssiValue"     : 0x24,
        "RegDioMapping1"     : 0x25,
        "RegDioMapping2"     : 0x26,
        "RegIrqFlags2"     : 0x28,
        "RegRssiThresh"    : 0x29,
        "RegPreambleMsb"   : 0x2c,
        "RegSyncConfig"    : 0x2e,
        "RegSyncValue1"    : 0x2f,
        "RegPacketConfig1" : 0x37,
        "RegPayloadLength" : 0x38,
        "RegAutoModes"     : 0x3b,
        "RegFifoThresh"    : 0x3c,
        "RegTestPllBW"     : 0x5f,
        }

# inverse dictionary for register name lookup
inv_sx1231_reg = {v: k for k, v in sx1231_reg.items()}

# RegSyncConfig
SyncOn              =  (1 << 7)
FifoFillSyncAddress =  (0 << 6)
FifoFillCondition   =  (1 << 6)

def SyncSize(bytes):
    return ((((bytes) - 1) & 0x7) << 3)

def SyncTol(errors):
    return ((errors) & 0x7)



# RegAfcFei
AfcAutoOn           = (1 << 2)
AfcAutoclearOn      = (1 << 3)
AfcDone             = (1 << 4)


#Automodes
EnterNone           =   (0b000 << 5)
EnterFifoNotEmpty   =   (0b001 << 5)
EnterFifoLevel      =   (0b010 << 5)
EnterCrcOk          =   (0b011 << 5)
EnterPayloadReady   =   (0b100 << 5)
EnterSyncAddress    =   (0b101 << 5)
EnterPacketSent     =   (0b110 << 5)
EnterFifoEmpty      =   (0b111 << 5)
ExitNone            =   (0b000 << 2)
ExitFifoEmpty       =   (0b001 << 2)
ExitFifoLevel       =   (0b010 << 2)
ExitCrcOk           =   (0b011 << 2)
ExitPayloadReady    =   (0b100 << 2)
ExitSyncAddress     =   (0b101 << 2)
ExitPacketSent      =   (0b110 << 2)
ExitTimeout         =   (0b111 << 2)
InterSleep          =   (0b00  << 0)
InterStdby          =   (0b01  << 0)
InterRX             =   (0b10  << 0)
InterTX             =   (0b11  << 0)

# Modes
MODE_RX                    = (1 << 4)
MODE_TX                    = (3 << 2)
LISTEN_ON                  = (1 << 6)
LISTEN_ABORT               = (1 << 5)

# PA
PA0                        = (1 << 7)
PA1                        = (1 << 6)
PA2                        = (1 << 5)

# RegLna
LnaZin50                   = (0x1 << 7)
LnaGain_G6                 = (0x6 << 0)
LnaGain_AGC                = (0x0 << 0)

# RegTestPllBW
PLLBandwidth_75kHz         = (0x0 << 2)

# RegDataModul
DataModul_Packet           = (0b00 << 5)
DataModul_Continuous       = (0b10 << 5)
DataModul_ContinuousNoSync = (0b11 << 5)
DataModul_FSK              = (0b00 << 3)
DataModul_OOK              = (0b01 << 3)
DataModul_NoShaping        = (0b00 << 0)

# sx1231 RegOpMode s
# sx1231 Datasheet p 65
SLEEP_MODE       = (0b000<<2)
STANDBY_MODE     = (0b001<<2)
FS_MODE          = (0b010<<2)
TRANSMITTER_MODE = (0b011<<2)
RECEIVER_MODE    = (0b100<<2)

G0_PIN           = "P9_12"
G1_PIN           = "P8_7"   # DIO1/DCLK
G2_PIN           = "P8_8"   # DIO2/DATA
G3_PIN           = "P8_9"
G4_PIN           = "P8_10"
G5_PIN           = "P8_12"
BLUE_LEDPIN      = "P9_41"
MODULE_EN        = "P9_23"
MODULE_RST       = "P9_15"
SPI0_MISO        = "P9_21"
SPI0_MOSI        = "P9_18"
SPI0_CLK         = "P9_22"
SPI0_CS          = "P9_17"

LED_STATE        = 1

Fxosc            = 32e6
Fstep            = 61.03515625

def check_register(addr, value):
  vals = RFM_SPI.xfer2([addr, 0x0])
  if vals[1] != value:
      str = "addr: "+ hex(addr) + "(" + inv_sx1231_reg[addr] + ")" + " should be: " + hex(value) + " got: " + hex(vals[1])
      raise CheckError(str)
  print "Reg{",hex(addr),"}(",inv_sx1231_reg[addr],")\t\t=", hex(vals[1])


def PAOutputCfg(PA, Power):
    return (((PA) & (PA0 | PA1 | PA2)) | ((Power) & 0x1F))

count = 0
byte = 0x0

def g0int(a):
    print "g0"

def g1int(a):
    global count
    global byte
    rxrdy = GPIO.input(G4_PIN)
    if rxrdy == 1 :
      count = count+1
      value = GPIO.input(G2_PIN)
      if value == 1 :
          byte = byte | 1<<count
      else:
          byte = byte | 0<<count  #  no effect - conceptual
  
    if count >= 7:
      print hex(byte)," ",
      count = 0
      byte  = 0

    sys.stdout.flush()

def g2int(a):
    pass
    # global count
    # # print "g2"
    # count = count+1

def g3int(a):
    print "rssi g3"
def g4int(a):
    print "rx_rdy g4"
def g5int(a):
    print "g5"


def io_setup():
  GPIO.setup(BLUE_LEDPIN, GPIO.OUT)
  GPIO.setup(MODULE_EN, GPIO.OUT)
  GPIO.setup(MODULE_RST, GPIO.OUT)
  GPIO.setup(G0_PIN, GPIO.IN)
  GPIO.setup(G1_PIN, GPIO.IN)
  GPIO.setup(G2_PIN, GPIO.IN)
  GPIO.setup(G3_PIN, GPIO.IN)
  GPIO.setup(G4_PIN, GPIO.IN)
  # GPIO.add_event_detect(G0_PIN, GPIO.FALLING, callback=g0int)
  GPIO.add_event_detect(G1_PIN, GPIO.RISING,  callback=g1int)
  # GPIO.add_event_detect(G3_PIN, GPIO.RISING,  callback=g3int)
  GPIO.add_event_detect(G4_PIN, GPIO.RISING,  callback=g4int)
  # GPIO.add_event_detect(G2_PIN, GPIO.RISING,  callback=g2int)


def blue_invert():
  global LED_STATE
  if(LED_STATE) == 1:
    LED_STATE=0
    GPIO.output(BLUE_LEDPIN,GPIO.HIGH)
  else:
    LED_STATE=1
    GPIO.output(BLUE_LEDPIN,GPIO.LOW)

def blue_blink(n):
    for num in range(0,n):
        blue_invert()
    time.sleep(0.25)

def RFM69HCW_Write_Register(reg, val):
  reg = reg | 0x80
  # print "reg is: ", bin(reg)
  # print "val is: " , bin(val)
  # RFM_SPI.writebytes([reg, val])
  RFM_SPI.xfer2([reg, val])

def RFM69HCW_Read_Register(reg):
  regval = RFM_SPI.xfer2([reg, 0x0])
  return regval[1]

# TODO: Collapse some of these multibyte register writes into a single def Wed 23 August 2017 17:08:45 (PDT)


# Facts:
#   Fxosc = 32Mhz
#   Fstep = 32e6/2^9  =  61.03515625
#   Frf   = int(carrier_hz/Fstep)
def RFM69HCW_Write_Carrier_Freq(carrier_hz):

  global Fstep
  frf      = int(carrier_hz / Fstep)

  # vals = RFM_SPI.xfer2([RegFrfMsb, 0x0, 0x0, 0x0])
  # print "Pre: vals=\t", hex(vals[0]), "\t", hex(vals[1]), "\t", hex(vals[2]), "\t", hex(vals[3])

  frfmsb = (frf>>16) & 0xff
  frfmid = (frf>>8)  & 0xff
  frflsb = frf       & 0xff

  wbuf      = [(sx1231_reg["RegFrfMsb"]|0x80), int(frfmsb), int(frfmid), int(frflsb)]
  RFM_SPI.writebytes(wbuf)

  vals = RFM_SPI.xfer2([sx1231_reg["RegFrfMsb"], 0x0, 0x0, 0x0])
  # print "Post: vals=\t", hex(vals[0]), "\t", hex(vals[1]), "\t", hex(vals[2]), "\t", hex(vals[3])

def RFM69HCW_Set_Freq_Deviation(freq_dev_hz):
  global Fstep
  freqdev = int(freq_dev_hz/Fstep)

  wbuf    = [(sx1231_reg["RegFdevMsb"]|0x80), (int(freqdev>>8) & 0x3f), int(freqdev&0xff)]
  RFM_SPI.writebytes(wbuf)
  # print "fdev_msb:\t",
  # check_register(sx1231_reg["RegFdevMsb"], (int(freqdev>>8) & 0x3f))
  # print "\nfdev_lsb:\t",
  # check_register(sx1231_reg["RegFdevLsb"], (int(freqdev & 0xff)))
  print "\n"

def RFM69HCW_Set_Bitrate(bitrate_hz):
  global Fxosc
  rate = int(Fxosc/bitrate_hz)

  wbuf    = [(sx1231_reg["RegBitrateMsb"]|0x80), (int(rate>>8) & 0xff), int(rate&0xff)]
  RFM_SPI.writebytes(wbuf)


def RFM69HCW_Set_Sync_Value(fourbytelist):
  wbuf    = [(sx1231_reg["RegSyncValue1"]|0x80)] + fourbytelist
  RFM_SPI.writebytes(wbuf)

def RFM69HCW_Set_Preamble(twobytelist):
  wbuf    = [(sx1231_reg["RegPreambleMsb"]|0x80)] + twobytelist
  RFM_SPI.writebytes(wbuf)

def RFM69HCW_config_xcvr(OpMode, pa, RxThreshdbm):
  # RegOpMode
  #    set mode FS - Frequency Synthesizer mode
  # RFM69HCW_Write_Register(sx1231_reg["RegOpMode"], FS_MODE)
  # check_register(sx1231_reg["RegOpMode"], FS_MODE)
  # time.sleep(0.05)

  # # Set Carrier Frequency
  RFM69HCW_Write_Carrier_Freq(436500000)
  # RFM69HCW_Write_Carrier_Freq(433000000)

  RFM69HCW_Set_Freq_Deviation(20000)

  RFM69HCW_Set_Bitrate(1200)
  # RFM69HCW_Set_Bitrate(38400)
  # RFM69HCW_Set_Bitrate(19200)

  RFM69HCW_Write_Register(sx1231_reg["RegDataModul"], DataModul_Continuous | DataModul_FSK | DataModul_NoShaping)
  check_register(sx1231_reg["RegDataModul"], DataModul_Continuous | DataModul_FSK | DataModul_NoShaping)
                                                       # 0     1     2      3
  # RFM69HCW_Write_Register(sx1231_reg["RegDioMapping1"], xx<<6|xx<<4|xx<<2|xx    )

  RFM69HCW_Write_Register(sx1231_reg["RegDioMapping2"], 0b01<<6    )  # RxReady
  check_register(sx1231_reg["RegDioMapping2"], 0b01<<6)

  RFM69HCW_Write_Register(sx1231_reg["RegRxBw"], (010<<5|0x10<<3|100<<0) ) # 20.8kHz?
  # RFM69HCW_Write_Register(sx1231_reg["RegRxBw"], 0x44)  # 31.3kHz?
  # RFM69HCW_Write_Register(sx1231_reg["RegRxBw"], 0b01010011)  # 41.3kHz?

  # # PLL Bandwith
  RFM69HCW_Write_Register(sx1231_reg["RegTestPllBW"], PLLBandwidth_75kHz )

  # # LNA Input Impedance
  # RFM69HCW_Write_Register(sx1231_reg["RegLna"], (LnaZin50 | LnaGain_G6))
  RFM69HCW_Write_Register(sx1231_reg["RegLna"], (LnaZin50 | LnaGain_G6))

  # # PA Output Power
  # RFM69HCW_Write_Register(sx1231_reg["RegPaLevel"], pa )
  # check_register(sx1231_reg["RegPaLevel"], pa)

  RFM69HCW_Write_Register(sx1231_reg["RegRssiThresh"], RxThreshdbm * 2)

  RFM69HCW_Write_Register(sx1231_reg["RegOpMode"], ((LISTEN_ABORT)| OpMode))
  print("val:\t", hex((LISTEN_ABORT)| OpMode))
  RFM69HCW_Write_Register(sx1231_reg["RegOpMode"], OpMode)
  # check_register(sx1231_reg["RegOpMode"], (~(LISTEN_ON)|~(LISTEN_ABORT)) | OpMode )

  time.sleep(0.05)

def reset_radio():
  blue_blink(2)
  GPIO.output(MODULE_EN,GPIO.HIGH)
  GPIO.output(MODULE_RST,GPIO.LOW)
  time.sleep(0.5)
  GPIO.output(MODULE_RST,GPIO.HIGH)
  time.sleep(0.5)
  GPIO.output(MODULE_RST,GPIO.LOW)
  time.sleep(0.5)

def spi_config():
  global RFM_SPI
  RFM_SPI     = SPI(0,0)
  RFM_SPI.msh = 5000000

def rx_continuous():
  print "RSSI Threshold.", (RFM69HCW_Read_Register(sx1231_reg["RegRssiThresh"])/2)
  RFM69HCW_config_xcvr(MODE_RX, PAOutputCfg(PA0, 0x0),40)
  print "RSSI Threshold.", (RFM69HCW_Read_Register(sx1231_reg["RegRssiThresh"])/2)
  # print "RegRxBw.", hex(RFM69HCW_Read_Register(sx1231_reg["RegRxBw"]))
  while True:
    # RSSI VALUE REGISTER CAN ONLY BE READ IF RSSI > RSSI THREASHOLD!!!
    RFM69HCW_Write_Register(sx1231_reg["RegRssiConfig"], 0x1 )   # Trigger RSSI measure
    RFM69HCW_Write_Register(sx1231_reg["RegAfcFei"], 0x1 )   # Trigger Afc start
    AfcValMSB = RFM69HCW_Read_Register(sx1231_reg["RegAfcMsb"])
    AfcValLSB = RFM69HCW_Read_Register(sx1231_reg["RegAfcLsb"])

    AfcVal    = int(0xf & AfcValMSB << 8 | AfcValLSB)
    print "\r\nAFCVAL:\t", AfcVal

    # print " Threshold.", (RFM69HCW_Read_Register(sx1231_reg["RegRssiThresh"])/2)
    print "\r\nRSSI:\t-",(RFM69HCW_Read_Register(sx1231_reg["RegRssiValue"])/2),"dBm"
    # print "Gain setting.", hex(RFM69HCW_Read_Register(sx1231_reg["RegLna"]))
    time.sleep(2)

if __name__ == "__main__":
    try:
        print "Begin RX Beacon. Ctl-C to Quit..."
        io_setup()
        reset_radio()
        spi_config()
        rx_continuous()
        GPIO.output(BLUE_LEDPIN, GPIO.LOW)
        print "End. Ctl-C to Quit..."
        while True:
          blue_invert()
          time.sleep(0.5)


    except KeyboardInterrupt:
      GPIO.cleanup()
      print ("\nQuitting-Bye!", count)

    except ModeError as e:
      print ('Mode not supported:', e.value)

    except NoCallSign as e:
      print ('No FCC Call Sign Entered', e.value)

    except CheckError as e:
      print ('Check Error', e.value)

