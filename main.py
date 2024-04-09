from fluorometer import Fluorometer
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.stats import linregress
import numpy as np
import threading

class QuantificationKit:
    """
    A class representing a quantification kit used for measuring DNA concentrations.

    Attributes:
        name (str): The name of the quantification kit.
        units (str): The units of measurement.
        standards (list): Concentrations of the calibration standards.
        led_power (float): The power (arb %) of the LED to use for measurements.
    """

    def __init__(self, name, units, standards, led_power):
        self.name = name
        self.units = units
        self.standards = standards
        self.led_power = led_power
        self.led_power = led_power

    def calculate_concentrations(self, standard_measurements, measurements):
        """
        Calculates the concentrations of the measurements by fitting a curve
        to a set of standard calibrants.

        Args:
            standard_measurements (list): A list of standard calibrant measurements.
            measurements (list): A list of sample measurements.

        Returns:
            list: A list of concentrations corresponding to the measurements.
        """
        # Fit a line to standard_measurements and standards
        slope, intercept, _, _, _ = linregress(standard_measurements, self.standards)
        
        # Calculate the concentrations of the measurements using the fitted line
        concentrations = (np.asarray(measurements) * slope + intercept)
        
        return concentrations

# Supported quantification kits
quantification_kits = [
    QuantificationKit("High Sensitivity", "ng/uL", [
        0.0,
        10.0
    ], 100),
    QuantificationKit("Broad Range", "ng/uL", [
        0.0,
        100.0
    ], 100),
]

class QuantificationKitModel:
    """
    Handles the state of a quantification kit measurement.

    Attributes:
        quantification_kit (QuantificationKit): The quantification kit used for measurements.
        units (str): The units of measurement for the quantification kit.
        standard_measurements (list): A list of standard calibrant measurements.
        standard_concentrations (list): A list of standard calibrant concentrations.
        measurements (list): A list of sample measurements.
        dilution_factors (list): A list of dilution factors for the samples.
        concentrations (list): A list of calculated concentrations for the samples.
        error (bool): Indicates if there was an error during measurement.

    Properties:
        current_instruction (str): Returns the current instruction for display to the user.

    Methods:
        generate_fitting_curve(): Generates a fitting curve based on the standard measurements.
        measure(port, led_power, known_concentration, dilution_factor): Performs a measurement using the fluorometer.
    """

    def __init__(self, quantification_kit):
        self.quantification_kit = quantification_kit
        self.units = self.quantification_kit.units
        self.standard_measurements = []
        self.standard_concentrations = []
        self.measurements = []
        self.dilution_factors = []
        self.concentrations = []
        self.error = False

    @property
    def current_instruction(self):
        if self.error:
            return "Previous measurement failed.\nCheck the fluorometer is connected."
        elif len(self.standard_measurements) < len(self.quantification_kit.standards):
            return f"Please measure standard #{len(self.standard_measurements)+1}."
        else:
            return "Please measure sample."

    def generate_fitting_curve(self):
        """
        Generates a fitting curve based on the standard measurements and the quantification kit.

        Returns:
            A tuple containing two lists:
            - The calculated concentrations based on the standard measurements and the generated curve.
            - The y-values of the generated curve.
        """
        if len(self.standard_measurements) < len(self.quantification_kit.standards):
            return [], []
        y = np.linspace(np.min(self.standard_measurements), np.max(self.standard_measurements), 100)
        return self.quantification_kit.calculate_concentrations(self.standard_measurements, y), y
    
    def measure(self, port, led_power, known_concentration, dilution_factor):
        """
        Measures the sample concentration using the fluorometer.

        Args:
            port (str): The serial port connected to the fluorometer.
            led_power (float): Unused.
            known_concentration (float): Unused.
            dilution_factor (float): The dilution factor of the sample.

        Returns:
            None

        Raises:
            Exception: If the measurement fails.
        """
        try:
            with Fluorometer(port=port) as f:
                measurement = f.read(self.quantification_kit.led_power)
                self.error = False
        except Exception as e:
            self.error = True
            print("Measure failed with exception:")
            print(e)
            return

        if len(self.standard_measurements) < len(self.quantification_kit.standards):
            self.standard_concentrations.append(self.quantification_kit.standards[len(self.standard_measurements)])
            self.standard_measurements.append(measurement)
        else:
            self.measurements.append(measurement)
            self.dilution_factors.append(dilution_factor)
            self.concentrations = self.quantification_kit.calculate_concentrations(
                self.standard_measurements,
                self.measurements
            )

