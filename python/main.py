import importlib.util
import subprocess
import sys

_REQUIRED = {
    "serial":     "pyserial",
    "PIL":        "Pillow",
    "matplotlib": "matplotlib",
    "numpy":      "numpy",
}

for _import_name, _pkg_name in _REQUIRED.items():
    if importlib.util.find_spec(_import_name) is None:
        print(f"Installing missing dependency: {_pkg_name}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", _pkg_name])

from fluorometer import Fluorometer
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import sys
import platform
from pathlib import Path

# Version number to display on the GUI
VERSION = (1, 1, 0)

# ── Colour palette ─────────────────────────────────────────────────────────────
_BLUE        = "#1976D2"
_BLUE_DARK   = "#1565C0"
_BLUE_LIGHT  = "#E3F2FD"
_GREEN       = "#2E7D32"
_RED         = "#C62828"
_ORANGE      = "#E65100"
_GREY        = "#78909C"
_BG          = "#F5F7FA"


class ToolTip:
    """Shows a small tooltip when the mouse hovers over a widget."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            self._tip, text=self.text, background="#FFFDE7",
            relief="solid", borderwidth=1, font=("Arial", 9),
            padx=6, pady=3, wraplength=240,
        )
        lbl.pack()

    def _hide(self, _event=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


class QuantificationKit:
    """
    A class representing a quantification kit used for measuring DNA concentrations.

    Attributes:
        name (str): The name of the quantification kit.
        units (str): The units of measurement.
        standards (list): Concentrations of the calibration standards.
        tube_volume (float): The volume (μL) of fluid (sample + mix) used for measurements.
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
        Converts tube concentrations (i.e. concentration in the measured tube)
        to sample concentrations (i.e. concentration in the original sample).

        Args:
            sample_volumes (list): A list of sample volumes (μL).
            tube_concentrations (list): A list of tube concentrations.

        Returns:
            list: A list of sample concentrations corresponding to the given tube concentrations.
        """
        sample_concentrations = [tc * self.tube_volume / sv if sv != 0 else 0
                                  for tc, sv in zip(tube_concentrations, sample_volumes)]
        return sample_concentrations


# Supported quantification kits
quantification_kits = [
    QuantificationKit("High Sensitivity", "ng/μL", [
        0.0,
        0.5,
    ], 200, 100),
    QuantificationKit("Broad Range", "ng/μL", [
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
            return f"Please measure standard #{len(self.standard_measurements) + 1}."
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
        ret = f"Name, Sample Concentration ({self.units}), Measured Fluorescence (arb.), Tube Concentration ({self.units}), Sample Input (μL)\n"
        for i, (m, tc) in enumerate(zip(self.standard_measurements, self.standard_concentrations)):
            ret += f"Standard #{i},-,{m},{tc:.4f},-\n"
        for i, (sc, m, tc, si) in enumerate(zip(self.sample_concentrations, self.measurements, self.tube_concentrations, self.sample_inputs)):
            ret += f"Sample #{i},{sc:.4f},{m:.4f},{tc:.4f},{si:.4f}\n"
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
                self.error_message = f"Previous measurement failed.\nCheck the correct standard (#{len(self.standard_measurements) + 1}) has been inserted."
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
        ret = f"Tube Concentration ({self.units}), Measured Fluorescence (arb.)\n"
        for tc, m in zip(self.tube_concentrations, self.measurements):
            ret += f"{tc:.4f},{m:.4f}\n"
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

    This class extends the `tk.Tk` class and provides the GUI for controlling
    the fluorometer and performing measurements.
    """
    _FLUOROMETER_MODE = -1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the window icon, on win32 this must be done before calling create_widgets
        self.configure_window_icon()

        self.title("DIYNAFLUOR Fluorometer")
        # Add explicit quit handler, since on some systems the window close button doesn't work
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.model = QuantificationKitModel(Fluorometer.DEMO_PORT, quantification_kits[0])
        self.have_unsaved_measurements = False
        self.measurement_in_progress = False
        self._connection_status = "demo"
        self._refreshing_ports = False

        self._setup_styles()
        self.create_widgets()
        self.refresh_com_ports()
        self.sync_model()

        # Track previous mode and COM port to allow changes to be undone if
        # the user cancels the change
        self.previous_mode = self.mode.get()
        self.previous_selected_com_port = self.selected_com_port.get()

        # Reset the window icon, we need to do this on macOS as matplotlib overwrites the
        # icon we set earlier
        self.configure_window_icon()

        self.minsize(700, 580)

    def _setup_styles(self):
        """Configure ttk styles for the application."""
        style = ttk.Style(self)
        style.theme_use("clam")
        self.configure(background=_BG)

        # Primary (Measure) button — visually distinct blue
        style.configure("Primary.TButton",
                        background=_BLUE, foreground="white",
                        font=("Arial", 10, "bold"), padding=(14, 6))
        style.map("Primary.TButton",
                  background=[("active", _BLUE_DARK), ("disabled", "#BDBDBD")],
                  foreground=[("disabled", "#9E9E9E")])

        # Standard buttons
        style.configure("TButton", font=("Arial", 10), padding=(8, 4))

        # Base label / frame / radiobutton backgrounds
        style.configure("TLabel",      background=_BG, font=("Arial", 10))
        style.configure("TFrame",      background=_BG)
        style.configure("TLabelframe", background=_BG)
        style.configure("TLabelframe.Label", background=_BG, font=("Arial", 10, "bold"))
        style.configure("TRadiobutton", background=_BG, font=("Arial", 10))

        # Instruction label — normal (blue tinted panel)
        style.configure("Instruction.TLabel",
                        foreground=_BLUE_DARK, font=("Arial", 12),
                        background=_BLUE_LIGHT, padding=(10, 8), anchor="center")
        # Instruction label — error (red tinted panel)
        style.configure("Error.Instruction.TLabel",
                        foreground=_RED, font=("Arial", 12, "bold"),
                        background="#FFEBEE", padding=(10, 8), anchor="center")

        # Large result value
        style.configure("Result.TLabel",
                        foreground=_BLUE, font=("Arial", 26, "bold"),
                        background="white")
        style.configure("ResultUnit.TLabel",
                        foreground=_GREY, font=("Arial", 13),
                        background="white")
        style.configure("ResultTitle.TLabel",
                        foreground=_GREY, font=("Arial", 9),
                        background="white")

        # Small progress annotation
        style.configure("Progress.TLabel",
                        background=_BG, font=("Arial", 9), foreground=_GREY)

        # Treeview (history table)
        style.configure("Treeview",
                        background="white", fieldbackground="white",
                        font=("Arial", 9), rowheight=22)
        style.configure("Treeview.Heading", font=("Arial", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", _BLUE_LIGHT)],
                  foreground=[("selected", "#1A237E")])

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
        if self._refreshing_ports:
            return
        # Reset model when changing COM ports
        if self._do_restart():
            self.previous_selected_com_port = self.selected_com_port.get()
        else:
            self.selected_com_port.set(self.previous_selected_com_port)
        port = self.selected_com_port.get()
        self._update_status_dot("demo" if port == Fluorometer.DEMO_PORT else "unknown")

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
            self.measured_concentration_label_string.set("Sample Fluorescence:")
            self.calibration_frame.grid_remove()
        else:
            self.known_concentration_entry.config(state='disabled')
            self.sample_input_entry.config(state='enabled')
            self.led_power_scale.config(state='disabled')
            self.led_power.set(self.model.quantification_kit.led_power)
            self.measured_concentration_label_string.set("Sample Concentration:")
            self.calibration_frame.grid()

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
        # We perform measurements in a separate thread, since they block on
        # serial port access which would cause the UI to freeze.
        measure_thread = threading.Thread(target=self._measure_thread)
        measure_thread.start()
        self.current_step_text.set("Measuring...")
        self.current_step_label.config(style="Instruction.TLabel")
        self.measure_button.config(state='disabled')
        self.restart_button.config(state='disabled')
        self.save_button.config(state='disabled')
        self.refresh_button.config(state='disabled')
        self.com_port_combobox.config(state='disabled')
        self.measurement_in_progress = True

    def _measure_done(self, success):
        self.measure_button.config(state='enabled')
        self.restart_button.config(state='enabled')
        self.save_button.config(state='enabled')
        self.refresh_button.config(state='enabled')
        self.com_port_combobox.config(state='enabled')
        if success:
            self.have_unsaved_measurements = True
            if self.selected_com_port.get() != Fluorometer.DEMO_PORT:
                self._update_status_dot("ok")
        else:
            if self.selected_com_port.get() != Fluorometer.DEMO_PORT:
                self._update_status_dot("error")
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

    def _update_status_dot(self, status):
        """Update the COM port connection status indicator colour."""
        colors = {
            "demo":    _ORANGE,
            "unknown": _GREY,
            "ok":      _GREEN,
            "error":   _RED,
        }
        self.status_canvas.itemconfig(self.status_oval, fill=colors.get(status, _GREY))
        self._connection_status = status

    def _current_kit_standards(self):
        """Return the current kit's standards list, or [] in fluorometer mode."""
        if self.mode.get() == self._FLUOROMETER_MODE:
            return []
        return quantification_kits[self.mode.get()].standards

    def configure_window_icon(self):
        """Set the icon for the main application window."""
        try:
            icon_path = Path(sys._MEIPASS) / "icon.png"
        except Exception:
            icon_path = Path(__file__).parent / "icon.png"
        icon_image = Image.open(icon_path)
        icon_photo = ImageTk.PhotoImage(icon_image)
        self.iconphoto(True, icon_photo)

    def create_widgets(self):
        """Create and lay out widgets for the main application window."""

        # ── Variables ──────────────────────────────────────────────────────────
        self.mode = tk.IntVar(value=0)
        self.selected_com_port = tk.StringVar(value=Fluorometer.DEMO_PORT)
        self.current_step_text = tk.StringVar(value="")
        self.led_power = tk.DoubleVar(value=100)
        self.known_concentration = tk.DoubleVar(value=0.0)
        self.sample_input = tk.DoubleVar(value=10.0)
        self.measured_concentration_label_string = tk.StringVar(value="Sample Concentration:")
        self.measured_concentration_string = tk.StringVar(value="—")
        self.measured_concentration_units_string = tk.StringVar(value=self.model.units)

        # Configure trace functions
        self.selected_com_port.trace_add('write', self._change_com_port)
        self.mode.trace_add('write', self._change_mode)

        # ── Row 0: Logo ────────────────────────────────────────────────────────
        try:
            logo_path = Path(sys._MEIPASS) / "logo.png"
        except Exception:
            logo_path = Path(__file__).parent / "logo.png"

        logo_image = Image.open(logo_path)
        logo_scale = logo_image.width / (self.winfo_fpixels('2.9i'))
        logo_photo = ImageTk.PhotoImage(logo_image.resize(
            (int(logo_image.width / logo_scale), int(logo_image.height / logo_scale))
        ))
        self.logo_image = logo_photo
        logo_label = ttk.Label(self, image=self.logo_image, anchor='center',
                               borderwidth=3, relief='groove', background='white', padding=5)
        logo_label.grid(row=0, column=0, columnspan=2, sticky="ew")
        version_label = ttk.Label(self, text=f"v{VERSION[0]}.{VERSION[1]}.{VERSION[2]}",
                                  anchor='e', padding=5)
        version_label.place(relx=1, rely=0, anchor='ne')

        # ── Row 1: Plot ────────────────────────────────────────────────────────
        fig, self.plot_ax = plt.subplots()
        fig.patch.set_facecolor(_BG)
        self.fig_canvas = FigureCanvasTkAgg(fig, master=self)
        self.fig_canvas.get_tk_widget().grid(row=1, column=0, columnspan=2,
                                              sticky='nsew', padx=6, pady=(6, 0))
        # Workaround: On macOS, the default figure DPI passed to the constructor is multiplied by
        # [NSWindow backingScaleFactor] to ensure consistent figure sizing between platforms.
        # This then seems to get doubled again when the canvas is rendered by TkInter, so we
        # explicitly fix the DPI here to match the size of a TkInter point to avoid this issue.
        # This may be addressed in a future version of matplotlib, after which this line may not
        # be necessary.
        fig.set_dpi(self.fig_canvas.get_tk_widget().winfo_fpixels('1i'))

        # ── Row 2: Settings ────────────────────────────────────────────────────
        settings_frame = ttk.Frame(self, padding=(6, 6, 6, 0))
        settings_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        # Left sub-column: Mode + Calibration progress
        left_col = ttk.Frame(settings_frame)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        mode_labelframe = ttk.LabelFrame(left_col, text="Mode", padding=(8, 4))
        mode_labelframe.grid(row=0, column=0, sticky="ew")
        self.mode_radiobuttons = []
        last_kit_idx = 0
        for kit_idx, kit in enumerate(quantification_kits):
            rb = ttk.Radiobutton(mode_labelframe, text=kit.name, value=kit_idx, variable=self.mode)
            rb.grid(row=kit_idx, column=0, sticky="w")
            self.mode_radiobuttons.append(rb)
            last_kit_idx = kit_idx
        fluoro_rb = ttk.Radiobutton(mode_labelframe, text="Fluorometer",
                                     value=self._FLUOROMETER_MODE, variable=self.mode)
        fluoro_rb.grid(row=last_kit_idx + 1, column=0, sticky="w")
        self.mode_radiobuttons.append(fluoro_rb)

        # Calibration progress bar (hidden in Fluorometer mode)
        self.calibration_frame = ttk.LabelFrame(left_col, text="Calibration", padding=(8, 4))
        self.calibration_frame.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.calibration_progress = ttk.Progressbar(
            self.calibration_frame, orient="horizontal", mode="determinate", length=110)
        self.calibration_progress.grid(row=0, column=0, sticky="ew")
        self.calibration_step_label = ttk.Label(
            self.calibration_frame, text="Step 0 / 0", style="Progress.TLabel")
        self.calibration_step_label.grid(row=0, column=1, padx=(8, 0))
        self.calibration_frame.columnconfigure(0, weight=1)

        # Right sub-column: Device settings + status
        device_frame = ttk.LabelFrame(settings_frame, text="Settings", padding=(8, 6))
        device_frame.grid(row=0, column=1, sticky="nsew")

        # COM port row with status dot and refresh button
        com_row = ttk.Frame(device_frame)
        com_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Label(com_row, text="COM Port:").grid(row=0, column=0, sticky="w")
        self.com_port_combobox = ttk.Combobox(com_row, textvariable=self.selected_com_port, width=14)
        self.com_port_combobox.grid(row=0, column=1, padx=(6, 4), sticky="ew")

        # Connection status dot
        self.status_canvas = tk.Canvas(com_row, width=14, height=14,
                                        highlightthickness=0, background=_BG)
        self.status_canvas.grid(row=0, column=2)
        self.status_oval = self.status_canvas.create_oval(2, 2, 12, 12, fill=_ORANGE, outline="")
        ToolTip(self.status_canvas,
                "Connection status:\n"
                "Orange = DEMO mode (no device)\n"
                "Grey = port selected, not yet tested\n"
                "Green = last measurement succeeded\n"
                "Red = last measurement failed")

        # Refresh COM port list button
        self.refresh_button = ttk.Button(com_row, text="↻", width=3,
                                          command=self.refresh_com_ports)
        self.refresh_button.grid(row=0, column=3, padx=(4, 0))
        ToolTip(self.refresh_button, "Refresh the list of available COM ports")
        com_row.columnconfigure(1, weight=1)

        # Sample input
        ttk.Label(device_frame, text="Sample Input (μL):").grid(
            row=1, column=0, sticky="w", pady=(4, 0))
        self.sample_input_entry = ttk.Entry(
            device_frame, textvariable=self.sample_input, width=8,
            validate='all', validatecommand=(
                self.register(self._generate_float_validator(self.sample_input, clamp_min=0)),
                '%P', '%V'))
        self.sample_input_entry.grid(row=1, column=1, sticky="ew", pady=(4, 0), padx=(6, 0))
        ToolTip(self.sample_input_entry,
                "Volume of sample added to the assay tube (μL).\n"
                "Used to back-calculate the original sample concentration.")

        # Known concentration (fluorometer mode only)
        self.known_concentration_label = ttk.Label(device_frame, text="Known Concentration (ng/μL):")
        self.known_concentration_label.grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.known_concentration_entry = ttk.Entry(
            device_frame, textvariable=self.known_concentration, state='disabled', width=8,
            validate='all', validatecommand=(
                self.register(self._generate_float_validator(self.known_concentration, clamp_min=0)),
                '%P', '%V'))
        self.known_concentration_entry.grid(row=2, column=1, sticky="ew", pady=(4, 0), padx=(6, 0))
        ToolTip(self.known_concentration_entry,
                "Known concentration of the sample — used in Fluorometer mode to\n"
                "build a custom calibration curve.")

        # LED power
        led_power_label = ttk.Label(device_frame, text="LED Power (%):")
        led_power_label.grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.led_power_scale = ttk.Spinbox(
            device_frame, from_=0, to=100, width=8, textvariable=self.led_power,
            validate='all', validatecommand=(
                self.register(self._generate_float_validator(self.led_power,
                                                              clamp_min=0, clamp_max=100)),
                '%P', '%V'),
            state='disabled')
        self.led_power_scale.grid(row=3, column=1, sticky="ew", pady=(4, 0), padx=(6, 0))
        ToolTip(self.led_power_scale,
                "LED excitation intensity (0–100 %).\n"
                "Only adjustable in Fluorometer mode; fixed at 100 % for kit modes.")

        # Instruction / status text
        self.current_step_label = ttk.Label(
            device_frame, textvariable=self.current_step_text,
            style="Instruction.TLabel", anchor='center', wraplength=260)
        self.current_step_label.grid(row=4, column=0, columnspan=2,
                                      sticky="ew", pady=(10, 0))

        device_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(1, weight=1)

        # ── Row 3: Controls + prominent result display ─────────────────────────
        control_frame = ttk.Frame(self, padding=(6, 8, 6, 4))
        control_frame.grid(row=3, column=0, columnspan=2, sticky="ew")

        self.measure_button = ttk.Button(control_frame, text="Measure",
                                          style="Primary.TButton", command=self._do_measure)
        self.restart_button = ttk.Button(control_frame, text="Restart", command=self._do_restart)
        self.save_button    = ttk.Button(control_frame, text="Save",    command=self._do_save)
        self.measure_button.grid(row=0, column=0, padx=(0, 6))
        self.restart_button.grid(row=0, column=1, padx=(0, 6))
        self.save_button.grid(row=0, column=2)
        ToolTip(self.measure_button, "Take a fluorescence measurement from the device")
        ToolTip(self.restart_button, "Discard all current measurements and restart from the beginning")
        ToolTip(self.save_button,    "Export all measurements to a CSV file")

        # Spacer pushes result box to the right
        spacer = ttk.Frame(control_frame)
        spacer.grid(row=0, column=3)
        control_frame.columnconfigure(3, weight=1)

        # Prominent result display box
        result_border = tk.Frame(control_frame, background=_BLUE_LIGHT,
                                  relief="groove", borderwidth=2)
        result_border.grid(row=0, column=4, sticky="e", padx=(10, 0))
        result_inner = tk.Frame(result_border, background="white", padx=14, pady=6)
        result_inner.pack(fill="both", expand=True, padx=2, pady=2)

        ttk.Label(result_inner, textvariable=self.measured_concentration_label_string,
                  style="ResultTitle.TLabel").pack(anchor="center")
        value_row = tk.Frame(result_inner, background="white")
        value_row.pack()
        ttk.Label(value_row, textvariable=self.measured_concentration_string,
                  style="Result.TLabel").pack(side="left")
        ttk.Label(value_row, textvariable=self.measured_concentration_units_string,
                  style="ResultUnit.TLabel").pack(side="left", padx=(6, 0), anchor="s")

        # ── Row 4: Measurement history table ──────────────────────────────────
        history_frame = ttk.LabelFrame(self, text="Measurement History", padding=(6, 4))
        history_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=6, pady=(4, 6))

        cols = ("type", "index", "fluorescence", "concentration", "input")
        self.history_tree = ttk.Treeview(history_frame, columns=cols,
                                          show="headings", height=4)
        self.history_tree.heading("type",          text="Type")
        self.history_tree.heading("index",         text="#")
        self.history_tree.heading("fluorescence",  text="Fluorescence (arb.)")
        self.history_tree.heading("concentration", text="Concentration")
        self.history_tree.heading("input",         text="Input (μL)")
        self.history_tree.column("type",          width=80,  minwidth=70,  stretch=False)
        self.history_tree.column("index",         width=35,  minwidth=30,  stretch=False)
        self.history_tree.column("fluorescence",  width=160, minwidth=120, stretch=True)
        self.history_tree.column("concentration", width=180, minwidth=140, stretch=True)
        self.history_tree.column("input",         width=90,  minwidth=70,  stretch=False)

        history_scroll = ttk.Scrollbar(history_frame, orient="vertical",
                                        command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        history_scroll.grid(row=0, column=1, sticky="ns")
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        # ── Global grid weights ────────────────────────────────────────────────
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    def refresh_com_ports(self):
        """Refresh the COM port dropdown, defaulting to DEMO if none are available."""
        self._refreshing_ports = True
        try:
            current = self.selected_com_port.get()
            ports = [port.device for port in serial.tools.list_ports.comports()]
            ports.append(Fluorometer.DEMO_PORT)
            if current not in ports:
                current = Fluorometer.DEMO_PORT
            self.selected_com_port.set(current)
            self.com_port_combobox['values'] = ports
        finally:
            self._refreshing_ports = False
        port = self.selected_com_port.get()
        self._update_status_dot("demo" if port == Fluorometer.DEMO_PORT else self._connection_status)

    def sync_model(self):
        """Synchronise all UI elements to the current model state."""

        # ── Instruction label ────────────────────────────────────────────────
        self.current_step_text.set(self.model.current_instruction)
        self.current_step_label.config(
            style="Error.Instruction.TLabel" if self.model.error else "Instruction.TLabel"
        )

        # ── Result display ───────────────────────────────────────────────────
        if self.mode.get() == self._FLUOROMETER_MODE:
            val = self.model.measurements[-1] if self.model.measurements else None
        else:
            val = self.model.sample_concentrations[-1] if self.model.sample_concentrations else None
        self.measured_concentration_string.set(f"{val:.4f}" if val is not None else "—")
        self.measured_concentration_units_string.set(self.model.units)
        self.known_concentration_label.config(
            text=f"Known Concentration ({self.model.units}):")

        # ── Calibration progress ─────────────────────────────────────────────
        if self.mode.get() != self._FLUOROMETER_MODE:
            total = len(self._current_kit_standards())
            done  = len(self.model.standard_measurements)
            self.calibration_progress['value'] = (done / total * 100) if total > 0 else 100
            if done >= total:
                self.calibration_step_label.config(text="Complete ✓")
            else:
                self.calibration_step_label.config(text=f"Step {done + 1} / {total}")

        # ── History table ────────────────────────────────────────────────────
        self.history_tree.delete(*self.history_tree.get_children())
        units = self.model.units
        self.history_tree.heading("concentration", text=f"Concentration ({units})")

        for i, (m, tc) in enumerate(zip(self.model.standard_measurements,
                                         self.model.standard_concentrations)):
            self.history_tree.insert("", "end", tags=("standard",),
                                      values=("Standard", i + 1, f"{m:.1f}", f"{tc:.4f}", "—"))

        if self.mode.get() == self._FLUOROMETER_MODE:
            for i, (m, tc) in enumerate(zip(self.model.measurements,
                                             self.model.tube_concentrations)):
                self.history_tree.insert("", "end", tags=("sample",),
                                          values=("Sample", i + 1, f"{m:.1f}", f"{tc:.4f}", "—"))
        else:
            for i, (m, sc, si) in enumerate(zip(self.model.measurements,
                                                  self.model.sample_concentrations,
                                                  self.model.sample_inputs)):
                self.history_tree.insert("", "end", tags=("sample",),
                                          values=("Sample", i + 1, f"{m:.1f}", f"{sc:.4f}", f"{si:.2f}"))

        self.history_tree.tag_configure("standard", foreground=_GREEN)
        self.history_tree.tag_configure("sample",   foreground=_BLUE)

        # ── Plot ─────────────────────────────────────────────────────────────
        ax = self.plot_ax
        ax.clear()
        ax.set_facecolor("white")
        ax.grid(True, color="#E0E0E0", linewidth=0.7, zorder=0)
        for spine in ax.spines.values():
            spine.set_edgecolor("#CFD8DC")

        if self.model.standard_concentrations:
            ax.plot(self.model.standard_concentrations, self.model.standard_measurements,
                    'o', color=_GREEN, markersize=8, label="Standards", zorder=3)
        curve_x, curve_y = self.model.generate_fitting_curve()
        if len(curve_x):
            ax.plot(curve_x, curve_y, '--', color=_GREY, linewidth=1.5, zorder=2)
        if self.model.tube_concentrations:
            ax.plot(self.model.tube_concentrations, self.model.measurements,
                    'o', color=_BLUE, markersize=8, label="Samples", zorder=3)
        if self.model.standard_concentrations or self.model.tube_concentrations:
            ax.legend(fontsize=9, framealpha=0.9)

        ax.set_xlabel(f"Tube Concentration ({self.model.units})", fontsize=10)
        ax.set_ylabel("Fluorescence (arb. units)", fontsize=10)
        ax.set_title("Fluorescence Measurements", fontsize=11,
                     fontweight='bold', color="#37474F")
        ax.tick_params(labelsize=9)
        self.fig_canvas.draw()


if __name__ == "__main__":
    # Mark process as DPI-aware on Windows before rendering any GUI elements (not needed on Linux/macOS)
    if sys.platform == 'win32' and int(platform.release()) >= 8:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)

    # Run GUI main loop
    root = FluorometerUI()

    # If we're running in a pyinstaller bundle, close the splash screen when the GUI is ready
    try:
        import pyi_splash
        root.after_idle(pyi_splash.close)
    except ImportError:
        pass

    root.mainloop()
