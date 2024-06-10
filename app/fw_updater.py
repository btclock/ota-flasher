import os
import random
from threading import Thread
from app import espota
from app.espota import FLASH, SPIFFS
import esptool
import serial
import wx


class FwUpdater:
    update_progress = None
    currentlyUpdating = False

    def __init__(self, update_progress, event_cb):
        self.update_progress = update_progress
        self.event_cb = event_cb

    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for port, desc, hwid in sorted(ports):
            available_ports.append((port, desc, hwid))
            print(f"Port: {port}, Description: {desc}, Hardware ID: {hwid}")
        return available_ports

    def run_fs_update(self, address, firmware_file, type):
        global PROGRESS
        PROGRESS = True
        espota.PROGRESS = True
        global TIMEOUT
        TIMEOUT = 10
        espota.TIMEOUT = 10

        espota.serve(address, "0.0.0.0", 3232, random.randint(
            10000, 60000), "", firmware_file, type, self.update_progress)

        wx.CallAfter(self.update_progress, 1)
        self.currentlyUpdating = False
#        self.SetStatusText(f"Finished!")

    def flash_firmware(port, baud, firmware_path):
        try:
            # Initialize the serial port
            serial_port = serial.Serial(port, baud)

            # Initialize the ESP32ROM with the serial port
            esp = esptool.ESP32ROM(serial_port)

            # Connect to the ESP32
            esp.connect()

            # Perform the flashing operation
            esp.flash_file(firmware_path, offset=0x1000)

            # Optionally, verify the flash
            esp.verify_flash(firmware_path, offset=0x1000)

            print("Firmware flashed successfully!")

        except esptool.FatalError as e:
            print(f"Failed to flash firmware: {e}")
        finally:
            # Ensure the serial port is closed
            if serial_port.is_open:
                serial_port.close()

    def start_firmware_update(self, release_name, address, hw_rev):
#        self.SetStatusText(f"Starting firmware update")

        model_name = "lolin_s3_mini_213epd"
        if (hw_rev == "REV_B_EPD_2_13"):
            model_name = "btclock_rev_b_213epd"

        local_filename = f"firmware/{
            release_name}_{model_name}_firmware.bin"

        self.updatingName = address
        self.currentlyUpdating = True
        
        if self.event_cb is not None:
            self.event_cb("Starting Firmware update")

        if os.path.exists(os.path.abspath(local_filename)):
            thread = Thread(target=self.run_fs_update, args=(
                address, os.path.abspath(local_filename), FLASH))
            thread.start()

    def start_fs_update(self, release_name, address):
        # Path to the firmware file
        local_filename = f"firmware/{release_name}_littlefs.bin"

        self.updatingName = address
        self.currentlyUpdating = True
        
        if self.event_cb is not None:
            self.event_cb("Starting WebUI update")

        if os.path.exists(os.path.abspath(local_filename)):
            thread = Thread(target=self.run_fs_update, args=(
                address, os.path.abspath(local_filename), SPIFFS))
            thread.start()

