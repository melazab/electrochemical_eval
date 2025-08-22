#!/usr/bin/env python3

"""
CIC_pH_record_data.py uses the UnifiedDataCollector class for combined pH and CIC measurements
with real-time visualization of measurements.
"""

import time

from data_collector import DataCollector, Keithley, Sper
from experimental_configs import keithleyOptions, sperOptions, waveformParameters


def main():
    print("Initializing data collection system...")
    # Initialize the unified data collector
    collector = DataCollector(use_ph_meter=True, use_keithley=True)
    collector.initialize_instruments(sperOptions, keithleyOptions)

    try:
        # Configure Keithley similar to your CIC code
        if collector.use_keithley:
            collector.keithley.write(
                f"smu.source.vlimit.level = {waveformParameters['complianceVoltage']}"
            )
            collector.keithley.write("timer.cleartime()")

        print("\nStarting measurement with real-time visualization...")
        print("Close the plot window or press Ctrl+C to stop the measurement")

        # Run the biphasic current pulse train while collecting pH data
        for cycle in range(waveformParameters["numPulses"]):
            print(f"\nExecuting cycle {cycle + 1}/{waveformParameters['numPulses']}")

            # Start with anodic phase if anodicFirst is True
            if waveformParameters["anodicFirst"]:
                current_value = waveformParameters["currentAmplitude"]["anodic"]
            else:
                current_value = waveformParameters["currentAmplitude"]["cathodic"]

            if collector.keithley:
                collector.keithley.write(f"smu.source.level = {current_value}")
                collector.keithley.write("smu.source.output = smu.ON")

            # Collect data during first pulse
            start_time = time.time()
            while (time.time() - start_time) < waveformParameters["pulseWidth"][
                "anodic"
            ] and collector.experiment_running:
                collector.collect_data_point(cycle_number=cycle + 1)

            # Check if experiment was aborted
            if not collector.experiment_running:
                break

            # Switch to opposite phase
            if waveformParameters["anodicFirst"]:
                current_value = waveformParameters["currentAmplitude"]["cathodic"]
            else:
                current_value = waveformParameters["currentAmplitude"]["anodic"]

            if collector.keithley:
                collector.keithley.write(f"smu.source.level = {current_value}")

            # Collect data during second phase
            start_time = time.time()
            while (time.time() - start_time) < waveformParameters["pulseWidth"][
                "cathodic"
            ] and collector.experiment_running:
                collector.collect_data_point(cycle_number=cycle + 1)

            # Check if experiment was aborted
            if not collector.experiment_running:
                break

            # Inter-pulse interval
            if collector.keithley:
                collector.keithley.write("smu.source.level = 0")

            start_time = time.time()
            while (time.time() - start_time) < waveformParameters[
                "interPulseInterval"
            ] and collector.experiment_running:
                collector.collect_data_point(cycle_number=cycle + 1)

            # Check if experiment was aborted
            if not collector.experiment_running:
                break

        print("\nMeasurement complete!")
        # Export the collected data
        trial_name = "data_trial"
        collector.export_data(trial_name)
        print("Data exported successfully")

    except KeyboardInterrupt:
        print("\nMeasurement interrupted by user")

    finally:
        print("\nClosing connections and saving final plot...")
        collector.close()
        print("Done!")


if __name__ == "__main__":
    main()