class FluorometerModel:
    """
    Represents a fluorometer model used for measuring raw fluorescence.

    Attributes:
        units (str): The units of measurement for fluorescence readout.
        standard_measurements (list): A list of standard measurements.
        standard_concentrations (list): A list of standard concentrations.
        measurements (list): A list of measurements.
        dilution_factors (list): A list of dilution factors.
        concentrations (list): A list of concentrations.
        error (bool): Indicates if there was an error during measurement.

    Properties:
        current_instruction (str): Returns the current instruction for display to the user.

    Methods:
        generate_fitting_curve(): Generates a fitting curve (stubbed here).
        measure(port, led_power, known_concentration, dilution_factor): Measures the fluorescence.

    """

    def __init__(self):
        self.units = "arb."
        self.standard_measurements = []
        self.standard_concentrations = []
        self.measurements = []
        self.dilution_factors = []
        self.concentrations = []
        self.error = False

    @property
    def current_instruction(self):
        if self.error:
            return "Previous measurement failed. Please check the fluorometer is connected and try again."
        else:
            return "Please measure sample."

    def generate_fitting_curve(self):
        return [], []
    
    def measure(self, port, led_power, known_concentration, dilution_factor):
        """
        Measures the sample fluorescence using the fluorometer.

        Args:
            port (str): The serial port connected to the fluorometer.
            led_power (float): Power output of the LED to use during measurement (arb %).
            known_concentration (float): The known concentration of the sample.
            dilution_factor (float): Unused.

        Returns:
            None

        Raises:
            Exception: If the measurement fails.
        """
        try:
            with Fluorometer(port=port) as f:
                measurement = f.read(led_power)
                self.error = False
        except Exception as e:
            self.error = True
            print("Measure failed with exception:")
            print(e)
            return

        self.concentrations.append(known_concentration)
        self.dilution_factors.append(1)
        self.measurements.append(measurement)

