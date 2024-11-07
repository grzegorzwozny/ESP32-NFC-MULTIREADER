### Multicard Reader PN5180 NFC ISO15693

This repository contains the code for a Multicard NFC Reader based on the PN5180, supporting ISO15693 cards. The project is implemented using MicroPython on an ESP32, with two NFC readers connected via SPI for simultaneous card detection.

### Features:
- **Dual NFC Reader Support**: Two ISO15693-compatible NFC readers (PN5180) are interfaced with the ESP32 via SPI.
- **NFC Card Detection**: Reads UID from NFC cards and saves them to Non-Volatile Storage (NVS).
- **LED Indicators**: Displays activity using an LED bar, with an active indicator that blinks when a button is pressed.
- **Button Handling**: A physical button allows activation of the NFC reading process.
- **Real-time NFC Inventory**: Continuously monitors NFC cards in 16-slot inventories.
- **Data Logging**: The unique UIDs of detected NFC cards are saved into NVS for later use.

### Hardware Setup:
- **ESP32**: Microcontroller running the MicroPython code.
- **NFC PN5180 Modules**: Two ISO15693 NFC readers connected via SPI.
- **LED Bar**: Used to visually indicate the NFC reading status.
- **Button**: Used to activate the NFC card reading function.

### Code Overview:
1. **LED_BAR Class**: Defines output pins for an LED bar to indicate NFC activity.
2. **BUTTONS Class**: Configures a button to trigger NFC scanning.
3. **SPI_NFC Class**: Configures the SPI interface for two NFC modules (PN5180).
4. **App Class**: Main application class that:
   - Initializes NFC readers.
   - Controls the LED bar based on button status.
   - Handles button presses to activate NFC scanning.
   - Reads and saves NFC card UIDs to NVS.

### How It Works:
1. The app waits for the user to press the button (`button_c1`), which triggers the reading of NFC cards from both readers.
2. Once activated, the app reads the NFC cards in both 16-slot inventories.
3. If cards are detected, the app prints the UIDs to the console and saves them to NVS.
4. The LED bar blinks to indicate that the scanning process is active.

### Installation:
1. Install MicroPython on the ESP32.
2. Upload the Python code to the ESP32.
3. Connect the NFC readers to the specified SPI pins.

### Example Output:
```python
# NFC: ISO15693 Card(s) Found!
# Total: 1
# UID #1: ['0x3', '0x4', '0x5', '0x6']
# EEPROM saved!: (uid_1):  [48, 50, 51, 52]
# ------------------
````

### License:
This project is licensed under the MIT License. See the LICENSE file for more details.

### Contributions:
Feel free to fork the repository and submit pull requests to improve the project. Contributions are welcome!

