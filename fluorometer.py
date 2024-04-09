import serial
import time

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
    _demo_values = [0.0, 50000.0, 10000.0, 20000.0, 30000.0, 40000.0]
    _demo_idx = 0

    def __init__(self, port):
        if port == Fluorometer.DEMO_PORT:
            self.demo_mode = True
        else:
            self.demo_mode = False
            self.serialInst = serial.Serial(
                baudrate=9600,
                timeout=10,
                port=port
            )
            self.serialInst.readline() # Wait for Arduino to initialize

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
            retval = Fluorometer._demo_values[Fluorometer._demo_idx]
            Fluorometer._demo_idx = (self._demo_idx + 1) % len(Fluorometer._demo_values)
            return retval
        else:
            self.serialInst.write(f'r{int(led_power*255/100)}\r'.encode('utf-8'))
            val = self.serialInst.readline().decode('utf-8').strip()
            if val == "":
                raise Exception("No response from Arduino")
            return float(val)

    # Stubs to allow use as a context manager
    def __enter__(self):
        return self    
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False