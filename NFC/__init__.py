from uasyncio import sleep_ms

# GLOBAL SETTIGNS
DEBUG_INFO = True

class REGISTERS:
    SYSTEM_CONFIG               = 0x00
    IRQ_ENABLE                  = 0x01
    IRQ_STATUS                  = 0x02
    IRQ_CLEAR                   = 0x03
    TRANSCEIVE_CONTROL          = 0x04
    TIMER1_RELOAD               = 0x0c
    TIMER1_CONFIG               = 0x0f
    RX_WAIT_CONFIG              = 0x11
    CRC_RX_CONFIG               = 0x12
    RX_STATUS                   = 0x13
    TX_CONFIG                   = 0x18
    CRC_TX_CONFIG               = 0x19
    RF_STATUS                   = 0x1d
    SYSTEM_STATUS               = 0x24
    TEMP_CONTROL                = 0x25

class IRQ_STATUS_REG:
    RX_IRQ_STAT                 = 1<<0  # End of RF rececption IRQ
    TX_IRQ_STAT                 = 1<<1  # End of RF transmission IRQ
    IDLE_IRQ_STAT               = 1<<2  # IDLE IRQ
    RFOFF_DET_IRQ_STAT          = 1<<6  # RF Field OFF detection IRQ
    RFON_DET_IRQ_STAT           = 1<<7  # RF Field ON detection IRQ
    TX_RFOFF_IRQ_STAT           = 1<<8  # RF Field OFF in PCD IRQ
    TX_RFON_IRQ_STAT            = 1<<9  # RF Field ON in PCD IRQ
    RX_SOF_DET_IRQ_STAT         = 1<<14 # RF SOF Detection IRQ

class CMDS:
    WRITE_REGISTER              = 0x00
    WRITE_REGISTER_OR_MASK      = 0x01
    WRITE_REGISTER_AND_MASK     = 0x02
    READ_REGISTER               = 0x04
    WRITE_EEPROM                = 0x06
    READ_EEPROM                 = 0x07
    SEND_DATA                   = 0x09
    READ_DATA                   = 0x0A
    SWITCH_MODE                 = 0x0B
    LOAD_RF_CONFIG              = 0x11
    RF_ON                       = 0x16
    RF_OFF                      = 0x17

class EEPROM_ADDRS:
    DIE_IDENTIFIER              = 0x00
    PRODUCT_VERSION             = 0x10
    FIRMWARE_VERSION            = 0x12
    EEPROM_VERSION              = 0x14
    IRQ_PIN_CONFIG              = 0x1A

class ISO15693_ERROR_CODE:
    EC_NO_CARD                  = -1
    EC_OK                       = 0x00
    EC_NOT_SUPPORTED            = 0x01
    EC_NOT_RECOGNIZED           = 0x02
    EC_OPTION_NOT_SUPPORTED     = 0x03
    EC_UNKNOWN_ERROR            = 0x0f
    EC_BLOCK_NOT_AVAILABLE      = 0x10
    EC_BLOCK_ALREADY_LOCKED     = 0x11
    EC_BLOCK_IS_LOCKED          = 0x12
    EC_BLOCK_NOT_PROGRAMMED     = 0x13
    EC_BLOCK_NOT_LOCKED         = 0x14
    EC_CUSTOM_CMD_ERROR         = 0xA0

class TRANSCEIVE_STAT:
    TS_IDLE                     = 0
    TS_WAIT_TRANSMIT            = 1
    TS_TRANSMITTING             = 2
    TS_WAIT_RECEIVE             = 3
    TS_WAIT_FOR_DATA            = 4
    TS_RECEIVING                = 5
    TS_LOOP_BACK                = 6
    TS_RESERVED                 = 7

