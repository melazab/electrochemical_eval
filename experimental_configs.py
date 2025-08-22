# Experimental configuration
NUM_PULSES = 1
INTER_PULSE_INTERVAL = 20 * 60
INTER_PHASE_DELAY = 10  # TODO: interphase delays are NOT IMPLEMENTED YET
CATHODIC_PULSE_WIDTH = 60 * 60  # Pulse width in minutes
ANODIC_PULSE_WIDTH = 60 * 60  # Pulse width in minutes
CATHODIC_CURRENT_AMPLITUDE = -2e-3  # current in mA
ANODIC_CURRENT_AMPLITUDE = 2e-3
COMPLIANCE_VOLTAGE = 210
waveformParameters = {
    "numPulses": NUM_PULSES,
    "interPulseInterval": INTER_PULSE_INTERVAL,
    "interPhaseDelay": INTER_PHASE_DELAY,
    "pulseWidth": {"anodic": ANODIC_PULSE_WIDTH, "cathodic": CATHODIC_PULSE_WIDTH},
    "currentAmplitude": {
        "anodic": ANODIC_CURRENT_AMPLITUDE,
        "cathodic": CATHODIC_CURRENT_AMPLITUDE,
    },
    # BUG: cathodic first waveforms are not working properly. If you set anodicFirst
    # to false, it will not work - 01/22/2025
    "anodicFirst": True,
    "complianceVoltage": COMPLIANCE_VOLTAGE,
}


# Keithley configuration
SMU_ENABLE = "ON"
SOURCE_MODE = "FUNC_DC_CURRENT"
MEASURE_MODE = "FUNC_DC_VOLTAGE"
NPLC = 1  # number of power line cycles
SENSE = "SENSE_4_WIRE"
AMPLITUDE = 0
LIMIT = 210
RANGE = None
SMU_TIMEOUT_MS = 10000

keithleyOptions = {
    "enable": SMU_ENABLE,
    "source": {
        "func": SOURCE_MODE,
        "autorange": "ON",
        "readback": "ON",
        "level": AMPLITUDE,
    },
    "measure": {
        "func": MEASURE_MODE,
        "nplc": NPLC,
        "senseType": SENSE,
        "compliance": LIMIT,
    },
    "misc": {
        "timeout": SMU_TIMEOUT_MS,
        "writeTermination": "\n",
        "readTermination": "\n",
    },
}

# Sper configuration
PH_ENABLE = "ON"
BAUD = 9600
DATA_BITS = 8
PARITY = None
STOP_BITS = 1
PH_TIMEOUT_MS = 5000

sperOptions = {
    "enable": PH_ENABLE,
    "baudRate": BAUD,
    "dataBits": DATA_BITS,
    "parity": PARITY,
    "stopBits": STOP_BITS,
    "readTermination": "\r\n",
}