class FluorometerUI(tk.Tk):
    """
    The main user interface class for the DIYNAFLUOR Fluorometer application.

    This class extends the `tk.Tk` class and provides the GUI for controlling the fluorometer and performing measurements.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("DIYNAFLUOR Fluorometer")
        # Add explicit quit handler, since on some systems the window close button doesn't work
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.model = QuantificationKitModel(quantification_kits[0])
        self.create_widgets()
        self.refresh_com_ports()
        self.sync_model()

    def _quit(self):
        self.quit()
        self.destroy()

    def _validate_float(self, value_if_allowed):
        if value_if_allowed == '':
            return True
        try:
            _ = float(value_if_allowed)
            return True
        except ValueError:
            return False
        
    def _clamp_led_power(self, *args):
        try:
            led_power = self.led_power.get()
        except tk.TclError:
            # Probably have an invalid value on the TCL side
            # (e.g. because the LED power field was left blank), set to 0
            self.led_power.set(0.0)
            led_power = 0.0
        
        # Clamp LED power level to 0-100, if it's out of range
        if led_power < 0:
            led_power = 0.0
            self.led_power.set(led_power)
        elif led_power > 100:
            led_power = 100.0
            self.led_power.set(led_power)

    def _change_com_port(self, *args):
        # Reset model when changing COM ports
        self._do_restart()

    def _change_mode(self, *args):
        self._do_restart()

        # Enable known concentration entry and disable dilution factor entry
        # for fluorometer mode, and vice versa for quantification kit mode
        if self.mode.get() == -1:
            self.known_concentration_entry.config(state='enabled')
            self.dilution_factor_entry.config(state='disabled')
            self.led_power_scale.config(state='enabled')
            self.measured_concentration_label_string.set("Sample Fluoresence:")
        else:
            self.known_concentration_entry.config(state='disabled')
            self.dilution_factor_entry.config(state='enabled')
            self.led_power_scale.config(state='disabled')
            self.led_power.set(self.model.quantification_kit.led_power)
            self.measured_concentration_label_string.set("Sample Concentration:")

    def _do_restart(self):
        if self.mode.get() == -1:
            self.model = FluorometerModel()
        else:
            self.model = QuantificationKitModel(quantification_kits[self.mode.get()])
        self.measure_button.config(state='enabled')
        self.sync_model()

    def _do_measure(self):
        # We perform measurements in a seperate thread, since they block on
        # serial port access which would cause the UI to freeze.
        measure_thread = threading.Thread(target=self._measure_thread)
        measure_thread.start()
        self.current_step_text.set("Measuring...")
        self.measure_button.config(state='disabled')
        self.restart_button.config(state='disabled')
        self.save_button.config(state='disabled')

    def _measure_done(self):
        self.measure_button.config(state='enabled')
        self.restart_button.config(state='enabled')
        self.save_button.config(state='enabled')
        self.sync_model()
    
    def _measure_thread(self):
        try:
            self.model.measure(
                port=self.selected_com_port.get(),
                led_power=self.led_power.get(),
                known_concentration=self.known_concentration.get(),
                dilution_factor=self.dilution_factor.get()
            )
        finally:
            self.after(0, self._measure_done)

    def _do_save(self):
        filetypes = [('CSV Files', '*.csv')]
        filename = tk.filedialog.asksaveasfilename(filetypes=filetypes, defaultextension='.csv')
        if filename:
            # Save the data to the CSV file
            with open(filename, 'w') as f:
                f.write("Sample Concentration, Flouresence, Tube Concentration, Dilution Factor\n")
                for m, tc, df in zip(self.model.measurements, self.model.concentrations, self.model.dilution_factors):
                    f.write(f"{tc*df},{m},{tc},{df}\n")
            print(f"Data saved to {filename}")

    def create_widgets(self):
        """Create and lay out widgets for the main application window."""
        # Configure the default options
        self.mode = tk.IntVar(value=0)
        self.selected_com_port = tk.StringVar(value=Fluorometer.DEMO_PORT)
        self.current_step_text = tk.StringVar(value="")
        self.led_power = tk.DoubleVar(value=100)
        self.known_concentration = tk.DoubleVar(value=0.0)
        self.dilution_factor = tk.DoubleVar(value=1.0)
        self.measured_concentration_label_string = tk.StringVar(value="Sample Concentration:")
        self.measured_concentration_string = tk.StringVar(value="-.--")
        self.measured_concentration_units_string = tk.StringVar(value=self.model.units)
        self.known_concentration_label_string = tk.StringVar(value="Known Concentration (ng/nL):")

        # Configure trace functions
        self.led_power.trace_add('write', self._clamp_led_power)
        self.selected_com_port.trace_add('write', self._change_com_port)
        self.mode.trace_add('write', self._change_mode)

        # Plot Frame
        plot_frame = ttk.Frame(self, padding="3")
        plot_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        fig, self.plot_ax = plt.subplots()
        self.fig_canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        self.fig_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Left Column Frame
        left_column_frame = ttk.Frame(self, padding="3")
        mode_labelframe = ttk.LabelFrame(left_column_frame, text="Mode:", padding="3")
        mode_inner_frame = ttk.Frame(mode_labelframe)
        last_kit_idx = 0
        for kit_idx, kit in enumerate(quantification_kits):
            ttk.Radiobutton(mode_inner_frame, text=kit.name, value=kit_idx, variable=self.mode).grid(row=kit_idx, column=0, sticky="ew")
            last_kit_idx = kit_idx
        ttk.Radiobutton(mode_inner_frame, text="Fluorometer", value=-1, variable=self.mode).grid(row=last_kit_idx+1, column=0, sticky="ew")
        led_power_label = ttk.Label(left_column_frame, text="LED Power (%):")
        self.led_power_scale = ttk.Spinbox(left_column_frame, from_=0, to=100, width=5, textvariable=self.led_power, validate='key',
                                           validatecommand=(self.register(self._validate_float), '%P'), state='disabled')

        # Right Column Frame
        right_column_frame = ttk.Frame(self, padding="3")
        com_port_label = ttk.Label(right_column_frame, text="COM Port:")
        self.com_port_combobox = ttk.Combobox(right_column_frame, textvariable=self.selected_com_port)
        known_concentration_label = ttk.Label(right_column_frame, textvariable=self.known_concentration_label_string)
        self.known_concentration_entry = ttk.Entry(right_column_frame, textvariable=self.known_concentration, state='disabled',
                                              validate='key', validatecommand=(self.register(self._validate_float), '%P'))
        dilution_factor_label = ttk.Label(right_column_frame, text="Dilution Factor:")
        self.dilution_factor_entry = ttk.Entry(right_column_frame, textvariable=self.dilution_factor, validate='key',
                                          validatecommand=(self.register(self._validate_float), '%P'))
        current_step_label = ttk.Label(right_column_frame, textvariable=self.current_step_text, foreground="red", font=("Arial", 16, "bold"), anchor='center')

        # Control Frame for Measure Button and Measured Concentration Label
        control_frame = ttk.Frame(self, padding="3")
        self.measure_button = ttk.Button(control_frame, text="Measure", command=self._do_measure)
        self.restart_button = ttk.Button(control_frame, text="Restart", command=self._do_restart)
        self.save_button = ttk.Button(control_frame, text="Save", command=self._do_save)
        measured_concentration_frame = ttk.Frame(control_frame)
        measured_concentration_label = ttk.Label(measured_concentration_frame, textvariable=self.measured_concentration_label_string)
        measured_concentration_entry = ttk.Entry(measured_concentration_frame, textvariable=self.measured_concentration_string, state='readonly', width=10)
        measured_concentration_units_label = ttk.Label(measured_concentration_frame, textvariable=self.measured_concentration_units_string)

        # Layout Configuration
        left_column_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        right_column_frame.grid(row=1, column=1, sticky="nsew")
        control_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        # Configure grid for left column frame
        mode_labelframe.grid(row=0, column=0, sticky="ew", columnspan=2)
        mode_inner_frame.grid(row=0, column=0, pady=5)
        led_power_label.grid(row=3, column=0, pady=(10, 0), sticky="w")
        self.led_power_scale.grid(row=3, column=1, pady=(10, 0), sticky="ew")

        # Configure grid for right column frame
        com_port_label.grid(row=0, column=0, pady=(10, 0), sticky="w")
        self.com_port_combobox.grid(row=0, column=1, pady=(10, 0), sticky="ew")
        known_concentration_label.grid(row=1, column=0, sticky="w")
        self.known_concentration_entry.grid(row=1, column=1, sticky="ew")
        dilution_factor_label.grid(row=2, column=0, sticky="w")
        self.dilution_factor_entry.grid(row=2, column=1, sticky="ew")
        current_step_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(20, 0))

        # Configure grid for control frame
        self.measure_button.grid(row=0, column=0, sticky="w", padx=(20, 0), pady=(0, 10), ipadx=20, ipady=5)
        self.restart_button.grid(row=0, column=1, sticky="w", padx=(20, 0), pady=(0, 10), ipadx=20, ipady=5)
        self.save_button.grid(row=0, column=2, sticky="w", padx=(20, 0), pady=(0, 10), ipadx=20, ipady=5)
        measured_concentration_frame.grid(row=0, column=3, sticky="ew", padx=(20, 20), pady=(0, 10))

        # Configure grid for measured concentration frame
        measured_concentration_label.grid(row=0, column=0, sticky="w")
        measured_concentration_entry.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        measured_concentration_units_label.grid(row=0, column=2, sticky="w")

        # Adjust grid configuration for scalability
        self.columnconfigure(1, weight=1)
        left_column_frame.columnconfigure(1, weight=1)
        mode_labelframe.columnconfigure(0, weight=1)
        right_column_frame.columnconfigure(1, weight=1)
        plot_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        
    def refresh_com_ports(self):
        # Refresh the COM port list (default to DEMO port if no COM ports are available)
        current_com_port = self.selected_com_port.get()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        ports.append(Fluorometer.DEMO_PORT)
        if current_com_port not in ports:
            current_com_port = Fluorometer.DEMO_PORT
        self.selected_com_port.set(current_com_port)
        self.com_port_combobox['values'] = ports
    
    def sync_model(self):
        # Synchronise UI to model
        self.current_step_text.set(self.model.current_instruction)
        if self.mode.get() == -1:
            if len(self.model.measurements) > 0:
                self.measured_concentration_string.set(f"{self.model.measurements[-1]:.2f}")
            else:
                self.measured_concentration_string.set("-.--")
        else:
            if len(self.model.concentrations) > 0:
                self.measured_concentration_string.set(f"{self.model.concentrations[-1] * self.model.dilution_factors[-1]:.2f}")
            else:
                self.measured_concentration_string.set("-.--")
        self.measured_concentration_units_string.set(value=self.model.units)

        self.known_concentration_label_string.set(f"Known Concentration ({self.model.units}):")

        # Update plot
        self.plot_ax.clear()
        self.plot_ax.plot(self.model.standard_concentrations, self.model.standard_measurements, 'go')
        self.plot_ax.plot(*self.model.generate_fitting_curve(), '--', color='grey')
        self.plot_ax.plot(self.model.concentrations, self.model.measurements, 'bo')
        self.plot_ax.set_xlabel(f'Tube Concentration ({self.model.units})')
        self.plot_ax.set_ylabel('Fluorescence (arb. units)')
        self.plot_ax.set_title('Fluorescence Measurements')
        self.fig_canvas.draw()

if __name__ == "__main__":
    # Run GUI main loop
    root = FluorometerUI()
    root.mainloop()