# CLASSES
class PN5180:
    def __init__(self, spi, nss, busy, rst):
        self.DEBUG("PN5180 Constructor.")
        self.PN5180_SPI  = spi
        self.PN5180_NSS  = nss
        self.PN5180_BUSY = busy
        self.PN5180_RST  = rst

    # PUBLIC METHOD(S)
    async def begin(self):
        self.DEBUG("Start PN5180.")
        self.PN5180_RST.value(1)  # Disable
        self.PN5180_BUSY.value(1) # No Reset
    
    async def reset(self):
        self.DEBUG("Reset.")
        self.PN5180_RST.value(0) # A minimum of 10us is required
        await sleep_ms(10)
        self.PN5180_RST.value(1) # Required 2ms to ramp-up
        await sleep_ms(10)
        # Wait for system to start-up
        while (0 == (IRQ_STATUS_REG.IDLE_IRQ_STAT & await self.get_irq_status()) ): pass
        self.DEBUG("\tStart-up OK")
        await self.clear_irq_status(0xffffffff) # Clear all flags

    async def get_irq_status(self):
        self.DEBUG("Read IRQ-Status register...")
        irq_status, result = await self.read_register(REGISTERS.IRQ_STATUS)
        irq_status = int.from_bytes(irq_status, 'little')
        self.DEBUG("\tIRQ-Status = " + str(irq_status))
        return irq_status    

    async def clear_irq_status(self, irq_mask):
        self.DEBUG("Clear IRQ-Status with mask = " + str(hex(irq_mask)))
        return await self.write_register(REGISTERS.IRQ_CLEAR, irq_mask)

    async def get_product_version(self):
        self.DEBUG("Get product version.")
        prod_ver, result = await self.read_eeprom(EEPROM_ADDRS.PRODUCT_VERSION, 2)
        return list(prod_ver)
    
    async def get_eeprom_version(self):
        self.DEBUG("Get EEPROM version.")
        eeprom_ver, result = await self.read_eeprom(EEPROM_ADDRS.EEPROM_VERSION, 2)
        return list(eeprom_ver)

    async def get_firmware_version(self):
        self.DEBUG("Get firmware version.")
        firmware_ver, result = await self.read_eeprom(EEPROM_ADDRS.FIRMWARE_VERSION, 2)
        return list(firmware_ver)

    async def get_irq_config(self):
        self.DEBUG("Ger IRQ Configuration.")
        irq_conf, result = await self.read_eeprom(EEPROM_ADDRS.IRQ_PIN_CONFIG, 1)
        return list(irq_conf)

    # WRITE_REGISTER: 0x00
    async def write_register(self, reg, value):
        self.DEBUG("Write Register: " + str(hex(reg)))
        self.DEBUG("\twrite value (LSB 1st) = " + str(hex(value)))
        # For all 4 bytes command parameter transfer (e.g. register values), the payload
        # parameters passed follow the little endian approach (Least Significant Bytest first).
        buffer = bytes([CMDS.WRITE_REGISTER, reg])
        buffer = buffer + value.to_bytes(4, 'little')
        self.DEBUG("\tWrite Register buffer: " + str(buffer))
        await self.__transceive_cmds(buffer)
        return True

    # WRITE_REGISTER_OR_MASK: 0x01
    async def write_register_with_or_mask(self, reg, mask):
        self.DEBUG(f"Write register {hex(reg)} with OR mask (LSB 1st)={hex(mask)}")
        buffer = bytes([CMDS.WRITE_REGISTER_OR_MASK, reg])
        buffer = buffer + mask.to_bytes(4, 'little')
        self.DEBUG("\tWrite Register with mask OR buffer: " + str(buffer))
        await self.__transceive_cmds(buffer)
        return True

    # WRITE_REGISTER_AND_MASK: 0x02
    async def write_register_with_and_mask(self, reg, mask):
        self.DEBUG(f"Write register {hex(reg)} with AND mask (LSB 1st)={hex(mask)}")
        buffer = bytes([CMDS.WRITE_REGISTER_AND_MASK, reg])
        buffer = buffer + mask.to_bytes(4, 'little')
        self.DEBUG("\tWrite Register with mask AND buffer: " + str(buffer))
        await self.__transceive_cmds(buffer)
        return True

    # READ_REGISTER: 0x04
    async def read_register(self, reg):
        self.DEBUG("Reading register: " + str(hex(reg)))
        cmd = [CMDS.READ_REGISTER, reg] 
        rx_data, result = await self.__transceive_cmds(cmd, 4)
        self.DEBUG("\tRegister value = " + str(rx_data))
        return rx_data, True

    # READ_EEPROM: 0x07
    async def read_eeprom(self, addr, rcv_len):
        # Address out of range protection
        if (addr > 254):
            print("ERROR: Reading beyond addr 254!")
            return False
        
        self.DEBUG("Reading EEPROM at " + str(hex(addr)))
        cmd = [CMDS.READ_EEPROM, addr, rcv_len]
        rxdata, result = await self.__transceive_cmds(cmd, rcv_len)
        self.DEBUG("\tEEPROM read values: " + str(rxdata))
        return rxdata, True

    # SEND_DATA: 0x09
    async def send_data(self, data, valid_bits=0):
        if (len(data) > 260):
            self.DEBUG("ERROR: The Send Data with more than 260 bytes is not supported!")
            return False
        
        self.DEBUG(f"Send Data (len = {len(data)}): {data}")
        # valid_bits = number of valid bits of last byte are transmitted (0 = all bits are transmitted)
        buffer = [CMDS.SEND_DATA, valid_bits] + data

        await self.write_register_with_and_mask(REGISTERS.SYSTEM_CONFIG, 0xfffffff8) # Idle/StopCom Command
        await self.write_register_with_or_mask(REGISTERS.SYSTEM_CONFIG, 0x00000003)  # Transceive Command  
        """
        Transceive command; initiates a transceive cycle.
        Note: Depending on the value of the Initiator bit, a
        transmission is started or the receiver is enabled
        Note: The transceive command does not finish
        automatically. It stays in the transceive cycle until
        stopped via the IDLE/StopCom command
        """
        transceive_state = await self.get_transceive_state()
        if ( TRANSCEIVE_STAT.TS_WAIT_TRANSMIT != transceive_state):
            self.DEBUG("\tERROR: Transceiver not in state WaitTransmit!")
            return False

        await self.__transceive_cmds(buffer)
        return True

    # READ_DATA: 0x0A
    async def read_data(self, length):
        if (length > 508):
            self.DEBUG(f"ERROR: Reading more than 508 bytes is not supported!")
            return 0
        
        self.DEBUG(f"Reading Data (len = {length})")
        cmd = [CMDS.READ_DATA, 0x00]
        read_buffer, result = await self.__transceive_cmds(cmd, length)
        self.DEBUG(f"\tData read: {read_buffer}")
        return read_buffer

    # LOAD_RF_CONFIG: 0x11
    async def load_RF_Config(self, tx_conf, rx_conf):
        self.DEBUG(f"Load RF-Config: txConf = {tx_conf}, rxConf = {rx_conf}")
        cmd = [CMDS.LOAD_RF_CONFIG, tx_conf, rx_conf]
        await self.__transceive_cmds(cmd)
        return True

    # RF_ON: 0x16
    async def set_RF_on(self):
        self.DEBUG("Set RF ON")
        cmd = [CMDS.RF_ON, 0x00]
        await self.__transceive_cmds(cmd)
        # Wait for RF field
        while ( (IRQ_STATUS_REG.TX_RFON_IRQ_STAT & await self.get_irq_status() ) == 0 ): pass
        await self.clear_irq_status(IRQ_STATUS_REG.TX_RFON_IRQ_STAT)
        return True

    async def set_RF_off(self):
        self.DEBUG("Set RF OFF")
        cmd = [CMDS.RF_OFF, 0x00]
        await self.__transceive_cmds(cmd)
        # Wait for RF field to shut down
        # TODO: Test RF Off functionality.
        # while ( (IRQ_STATUS_REG.TX_RFOFF_IRQ_STAT & self.get_irq_status() ) == 0 ): pass
        await self.clear_irq_status(IRQ_STATUS_REG.TX_RFOFF_IRQ_STAT)
        return True

    async def send_eof(self):
        self.DEBUG("Send EOF")
        cmd = [CMDS.SEND_DATA, 0x00]
        await self.__transceive_cmds(cmd)
        return True

    # Helper functions
    async def DEBUG(self, debug_str):
        if DEBUG_INFO:
            print(debug_str)
    
    async def get_transceive_state(self):
        self.DEBUG("Get Transceive state...")

        rf_status, result = await self.read_register(REGISTERS.RF_STATUS)
        if (not result):
            self.DEBUG("ERROR: Reading RF_STATUS register.")
            return TRANSCEIVE_STAT.TS_IDLE
        """
        TRANSCEIVE STATES:
            0 - idle
            1 - wait transmit
            2 - transmitting
            3 - wait receive
            4 - wait for data
            5 - receiving
            6 - loopback
            7 - reserved
        """
        state = ( (int.from_bytes(rf_status,"little") >> 24) & 0x07 )
        self.DEBUG(f"\tTRANSCEIVE_STATE = {hex(state)}")
        return state

    # PRIVATE METHOD(S)
    async def __transceive_cmds(self, tx_data, rx_data_len=0):
        self.DEBUG("Transceive Commands.")
        self.DEBUG("\tSending SPI frame: " + str(bytes(tx_data)))
        # 0.
        while (self.PN5180_BUSY.value() != 0): pass # Wait until busy is low
        # 1.
        self.PN5180_NSS.value(0)
        await sleep_ms(2)
        # 2.
        self.PN5180_SPI.write(bytes(tx_data))
        self.DEBUG("\tPN5180_SPI.write: " + str(bytes(tx_data)))
        # 3.
        while (self.PN5180_BUSY.value() != 1): pass # Wait until busy is high
        # 4.
        self.PN5180_NSS.value(1)
        await sleep_ms(1)
        # 5.
        while (self.PN5180_BUSY.value() != 0): pass # Wait until busy is low

        # Check, if write-only
        self.DEBUG("\tCheck, if write-only")
        if ( not rx_data_len ):
            return 0, True
        self.DEBUG("\tReceiving SPI frame...")

        # 1.
        self.PN5180_NSS.value(0)
        await sleep_ms(2)
        # 2.
        rx_data = self.PN5180_SPI.read(rx_data_len)
        # 3.
        while (self.PN5180_BUSY.value() != 1) : pass # Wait until busy is high
        # 4.
        self.PN5180_NSS.value(1)
        await sleep_ms(1)
        # 5.
        while (self.PN5180_BUSY.value() != 0) : pass # Wait until busy is low
        self.DEBUG(f"\tReceived Data: {str(rx_data)}")
        return rx_data, True

