from fluorometer import Fluorometer
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading

class QuantificationKit:
    """
    A class representing a quantification kit used for measuring DNA concentrations.

    Attributes:
        name (str): The name of the quantification kit.
        units (str): The units of measurement.
        standards (list): Concentrations of the calibration standards.
        tube_volume (float): The volume (uL) of fluid (sample + mix) used for measurements.
        led_power (float): The power (arb %) of the LED to use for measurements.
    """

    def __init__(self, name, units, standards, tube_volume, led_power):
        self.name = name
        self.units = units
        self.standards = standards
        self.tube_volume = tube_volume
        self.led_power = led_power

    def validate_standard(self, standard_measurements, measurement):
        """
        Validates a provided standard measurement makes sense compared to
        the previous standard measurements.
        """
        # Assume the first standard is always correct
        if len(standard_measurements) == 0:
            return True
        # We assume that each standard increases in concentration,
        # and is at least ~1000 units greater than the previous standard.
        elif measurement <= (standard_measurements[-1] + 1000):
            return False
        else:
            return True

    def calculate_tube_concentrations(self, standard_measurements, measurements):
        """
        Calculates the concentrations of the measurements by fitting a curve
        to a set of standard calibrants.

        Args:
            standard_measurements (list): A list of standard calibrant measurements.
            measurements (list): A list of sample measurements.

        Returns:
            list: A list of tube concentrations corresponding to the measurements.
        """
        # Fit a line to standard_measurements and standards
        slope, intercept = np.polyfit(standard_measurements, self.standards, 1)
        
        # Calculate the concentrations of the measurements using the fitted line
        tube_concentrations = (np.asarray(measurements) * slope + intercept)
        
        return tube_concentrations

    def calculate_sample_concentrations(self, sample_volumes, tube_concentrations):
        """
        Converts tube concentrations (i.e. concentration in thbe measured tube)
        to sample concentrations (i.e. concentration in the original sample).

        Args:
            sample_volumes (list): A list of sample volumes (uL).
            tube_concentrations (list): A list of tube concentrations.

        Returns:
            list: A list of sample concentrations corresponding to the given tube concentrations.
        """
        sample_concentrations = [tc * self.tube_volume / sv if sv != 0 else 0 for tc, sv in zip(tube_concentrations, sample_volumes)]
        return sample_concentrations

