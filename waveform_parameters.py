NUM_PULSES = 1
INTER_PULSE_INTERVAL = 2
INTER_PHASE_DELAY = 0  # TODO: interphase delays are NOT IMPLEMENTED YET
CATHODIC_PULSE_WIDTH = 120 
ANODIC_PULSE_WIDTH = 3600
CATHODIC_CURRENT_AMPLITUDE = 0e-3
ANODIC_CURRENT_AMPLITUDE = 4e-3
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