class ISO15693(PN5180):
    def __init__(self, *args):
        self.DEBUG("ISO15693 Constructor.")
        super().__init__(*args)

    # PUBLIC METHODS
    # Inventory, code=01
    # Request format: SOF, Req.Flags, Inventory, AFI (opt.), Mask len, Mask value, CRC16, EOF
    # Response format: SOF, Resp.Flags, DSFID, UID, CRC16, EOF
    async def get_inventory_16_slots(self):
        self.DEBUG("Get Inventory 16 Slots...")
        inventory =  [0x06, 0x01, 0x00] # NFC payload defined by ISO15693-3 2000.
                    # 0x06: Flag Byte: High data rate, 
                    #                  Inventory flag set, 
                    #                  16 Slot, AFI not prsent.
                    # 0x01: Inventory Command.
                    # 0x00: Mask Length.

        await self.setup_RF()
        await self.clear_irq_status(0x000fffff)
        await self.send_data(inventory)
        await sleep_ms(15)

        uid_buffer, uid_counter = [], 0
        for i in range(16):
            if ( (await self.get_irq_status() & IRQ_STATUS_REG.RX_SOF_DET_IRQ_STAT) != 0 ):
                rx_status, result_red_reg = await self.read_register(REGISTERS.RX_STATUS);
                length = (int.from_bytes(rx_status, 'little') & 0x000001ff)
                result_read_data = await self.read_data(length)
                uid_buffer.append(result_read_data)
                uid_counter += 1

            await self.write_register_with_and_mask(REGISTERS.TX_CONFIG,     0xfffffb3f) # Send onlu EOF
            await self.write_register_with_and_mask(REGISTERS.SYSTEM_CONFIG, 0xfffffff8) # Idle/StopCom Command
            await self.write_register_with_or_mask (REGISTERS.SYSTEM_CONFIG, 0x00000003) # Transceive Command

            await self.clear_irq_status(0x000fffff) # Clears the interrupt register IRQ_STATUS
            await self.send_eof()
        
        if (len(uid_buffer) and uid_counter):
            return ISO15693_ERROR_CODE.EC_OK, uid_counter, uid_buffer
        else:
            # No card(s) detected
            return ISO15693_ERROR_CODE.EC_NO_CARD, uid_counter, uid_buffer
        
    # Helper Function(s)
    async def setup_RF(self):
        await self.set_RF_off()

        self.DEBUG("Setup RF. Loading RF Configuration...")
        if (await self.load_RF_Config(0x0D, 0x8D)): # ISO15693 Configuration
            self.DEBUG("\tDONE. RF Conf. OK.")
        else:
            return False

        self.DEBUG("\tTurning ON RF Field...")
        if ( await self.set_RF_on() ):
            self.DEBUG("\tDONE. RF Field Turn-on.")
        else:
            return False

        await self.write_register_with_and_mask( REGISTERS.SYSTEM_CONFIG, 0xfffffff8 )   # Idle/StopCom Command
        await self.write_register_with_or_mask ( REGISTERS.SYSTEM_CONFIG, 0x00000003 )   # Transceive Command
        return True
    