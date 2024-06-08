import esptool
import serial

class FwUpdate:
    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for port, desc, hwid in sorted(ports):
            available_ports.append((port, desc, hwid))
            print(f"Port: {port}, Description: {desc}, Hardware ID: {hwid}")
        return available_ports
    
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