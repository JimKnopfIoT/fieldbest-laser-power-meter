"""Minimal driver for the FieldBest II laser power meter over USB.

The meter enumerates as an STM32 virtual COM port (VID:PID 0483:5740); no
vendor driver is needed on Windows 10/11 or Linux (/dev/ttyACM*).
Protocol: send the four ASCII bytes b"?pw%" (no line ending); the meter
answers with the current reading in watts, e.g. b"0.340\\x00\\n".
The baud rate is ignored on the USB link.
"""
import serial
from serial.tools import list_ports

VID, PID = 0x0483, 0x5740


def find_port():
    """Return the first serial port that looks like a FieldBest meter, or None."""
    for p in list_ports.comports():
        if p.vid == VID and p.pid == PID:
            return p.device
    return None


class FieldBest:
    def __init__(self, port=None, timeout=0.3):
        port = port or find_port()
        if not port:
            raise RuntimeError("no FieldBest meter found (USB 0483:5740); pass the port explicitly")
        self.port = port
        self.s = serial.Serial(port, 9600, timeout=timeout)

    def read_watts(self, settle=0.25):
        """Query one reading. Returns float watts, or None if the reply was unusable."""
        import time
        self.s.reset_input_buffer()
        self.s.write(b"?pw%")
        time.sleep(settle)
        raw = self.s.read(64).replace(b"\x00", b"").strip()
        try:
            return float(raw.split()[0])
        except (ValueError, IndexError):
            return None

    def close(self):
        self.s.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


if __name__ == "__main__":
    import sys
    with FieldBest(sys.argv[1] if len(sys.argv) > 1 else None) as fb:
        print(f"{fb.port}: {fb.read_watts()} W")
