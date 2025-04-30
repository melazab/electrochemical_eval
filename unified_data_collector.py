"""
Unified Data Collection Module for CIC and pH Measurements
--------------------------------------------------------
This module combines functionality from the CIC testing and pH measurement systems,
allowing simultaneous data collection and unified export format.

Date: 01/14/2025
"""

import pyvisa
import re
import time
from pathlib import Path
from datetime import datetime
import numpy as np
from typing import Optional, Dict, Tuple, List
import csv
import os
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


class UnifiedDataCollector:
    def __init__(self, use_ph_meter: bool = True, use_keithley: bool = True):
        """
        Initialize the unified data collection system.

        Parameters:
        use_ph_meter (bool): Whether to enable pH meter readings
        use_keithley (bool): Whether to enable Keithley measurements
        """
        self.use_ph_meter = use_ph_meter
        self.use_keithley = use_keithley
        self.ph_meter = None
        self.keithley = None
        self.data_buffer = []
        self.experiment_running = True
        self.data_saved = False

        # Initialize real-time plotting
        plt.ion()
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # Setup current/voltage plot
        self.ax1_twin = self.ax1.twinx()  # Create twin axis first
        (self.voltage_line,) = self.ax1.plot([], [], "b-", label="Voltage")
        (self.current_line,) = self.ax1_twin.plot(
            [], [], "r-", label="Current"
        )  # Plot current on twin axis

        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("Measured Voltage (V)", color="b", weight="bold")
        self.ax1_twin.set_ylabel("Current Output (mA)", color="r", weight="bold")
        self.ax1.grid(True)

        # Setup pH/temperature plot
        self.ax2_twin = self.ax2.twinx()
        (self.ph_line,) = self.ax2.plot([], [], "b-", label="pH")
        (self.temp_line,) = self.ax2_twin.plot([], [], "r-", label="Temperature")

        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel("pH", color="b", weight="bold")
        self.ax2.tick_params(axis="y", labelcolor="b")
        self.ax2_twin.set_ylabel("Temperature (°C)", color="r", weight="bold")
        self.ax2_twin.tick_params(axis="y", labelcolor="r")
        self.ax2.grid(True)

        # Add legends
        lines1 = [self.voltage_line, self.current_line]
        labels1 = ["Voltage", "Current"]
        self.ax1.legend(lines1, labels1, loc="upper left")

        lines2 = [self.ph_line, self.temp_line]
        labels2 = ["pH", "Temperature"]
        self.ax2.legend(lines2, labels2, loc="upper left")

        # Add close event handler
        self.fig.canvas.mpl_connect("close_event", self.on_close)

        # Add padding to the layout and show the plot
        plt.tight_layout()
        self.fig.show()
        plt.pause(0.1)

    def initialize_instruments(self):
        """Initialize all enabled instruments."""
        rm = pyvisa.ResourceManager()

        if self.use_ph_meter:
            try:
                # Initialize pH meter (assuming ASRL4::INSTR is the pH meter)
                self.ph_meter = rm.open_resource("ASRL4::INSTR")
                self.ph_meter.baud_rate = 9600
                self.ph_meter.data_bits = 8
                self.ph_meter.parity = pyvisa.constants.Parity.none
                self.ph_meter.stop_bits = pyvisa.constants.StopBits.one
                self.ph_meter.timeout = 5000
                self.ph_meter.read_termination = "\n"
                print("pH meter initialized successfully")
            except Exception as e:
                print(f"Error initializing pH meter: {e}")
                self.use_ph_meter = False

        if self.use_keithley:
            try:
                # Try to open with alias first
                try:
                    self.keithley = rm.open_resource("Keithley2450_CWRU")
                except:
                    # Fall back to first available resource if alias not found
                    self.keithley = rm.open_resource(rm.list_resources()[0])

                self.keithley.read_termination = self.keithley.write_termination = "\n"
                self.keithley.write("reset()")
                self.keithley.write("defbuffer1.clear()")
                print("Keithley initialized successfully")
            except Exception as e:
                print(f"Error initializing Keithley: {e}")
                self.use_keithley = False

    def read_ph_data(self) -> Optional[Dict]:
        """Read data from pH meter and return parsed values."""
        if not self.use_ph_meter or self.ph_meter is None:
            return None

        try:
            raw_data = self.ph_meter.read()
            cleaned_data = "".join(c for c in raw_data if c.isprintable())

            # Regular expression to match the meter's output format
            pattern = r"p(\d+\.\d+).*?m([-+]?\d+\.\d+)mV.*?T(\d+\.\d+)C.*?@(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
            match = re.search(pattern, cleaned_data)

            if match:
                return {
                    "pH": float(match.group(1)),
                    "temperature": float(match.group(3)),
                    "timestamp": match.group(4),
                }
        except Exception as e:
            print(f"Error reading pH data: {e}")
        return None

    def read_keithley_data(self) -> Optional[Dict]:
        """Read data from Keithley and return parsed values."""
        if not self.use_keithley or self.keithley is None:
            return None

        try:
            self.keithley.write("smu.measure.read(defbuffer1)")
            measurement = float(
                self.keithley.query("print(defbuffer1.readings[defbuffer1.n])")
            )
            source = float(
                self.keithley.query("print(defbuffer1.sourcevalues[defbuffer1.n])")
            )
            elapsed_time = float(self.keithley.query("print(timer.gettime())"))

            return {
                "voltage": measurement,
                "current": source,
                "elapsed_time": elapsed_time,
            }
        except Exception as e:
            print(f"Error reading Keithley data: {e}")
        return None

    def collect_data_point(self, cycle_number: Optional[int] = None) -> Dict:
        """Collect a single data point from all enabled instruments."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_point = {"absolute_time": timestamp}

        # Get pH meter data
        ph_data = self.read_ph_data()
        if ph_data:
            data_point.update(
                {"pH": ph_data["pH"], "temperature": ph_data["temperature"]}
            )
        else:
            data_point.update({"pH": None, "temperature": None})

        # Get Keithley data
        keithley_data = self.read_keithley_data()
        if keithley_data:
            data_point.update(
                {
                    "voltage": keithley_data["voltage"],
                    "current": keithley_data["current"],
                    "elapsed_time": keithley_data["elapsed_time"],
                }
            )
        else:
            data_point.update({"voltage": None, "current": None, "elapsed_time": None})

        if cycle_number is not None:
            data_point["cycle_number"] = cycle_number

        self.data_buffer.append(data_point)
        self.update_plots()
        return data_point

    def update_plots(self):
        """Update real-time plots with current data."""
        try:
            times = []
            voltages = []
            currents = []
            phs = []
            temps = []

            for d in self.data_buffer:
                if d["elapsed_time"] is not None:
                    t = d["elapsed_time"]
                    if d["voltage"] is not None and d["current"] is not None:
                        times.append(t)
                        voltages.append(d["voltage"])
                        currents.append(d["current"] * 1000)  # Multiply by 1000 for mA

                    if d["pH"] is not None:
                        phs.append((t, d["pH"]))
                    if d["temperature"] is not None:
                        temps.append((t, d["temperature"]))

            if times:
                self.voltage_line.set_data(times, voltages)
                self.current_line.set_data(times, currents)

                # Update primary (voltage) axis
                self.ax1.relim()
                self.ax1.autoscale_view()

                # Update secondary (current) axis
                self.ax1_twin.relim()
                self.ax1_twin.autoscale_view()

            if phs:
                ph_times, ph_values = zip(*phs)
                self.ph_line.set_data(ph_times, ph_values)
                self.ax2.relim()
                self.ax2.autoscale_view()

            if temps:
                temp_times, temp_values = zip(*temps)
                self.temp_line.set_data(temp_times, temp_values)
                self.ax2_twin.relim()
                self.ax2_twin.autoscale_view()

            self.fig.canvas.draw()
            self.fig.canvas.flush_events()

        except Exception as e:
            print(f"Error updating plots: {e}")

    def export_data(self, filename: str):
        """Export collected data to CSV file and save plot."""
        if self.data_saved:  # Skip if data has already been saved
            return

        # Create directory structure
        data_repository_path = (
            Path.home()
            / "Box/Electrical Nerve Block Institute/Data/ElectrodeTesting/STTR/"
        )
        session_path = data_repository_path / datetime.now().strftime("%Y-%m-%d")
        session_path.mkdir(parents=True, exist_ok=True)

        # Save data
        timestamp = datetime.now().strftime("%H_%M_%S")
        base_name = f"{filename}_{timestamp}"
        csv_filename = session_path / f"{base_name}.csv"
        plot_filename = session_path / f"{base_name}.png"

        headers = [
            "absolute_time",
            "elapsed_time",
            "current",
            "voltage",
            "pH",
            "temperature",
            "cycle_number",
        ]

        with open(csv_filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for data_point in self.data_buffer:
                writer.writerow({h: data_point.get(h, "") for h in headers})

        # Save plot
        self.fig.savefig(plot_filename)
        print(f"Data exported to: {csv_filename}")
        print(f"Plot saved to: {plot_filename}")

        self.data_saved = True  # Mark data as saved

    def on_close(self, event):
        """Handle window close event"""
        print("\nPlot window closed. Stopping experiment...")
        self.experiment_running = False

        # Turn off Keithley output
        if self.keithley:
            try:
                self.keithley.write("smu.source.output = smu.OFF")
                print("Keithley output turned off")
            except Exception as e:
                print(f"Error turning off Keithley: {e}")

        # Close resources
        try:
            self.close()
        except Exception as e:
            print(f"Error during close: {e}")

        # Export data only if we have data and haven't already saved it
        if self.data_buffer and not self.data_saved:
            try:
                self.export_data("combined_CIC_pH_cathodic_trial02_-4mA")

            except Exception as e:
                print(f"Error during export: {e}")

        # Exit the program
        import sys

        sys.exit(0)

    def close(self):
        """Close all instrument connections."""
        if self.ph_meter:
            try:
                self.ph_meter.close()
            except:
                pass

        if self.keithley:
            try:
                self.keithley.write("smu.source.output = smu.OFF")
                self.keithley.write("defbuffer1.clear()")
                self.keithley.close()
            except:
                pass
