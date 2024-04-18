import serial
import time
import random

class Fluorometer:
    """
    Handles serial connections to the DIYNAFLUOR device.

    The port 'DEMO' is a special port that simulates the device.

    Methods:
        __init__(self, port): Initializes a Fluorometer instance.
        read(self, led_power): Reads the fluorometer value.
        __enter__(self): Enters the context manager.
        __exit__(self, exc_type, exc_val, exc_tb): Exits the context manager.
    """

    DEMO_PORT = "DEMO"
    _demo_init_values = [0.0, 25000.0]

    def __init__(self, port):
        self.port = port
        if port == Fluorometer.DEMO_PORT:
            self.demo_idx = 0
            self.demo_mode = True
        else:
            self.demo_mode = False

    def read(self, led_power):
        """
        Reads a sample fluoresence value.

        Args:
            led_power (float): The power of the LED in percentage.

        Returns:
            float: The fluorometer value.
        
        Raises:
            Exception: If there is no response from the Arduino.
        """
        if self.demo_mode:
            time.sleep(0.25)
            if self.demo_idx < len(Fluorometer._demo_init_values):
                retval = Fluorometer._demo_init_values[self.demo_idx]
                self.demo_idx = self.demo_idx + 1
            else:
                retval = random.random() * 25000.0
            return retval
        else:
            self.serialInst.write(f'r{int(led_power*255/100)}\r'.encode('utf-8'))
            val = self.serialInst.readline().decode('utf-8').strip()
            if val == "":
                raise Exception("No response from Arduino")
            return float(val)

    def __enter__(self):
        if not self.demo_mode:
            self.serialInst = serial.Serial(
                baudrate=9600,
                timeout=10,
                port=self.port
            )
            self.serialInst.readline() # Wait for Arduino to initialize
        return self    
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False