# Supported quantification kits
quantification_kits = [
    QuantificationKit("High Sensitivity", "ng/uL", [
        0.0,
        0.5,
    ], 200, 100),
    QuantificationKit("Broad Range", "ng/uL", [
        0.0,
        5.0
    ], 200, 100),
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
        sample_inputs (list): A list of input volumes for the samples.
        tube_concentrations (list): A list of calculated concentrations for the tubes.
        sample_concentrations (list): A list of calculated concentrations for the original samples.
        error (bool): Indicates if there was an error during measurement.

    Properties:
        current_instruction (str): Returns the current instruction for display to the user.

    Methods:
        generate_fitting_curve(): Generates a fitting curve based on the standard measurements.
        measure(port, led_power, known_concentration, sample_input): Performs a measurement using the fluorometer.
    """

    def __init__(self, port, quantification_kit):
        self.fluorometer = Fluorometer(port=port)
        self.quantification_kit = quantification_kit
        self.units = self.quantification_kit.units
        self.standard_measurements = []
        self.standard_concentrations = []
        self.measurements = []
        self.sample_inputs = []
        self.tube_concentrations = []
        self.sample_concentrations = []
        self.error = False
        self.error_message = "No error set."

    @property
    def current_instruction(self):
        if self.error:
            return self.error_message
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
        return self.quantification_kit.calculate_tube_concentrations(self.standard_measurements, y), y
    
    def generate_csv(self):
        """
        Generates a CSV string containing the measured data.
        """
        ret = f"Name, Sample Concentration ({self.units}), Measured Flouresence (arb.), Tube Concentration ({self.units}), Sample Input (uL)\n"
        for i, (m, tc) in enumerate(zip(self.standard_measurements, self.standard_concentrations)):
            ret += f"Standard #{i},-,{m},{tc},-\n"
        for i, (sc, m, tc, df) in enumerate(zip(self.sample_concentrations, self.measurements, self.tube_concentrations, self.sample_inputs)):
            ret += f"Sample #{i},{sc},{m},{tc},{df}\n"
        return ret
    
    def measure(self, led_power, known_concentration, sample_input):
        """
        Measures the sample concentration using the fluorometer.

        Args:
            led_power (float): Unused.
            known_concentration (float): Unused.
            sample_input (float): The initial volume of the sample.

        Returns:
            None

        Raises:
            Exception: If the measurement fails.
        """
        try:
            measurement = self.fluorometer.read(self.quantification_kit.led_power)
            self.error = False
            self.error_message = "No error set."
        except Exception as e:
            self.error = True
            self.error_message = "Previous measurement failed.\nCheck the fluorometer is connected."
            print("Measure failed with exception:")
            print(e)
            return

        if len(self.standard_measurements) < len(self.quantification_kit.standards):
            # In calibration phase, validate this measurement and add it to the list of calibrants
            if self.quantification_kit.validate_standard(self.standard_measurements, measurement):
                self.standard_concentrations.append(self.quantification_kit.standards[len(self.standard_measurements)])
                self.standard_measurements.append(measurement)
            else:
                self.error = True
                self.error_message = f"Previous measurement failed.\nCheck the correct standard (#{len(self.standard_measurements)+1}) has been inserted."
        else:
            # Calibration complete, so measure sample instead
            self.measurements.append(measurement)
            self.sample_inputs.append(sample_input)
            self.tube_concentrations = self.quantification_kit.calculate_tube_concentrations(
                self.standard_measurements,
                self.measurements
            )
            self.sample_concentrations = self.quantification_kit.calculate_sample_concentrations(
                self.sample_inputs,
                self.tube_concentrations
            )

class FluorometerModel:
    """
    Represents a fluorometer model used for measuring raw fluorescence.

    Attributes:
        units (str): The units of measurement for fluorescence readout.
        standard_measurements (list): A list of standard measurements.
        standard_concentrations (list): A list of standard concentrations.
        measurements (list): A list of measurements.
        tube_concentrations (list): A list of tube concentrations as provided by the user.
        error (bool): Indicates if there was an error during measurement.

    Properties:
        current_instruction (str): Returns the current instruction for display to the user.

    Methods:
        generate_fitting_curve(): Generates a fitting curve (stubbed here).
        measure(port, led_power, known_concentration, sample_input): Measures the fluorescence.

    """

    def __init__(self, port):
        self.fluorometer = Fluorometer(port=port)
        self.units = "arb."
        self.standard_measurements = []
        self.standard_concentrations = []
        self.measurements = []
        self.tube_concentrations = []
        self.error = False

    @property
    def current_instruction(self):
        if self.error:
            return "Previous measurement failed. Please check the fluorometer is connected and try again."
        else:
            return "Please measure sample."

    def generate_fitting_curve(self):
        return [], []
    
    def generate_csv(self):
        """
        Generates a CSV string containing the measured data.
        """
        ret = f"Tube Concentration ({self.units}), Measured Flouresence (arb.)\n"
        for tc, m in zip(self.tube_concentrations, self.measurements):
            ret += f"{tc},{m}\n"
        return ret
    
    def measure(self, led_power, known_concentration, sample_input):
        """
        Measures the sample fluorescence using the fluorometer.

        Args:
            led_power (float): Power output of the LED to use during measurement (arb %).
            known_concentration (float): The known concentration of the sample.
            sample_input (float): Unused.

        Returns:
            None

        Raises:
            Exception: If the measurement fails.
        """
        try:
            measurement = self.fluorometer.read(led_power)
            self.error = False
        except Exception as e:
            self.error = True
            print("Measure failed with exception:")
            print(e)
            return

        self.tube_concentrations.append(known_concentration)
        self.measurements.append(measurement)

class FluorometerUI(tk.Tk):
    """
    The main user interface class for the DIYNAFLUOR Fluorometer application.

    This class extends the `tk.Tk` class and provides the GUI for controlling the fluorometer and performing measurements.
    """
    _FLUOROMETER_MODE = -1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("DIYNAFLUOR Fluorometer")
        # Add explicit quit handler, since on some systems the window close button doesn't work
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.model = QuantificationKitModel(Fluorometer.DEMO_PORT, quantification_kits[0])
        self.have_unsaved_measurements = False
        self.measurement_in_progress = False
        self.create_widgets()
        self.refresh_com_ports()
        self.sync_model()
        # Track previous mode and COM port to allow changes to be undone if
        # the user cancels the change
        self.previous_mode = self.mode.get()
        self.previous_selected_com_port = self.selected_com_port.get()

    def _quit(self):
        self.quit()
        self.destroy()

    def _generate_float_validator(self, variable, clamp_min=None, clamp_max=None):
        def _validate_float(value_if_allowed, validate_type):
            # Allow blank values / a bare minus sign for key validation,
            # but set the value to 0/clamp_min if the field is empty or invalid
            # when focus leaves it
            if value_if_allowed == '' or value_if_allowed == '-':
                if validate_type == 'focusout':
                    variable.set(clamp_min if clamp_min is not None else 0)
                return True
            try:
                float_val = float(value_if_allowed)

                # Clamp to min/max values when losing focus
                if validate_type == 'focusout':
                    if clamp_min is not None and float_val <= clamp_min:
                        variable.set(clamp_min)
                    elif clamp_max is not None and float_val >= clamp_max:
                        variable.set(clamp_max)

                return True
            except ValueError:
                return False
        return _validate_float

    def _change_com_port(self, *args):
        # Reset model when changing COM ports
        if self._do_restart():
            self.previous_selected_com_port = self.selected_com_port.get()
        else:
            self.selected_com_port.set(self.previous_selected_com_port)

    def _change_mode(self, *args):
        # Cancel the mode change if a measurement is in progress.
        if not self.measurement_in_progress and self._do_restart():
            self.previous_mode = self.mode.get()
        else:
            # Revert to previous mode and refresh radiobutton state manually,
            # since the trace that would normally do this is disabled right now
            self.mode.set(self.previous_mode)
            for rb in self.mode_radiobuttons:
                if rb['value'] == self.previous_mode:
                    rb['state'] = 'selected'
                else:
                    rb['state'] = 'alternate'

        # Enable known concentration/led power fields for fluorometer mode,
        # and disable them for quantification kit mode
        if self.mode.get() == self._FLUOROMETER_MODE:
            self.known_concentration_entry.config(state='enabled')
            self.sample_input_entry.config(state='disabled')
            self.led_power_scale.config(state='enabled')
            self.measured_concentration_label_string.set("Sample Fluoresence:")
        else:
            self.known_concentration_entry.config(state='disabled')
            self.sample_input_entry.config(state='enabled')
            self.led_power_scale.config(state='disabled')
            self.led_power.set(self.model.quantification_kit.led_power)
            self.measured_concentration_label_string.set("Sample Concentration:")

    def _do_restart(self):
        # Prompt user to save if they have unsaved data
        if self.have_unsaved_measurements:
            response = tk.messagebox.askyesnocancel(
                "Unsaved Data",
                "You have unsaved measurements. This operation will discard them, would you like to save them before continuing?",
                default=tk.messagebox.CANCEL, parent=self
            )
            if response is None:
                # User cancelled, abort the restart
                return False
            elif response:
                # User wants to save, do so
                if not self._do_save():
                    # They cancelled the save, abort the restart
                    return False

        if self.mode.get() == self._FLUOROMETER_MODE:
            self.model = FluorometerModel(self.selected_com_port.get())
        else:
            self.model = QuantificationKitModel(self.selected_com_port.get(), quantification_kits[self.mode.get()])
        self.have_unsaved_measurements = False
        self.measure_button.config(state='enabled')
        self.sync_model()
        return True

    def _do_measure(self):
        # We perform measurements in a seperate thread, since they block on
        # serial port access which would cause the UI to freeze.
        measure_thread = threading.Thread(target=self._measure_thread)
        measure_thread.start()
        self.current_step_text.set("Measuring...")
        self.measure_button.config(state='disabled')
        self.restart_button.config(state='disabled')
        self.save_button.config(state='disabled')
        self.com_port_combobox.config(state='disabled')
        self.measurement_in_progress = True

    def _measure_done(self, success):
        self.measure_button.config(state='enabled')
        self.restart_button.config(state='enabled')
        self.save_button.config(state='enabled')
        self.com_port_combobox.config(state='enabled')
        if success:
            self.have_unsaved_measurements = True
        self.measurement_in_progress = False
        self.sync_model()
    
    def _measure_thread(self):
        try:
            self.model.measure(
                led_power=self.led_power.get(),
                known_concentration=self.known_concentration.get(),
                sample_input=self.sample_input.get()
            )
        finally:
            self.after(0, self._measure_done, not self.model.error)

    def _do_save(self):
        filetypes = [('CSV Files', '*.csv')]
        filename = tk.filedialog.asksaveasfilename(filetypes=filetypes, defaultextension='.csv')
        if filename:
            # Save the data to the CSV file
            with open(filename, 'w') as f:
                f.write(self.model.generate_csv())
            print(f"Data saved to {filename}")
            self.have_unsaved_measurements = False
            return True
        else:
            return False

    def create_widgets(self):
        """Create and lay out widgets for the main application window."""
        # Configure the default options
        self.mode = tk.IntVar(value=0)
        self.selected_com_port = tk.StringVar(value=Fluorometer.DEMO_PORT)
        self.current_step_text = tk.StringVar(value="")
        self.led_power = tk.DoubleVar(value=100)
        self.known_concentration = tk.DoubleVar(value=0.0)
        self.sample_input = tk.DoubleVar(value=10.0)
        self.measured_concentration_label_string = tk.StringVar(value="Sample Concentration:")
        self.measured_concentration_string = tk.StringVar(value="-.--")
        self.measured_concentration_units_string = tk.StringVar(value=self.model.units)
        self.known_concentration_label_string = tk.StringVar(value="Known Concentration (ng/nL):")

        # Configure trace functions
        self.selected_com_port.trace_add('write', self._change_com_port)
        self.mode.trace_add('write', self._change_mode)

        # Logo
        self.logo_image = tk.PhotoImage(file="./logo.png").subsample(4)
        logo_label = ttk.Label(self, image=self.logo_image, anchor='center', borderwidth=3, relief='groove', background='white', padding=5)
        logo_label.grid(row=0, column=0, columnspan=2)

        # Plot Frame
        plot_frame = ttk.Frame(self, padding="3")
        plot_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        fig, self.plot_ax = plt.subplots()
        self.fig_canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        self.fig_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Left Column Frame
        left_column_frame = ttk.Frame(self, padding="3")
        mode_labelframe = ttk.LabelFrame(left_column_frame, text="Mode:", padding="3")
        mode_inner_frame = ttk.Frame(mode_labelframe)
        last_kit_idx = 0
        self.mode_radiobuttons = []
        for kit_idx, kit in enumerate(quantification_kits):
            kit_radiobutton = ttk.Radiobutton(mode_inner_frame, text=kit.name, value=kit_idx, variable=self.mode)
            kit_radiobutton.grid(row=kit_idx, column=0, sticky="ew")
            self.mode_radiobuttons.append(kit_radiobutton)
            last_kit_idx = kit_idx
        fluorometer_radiobutton = ttk.Radiobutton(mode_inner_frame, text="Fluorometer", value=self._FLUOROMETER_MODE, variable=self.mode)
        fluorometer_radiobutton.grid(row=last_kit_idx+1, column=0, sticky="ew")
        self.mode_radiobuttons.append(fluorometer_radiobutton)
        led_power_label = ttk.Label(left_column_frame, text="LED Power (%):")
        self.led_power_scale = ttk.Spinbox(left_column_frame, from_=0, to=100, width=5, textvariable=self.led_power, validate='all',
                                           validatecommand=(self.register(self._generate_float_validator(self.led_power, clamp_min=0, clamp_max=100)), '%P', '%V'),
                                           state='disabled')

        # Right Column Frame
        right_column_frame = ttk.Frame(self, padding="3")
        com_port_label = ttk.Label(right_column_frame, text="COM Port:")
        self.com_port_combobox = ttk.Combobox(right_column_frame, textvariable=self.selected_com_port)
        known_concentration_label = ttk.Label(right_column_frame, textvariable=self.known_concentration_label_string)
        self.known_concentration_entry = ttk.Entry(right_column_frame, textvariable=self.known_concentration, state='disabled',
                                              validate='all', validatecommand=(self.register(self._generate_float_validator(self.known_concentration, clamp_min=0)), '%P', '%V'))
        sample_input_label = ttk.Label(right_column_frame, text="Sample Input (uL):")
        self.sample_input_entry = ttk.Entry(right_column_frame, textvariable=self.sample_input, validate='key',
                                          validatecommand=(self.register(self._generate_float_validator(self.sample_input, clamp_min=0)), '%P', '%V'))
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
        left_column_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        right_column_frame.grid(row=2, column=1, sticky="nsew")
        control_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="ew")

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
        sample_input_label.grid(row=2, column=0, sticky="w")
        self.sample_input_entry.grid(row=2, column=1, sticky="ew")
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
        self.rowconfigure(2, weight=1)
        
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
        if self.mode.get() == self._FLUOROMETER_MODE:
            if len(self.model.measurements) > 0:
                self.measured_concentration_string.set(f"{self.model.measurements[-1]:.2f}")
            else:
                self.measured_concentration_string.set("-.--")
        else:
            if len(self.model.sample_concentrations) > 0:
                self.measured_concentration_string.set(f"{self.model.sample_concentrations[-1]:.2f}")
            else:
                self.measured_concentration_string.set("-.--")
        self.measured_concentration_units_string.set(value=self.model.units)

        self.known_concentration_label_string.set(f"Known Concentration ({self.model.units}):")

        # Update plot
        self.plot_ax.clear()
        self.plot_ax.plot(self.model.standard_concentrations, self.model.standard_measurements, 'go')
        self.plot_ax.plot(*self.model.generate_fitting_curve(), '--', color='grey')
        self.plot_ax.plot(self.model.tube_concentrations, self.model.measurements, 'bo')
        self.plot_ax.set_xlabel(f'Tube Concentration ({self.model.units})')
        self.plot_ax.set_ylabel('Fluorescence (arb. units)')
        self.plot_ax.set_title('Fluorescence Measurements')
        self.fig_canvas.draw()

if __name__ == "__main__":
    # Run GUI main loop
    root = FluorometerUI()
    root.mainloop()