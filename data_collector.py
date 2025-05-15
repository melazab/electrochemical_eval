#!/usr/bin/env python3
"""
Data Collection software for real-time CIC and pH measurements.
---------------------------------------------------------------
This module combines functionality from the Charge Injection
Capacity testing and pH measurement systems, allowing
simultaneous data collection and exporting.

Date: 05/01/2025
Mohamed Elazab
"""

import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pyvisa


class DataCollector:
    """Data Collector Class"""

    def __init__(self, use_ph_meter: bool = True, use_keithley: bool = True):
        """
        Initialize the data collection system.

        Parameters:
        use_ph_meter (bool): Whether to enable pH meter readings
        use_keithley (bool): Whether to enable Keithley measurements
        """
        # Check if at least one instrument is enabled
        if not (use_ph_meter or use_keithley):
            print("No instruments enabled. Exiting program.")
            sys.exit(0)

        self.use_ph_meter = use_ph_meter
        self.use_keithley = use_keithley
        self.ph_meter = None
        self.keithley = None
        self.data_buffer = []
        self.experiment_running = True
        self.data_saved = False

        # Initialize plots
        self._init_plots()

    def _init_plots(self):
        """Initialize plotting based on enabled instruments."""
        plt.ion()

        # Determine plot layout based on enabled instruments
        if self.use_ph_meter and self.use_keithley:
            self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
            self._setup_current_voltage_plot()
            self._setup_ph_temp_plot()
        elif self.use_keithley:
            self.fig, self.ax1 = plt.subplots(1, 1, figsize=(12, 5))
            self._setup_current_voltage_plot()
        elif self.use_ph_meter:
            self.fig, self.ax2 = plt.subplots(1, 1, figsize=(12, 5))
            self._setup_ph_temp_plot()

        # Add close event handler and display plot
        self.fig.canvas.mpl_connect("close_event", self.on_close)
        plt.tight_layout()
        self.fig.show()
        plt.pause(0.1)

    def _setup_current_voltage_plot(self):
        """Setup current and voltage plot."""
        self.ax1_twin = self.ax1.twinx()
        (self.voltage_line,) = self.ax1.plot([], [], "b-", label="Voltage")
        (self.current_line,) = self.ax1_twin.plot([], [], "r-", label="Current")

        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("Voltage (V)", color="b", weight="bold")
        self.ax1_twin.set_ylabel("Current (mA)", color="r", weight="bold")
        self.ax1.grid(True)

        # Add legend
        lines = [self.voltage_line, self.current_line]
        labels = ["Voltage", "Current"]
        self.ax1.legend(lines, labels, loc="upper left")

    def _setup_ph_temp_plot(self):
        """Setup pH and temperature plot."""
        self.ax2_twin = self.ax2.twinx()
        (self.ph_line,) = self.ax2.plot([], [], "b-", label="pH")
        (self.temp_line,) = self.ax2_twin.plot([], [], "r-", label="Temperature")

        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel("pH", color="b", weight="bold")
        self.ax2_twin.set_ylabel("Temperature (°C)", color="r", weight="bold")
        self.ax2.grid(True)

        # Add legend
        lines = [self.ph_line, self.temp_line]
        labels = ["pH", "Temperature"]
        self.ax2.legend(lines, labels, loc="upper left")

    def initialize_instruments(self):
        """Initialize all enabled instruments separately"""
        if self.use_ph_meter:
            self._initialize_ph_meter()

        if self.use_keithley:
            self._initialize_keithley()

    def _initialize_ph_meter(self):
        """Initialize pH meter"""
        try:
            rm = pyvisa.ResourceManager()
            # First, find the right serial port for pH meter
            ph_port = None
            for port in rm.list_resources():
                if "/dev/ttyUSB" in port:
                    ph_port = port
                    break

            if not ph_port:
                print("No serial ports found. Disabling pH measurements.")
                self.use_ph_meter = False
                return

            # Open and configure pH meter
            self.ph_meter = rm.open_resource(ph_port)
            self.ph_meter.baud_rate = 9600
            self.ph_meter.data_bits = 8
            self.ph_meter.parity = pyvisa.constants.Parity.none
            self.ph_meter.stop_bits = pyvisa.constants.StopBits.one
            self.ph_meter.timeout = 5000
            self.ph_meter.read_termination = "\r\n"

            # Flush the input buffer by reading a few times
            try:
                for _ in range(3):
                    self.ph_meter.read()
            except:
                pass  # Ignore errors during flushing

            print("pH meter initialized successfully")

        except Exception as e:
            print(f"Error initializing pH meter: {e}")
            self.use_ph_meter = False

    def _initialize_keithley(self):
        """Initialize Keithley source meter with PyVISA."""
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        for resource in resources:
            if resource.startswith("USB"):
                self.keithley = rm.open_resource(resource)

        # Configure Keithley
        self.keithley.write_termination = "\n"
        self.keithley.read_termination = "\n"
        self.keithley.timeout = 10000  # 10 seconds timeout
        self.keithley.write("reset()")
        self.keithley.write("defbuffer1.clear()")
        self.keithley.write("timer.reset()")

        # Configure source and measurement
        self.keithley.write("smu.source.func = smu.FUNC_DC_CURRENT")
        self.keithley.write("smu.source.autorange = smu.ON")
        self.keithley.write("smu.source.level = 0")
        self.keithley.write("smu.measure.func = smu.FUNC_DC_VOLTAGE")
        self.keithley.write("smu.measure.autorange = smu.ON")
        self.keithley.write("smu.measure.nplc = 1")
        self.keithley.write("smu.measure.sense = smu.SENSE_4WIRE")
        self.keithley.write("smu.source.readback = smu.ON")

    def read_ph_data(self) -> Optional[Dict]:
        """Read and parse pH meter data."""
        if not self.use_ph_meter or self.ph_meter is None:
            return None

        try:
            # Read until we get a valid reading, with a limit to avoid infinite loops
            for attempt in range(5):
                try:
                    raw_data = self.ph_meter.read()
                    if raw_data.startswith("$"):
                        continue  # Skip header lines

                    # Parse the pH and temperature values
                    ph_match = re.search(r"p(\d+\.\d+)", raw_data)
                    temp_match = re.search(r"T(\d+\.\d+)C", raw_data)

                    if ph_match and temp_match:
                        pH = float(ph_match.group(1))
                        temperature = float(temp_match.group(1))

                        return {
                            "pH": pH,
                            "temperature": temperature,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                except Exception as e:
                    print(f"Error parsing pH data (attempt {attempt+1}): {e}")

            # If we get here, we couldn't get a valid reading
            print("Failed to get valid pH reading after multiple attempts")

        except Exception as e:
            print(f"Error reading from pH meter: {e}")

        return None

    def read_keithley_data(self) -> Optional[Dict]:
        try:
            # Take a measurement
            self.keithley.write("smu.measure.read(defbuffer1)")

            voltage = float(
                self.keithley.query("print(defbuffer1.readings[defbuffer1.n])")
            )
            current = float(
                self.keithley.query("print(defbuffer1.sourcevalues[defbuffer1.n])")
            )
            elapsed_time = float(self.keithley.query("print(timer.gettime())"))

            return {
                "voltage": voltage,
                "current": current,
                "elapsed_time": elapsed_time,
            }
        except Exception as e:
            print(f"Error reading Keithley data: {e}")
            # Try to keep the connection alive
            try:
                self.keithley.write("*CLS")  # Clear status
            except:
                pass

        return None

    def collect_data_point(self, cycle_number: Optional[int] = None) -> Dict:
        """Collect a single data point from all enabled instruments."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_point = {"absolute_time": timestamp, "elapsed_time": time.time()}

        # Important: Read instruments separately to avoid cross-contamination
        # Get pH meter data first if enabled
        if self.use_ph_meter:
            ph_data = self.read_ph_data()
            if ph_data:
                data_point.update(
                    {"pH": ph_data["pH"], "temperature": ph_data["temperature"]}
                )
            else:
                data_point.update({"pH": None, "temperature": None})

        # Then get Keithley data if enabled
        if self.use_keithley:
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
                data_point.update({"voltage": None, "current": None})

        if cycle_number is not None:
            data_point["cycle_number"] = cycle_number

        # Add to data buffer and update plots
        self.data_buffer.append(data_point)
        self.update_plots()

        return data_point

    def update_plots(self):
        """Update real-time plots with current data."""
        try:
            if not self.data_buffer:
                return

            # Extract data for plotting
            times = []
            voltages = []
            currents = []
            ph_times = []
            ph_values = []
            temp_times = []
            temp_values = []

            # Get the start time for relative timing
            start_time = self.data_buffer[0]["elapsed_time"]

            for d in self.data_buffer:
                # Use relative time (seconds since start)
                t = d["elapsed_time"] - start_time

                # Extract voltage/current data
                if self.use_keithley and "voltage" in d and d["voltage"] is not None:
                    times.append(t)
                    voltages.append(d["voltage"])
                    currents.append(
                        d["current"] * 1000 if d["current"] is not None else 0
                    )  # Convert to mA

                # Extract pH/temperature data
                if self.use_ph_meter:
                    if "pH" in d and d["pH"] is not None:
                        ph_times.append(t)
                        ph_values.append(d["pH"])
                    if "temperature" in d and d["temperature"] is not None:
                        temp_times.append(t)
                        temp_values.append(d["temperature"])

            # Update voltage/current plot if data exists
            if self.use_keithley and times and hasattr(self, "voltage_line"):
                self.voltage_line.set_data(times, voltages)
                self.current_line.set_data(times, currents)
                self.ax1.relim()
                self.ax1.autoscale_view()
                self.ax1_twin.relim()
                self.ax1_twin.autoscale_view()

            # Update pH/temperature plot if data exists
            if self.use_ph_meter and ph_times and hasattr(self, "ph_line"):
                self.ph_line.set_data(ph_times, ph_values)
                self.temp_line.set_data(temp_times, temp_values)
                self.ax2.relim()
                self.ax2.autoscale_view()
                self.ax2_twin.relim()
                self.ax2_twin.autoscale_view()

            # Refresh the figure
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()

        except Exception as e:
            print(f"Error updating plots: {e}")

    def export_data(self, filename: str):
        """Export collected data to CSV file and save plot."""
        if not self.data_buffer:
            print("No data to export")
            return

        if self.data_saved:
            print("Data already saved")
            return

        # Create directory structure
        data_dir = Path.home() / "Documents/STTR_DATA"
        date_dir = data_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Create filenames with timestamp
        timestamp = datetime.now().strftime("%H_%M_%S")
        base_name = f"{filename}_{timestamp}"
        csv_file = date_dir / f"{base_name}.csv"
        plot_file = date_dir / f"{base_name}.png"

        # Save CSV data
        headers = [
            "absolute_time",
            "elapsed_time",
            "current",
            "voltage",
            "pH",
            "temperature",
            "cycle_number",
        ]

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for data_point in self.data_buffer:
                writer.writerow({h: data_point.get(h, "") for h in headers})

        # Save plot
        self.fig.savefig(plot_file)

        print(f"Data exported to: {csv_file}")
        print(f"Plot saved to: {plot_file}")
        self.data_saved = True

    def on_close(self, event):
        """Handle window close event."""
        print("\nPlot window closed. Stopping experiment...")
        self.experiment_running = False

        # Close instrument connections
        self.close()

        # Export data if needed
        if self.data_buffer and not self.data_saved:
            self.export_data("auto_saved_data")

        # Exit program
        sys.exit(0)

    def close(self):
        """Close all instrument connections."""
        if self.ph_meter:
            try:
                self.ph_meter.close()
                print("pH meter connection closed")
            except:
                pass

        if self.keithley:
            try:
                self.keithley.write("smu.source.output = smu.OFF")
                self.keithley.write("defbuffer1.clear()")
                self.keithley.close()
                print("Keithley connection closed")
            except:
                pass
