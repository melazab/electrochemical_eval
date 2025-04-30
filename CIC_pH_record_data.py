#!/user/bin/python3

"""
CIC_pH_record_data.py uses the UnifiedDataCollector class for combined pH and CIC measurements
with real-time visualization of measurements.
"""

import time

from unified_data_collector import UnifiedDataCollector
from waveform_parameters import waveformParameters


def main():
    print("Initializing data collection system...")
    # Initialize the unified data collector
    collector = UnifiedDataCollector(use_ph_meter=True, use_keithley=True)
    collector.initialize_instruments()

    try:
        # Configure Keithley similar to your CIC code
        if collector.keithley:
            collector.keithley.write("smu.source.func = smu.FUNC_DC_CURRENT")
            collector.keithley.write("smu.measure.func = smu.FUNC_DC_VOLTAGE")
            collector.keithley.write("smu.measure.sense = smu.SENSE_4WIRE")
            collector.keithley.write("smu.source.readback = smu.ON")
            collector.keithley.write(
                f"smu.source.vlimit.level = {waveformParameters['complianceVoltage']}"
            )
            collector.keithley.write("timer.cleartime()")
            print("Keithley configured successfully")

        print("\nStarting measurement with real-time visualization...")
        print("Close the plot window or press Ctrl+C to stop the measurement")

        # Run the biphasic current pulse train while collecting pH data
        for cycle in range(waveformParameters["numPulses"]):
            print(f"\nExecuting cycle {cycle + 1}/{waveformParameters['numPulses']}")

            # Start with anodic phase if anodicFirst is True
            if waveformParameters["anodicFirst"]:
                current_value = waveformParameters["currentAmplitude"]["anodic"]
                print("Starting anodic phase...")
            else:
                current_value = waveformParameters["currentAmplitude"]["cathodic"]
                print("Starting cathodic phase...")

            if collector.keithley:
                collector.keithley.write(f"smu.source.level = {current_value}")
                collector.keithley.write("smu.source.output = smu.ON")

            # Collect data during first pulse
            start_time = time.time()
            while (time.time() - start_time) < waveformParameters["pulseWidth"][
                "anodic"
            ] and collector.experiment_running:
                collector.collect_data_point(cycle_number=cycle + 1)
                time.sleep(0.1)  # Adjust sampling rate as needed

            # Check if experiment was aborted
            if not collector.experiment_running:
                break

            # Switch to opposite phase
            if waveformParameters["anodicFirst"]:
                current_value = waveformParameters["currentAmplitude"]["cathodic"]
                print("Switching to cathodic phase...")
            else:
                current_value = waveformParameters["currentAmplitude"]["anodic"]
                print("Switching to anodic phase...")

            if collector.keithley:
                collector.keithley.write(f"smu.source.level = {current_value}")

            # Collect data during second phase
            start_time = time.time()
            while (time.time() - start_time) < waveformParameters["pulseWidth"][
                "cathodic"
            ] and collector.experiment_running:
                collector.collect_data_point(cycle_number=cycle + 1)
                time.sleep(0.1)

            # Check if experiment was aborted
            if not collector.experiment_running:
                break

            # Inter-pulse interval
            if collector.keithley:
                collector.keithley.write("smu.source.level = 0")

            print("Inter-pulse interval...")
            start_time = time.time()
            while (time.time() - start_time) < waveformParameters[
                "interPulseInterval"
            ] and collector.experiment_running:
                collector.collect_data_point(cycle_number=cycle + 1)
                time.sleep(0.1)

            # Check if experiment was aborted
            if not collector.experiment_running:
                break

        print("\nMeasurement complete!")
        # Export the collected data
        collector.export_data("combined_CIC_pH_anodic_test_1")
        print("Data exported successfully")

    except KeyboardInterrupt:
        print("\nMeasurement interrupted by user")

    finally:
        print("\nClosing connections and saving final plot...")
        collector.close()
        print("Done!")


if __name__ == "__main__":
    main()
