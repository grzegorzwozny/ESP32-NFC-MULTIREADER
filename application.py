import esp32, machine, NFC 
from machine import Pin, SPI
from uasyncio import sleep_ms

# Set CPU Frequency
machine.freq(240000000)

class LED_BAR:
    # led_a1      = Pin(?, mode      = Pin.OUT) # Vib
    # led_a2      = Pin(?, mode      = Pin.OUT) # Mic
    # led_a3      = Pin(?, mode      = Pin.OUT) # WiFi
    # led_a4      = Pin(?, mode      = Pin.OUT) # Ready
    # led_a5      = Pin(?, mode      = Pin.OUT) # BLE
    led_a6      = Pin(46, mode      = Pin.OUT)  # Count

class BUTTONS:
    button_c1   = Pin(3, mode      = Pin.IN, pull = Pin.PULL_UP)  # Count
    # button_c2   = Pin(?, mode      = Pin.IN, pull = Pin.PULL_UP) # Assign
    # button_c3   = Pin(?, mode      = Pin.IN, pull = Pin.PULL_UP) # BLE
    # button_c4   = Pin(?, mode      = Pin.IN, pull = Pin.PULL_UP) # WiFi

class SPI_NFC:
    spi         = SPI(2,  baudrate  = 1000000, 
                          polarity  = 0, 
                          phase     = 0, 
                          bits      = 8, 
                          firstbit  = SPI.MSB, 
                          sck       = Pin(12),
                          mosi      = Pin(13),
                          miso      = Pin(11))
    nss_nfc_1   = Pin(10, mode      = Pin.OUT)
    busy_nfc_1  = Pin(14, mode      = Pin.IN)
    rst_nfc_1   = Pin(9,  mode      = Pin.OUT)

    nss_nfc_2   = Pin(18, mode      = Pin.OUT)
    busy_nfc_2  = Pin(17, mode      = Pin.IN)
    rst_nfc_2   = Pin(8,  mode      = Pin.OUT)


class App:
    def __init__(self):
        # Initialize LED Bar
        LED_BAR.led_a6.value(0)
        # Reader #1: Create NFC Interface
        self.nfc_1 = NFC.ISO15693( SPI_NFC.spi,
                                   SPI_NFC.nss_nfc_1,
                                   SPI_NFC.busy_nfc_1,
                                   SPI_NFC.rst_nfc_1 )
        # Reader #2: Create NFC Interface
        self.nfc_2 = NFC.ISO15693( SPI_NFC.spi,
                                   SPI_NFC.nss_nfc_2,
                                   SPI_NFC.busy_nfc_2,
                                   SPI_NFC.rst_nfc_2 )
        # Create an objects providing access to a NVS namespaces
        self.nfc_1_nvs = esp32.NVS('NFC_1_UIDS')
        self.nfc_2_nvs = esp32.NVS('NFC_2_UIDS')

    # GLOBAL FLAGS
    __btn_c1_is_active = False

    async def led_bar(self):
        while True:
            if(self.__btn_c1_is_active):
                LED_BAR.led_a6.value(1)
                await sleep_ms(100)
                LED_BAR.led_a6.value(0)
                await sleep_ms(100)
            await sleep_ms(10)

    async def buttons(self):
        while True:
            if( not BUTTONS.button_c1.value() ):
                await sleep_ms(50) # Reduce Debouncing.
                self.__btn_c1_is_active = True
            await sleep_ms(100)

    async def nfc_readers(self):
        await self.nfc_1.begin()
        await self.nfc_1.reset()
        await self.nfc_2.begin()
        await self.nfc_2.reset()

        while True:
            if(self.__btn_c1_is_active):
                await self.show_and_save(await self.nfc_1.get_inventory_16_slots())
                await self.show_and_save(await self.nfc_2.get_inventory_16_slots())    
                # Disactivate flag
                self.__btn_c1_is_active = False
            await sleep_ms(100)

    async def show_and_save(self, inventory):
        rc, num, uid = inventory

        if (rc == NFC.ISO15693_ERROR_CODE.EC_OK):
            print("\r\n*** NFC: ISO15693 Card(s) Found!")
            print(f"\tTotal: {num}")

            uids = [list(map(hex,list(x[2:]))) for x in uid]
            for u in uids:
                print(f"\tUID #{uids.index(u) + 1}: " + str(u))
                # Store data in NVS partition (EEPROM)
                print(f"\t\tEEPROM saved!: (uid_{uids.index(u) + 1}):  {uid[uids.index(u)]}")
                self.nfc_1_nvs.set_blob('uid_' + str(uids.index(u) + 1), uid[uids.index(u)] )
            print("------------------\r\n")
        else:
            print(f"*** NFC: No card detected!")
            print(f"\tError Code: {rc}")
            print("------------------\r\n")