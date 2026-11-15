"""Fire timed power steps on a BJJCZ/LMC galvo controller while a FieldBest logs.

Example for automated power series on a galvo marker. Draws a
filled disk (Archimedean spiral out and back, laser on without jumps or pauses)
in the field centre, so the whole beam stays inside the meter's 18 mm aperture.
Each step: ON_S seconds laser on, OFF_S seconds off. The printed END time of a
step is reliable (the controller buffers the list, so the script waits until it
is really done); evaluate the last ~20 s before that end.

Needs: pip install galvoplotter pyusb libusb-package
Controller commands mirror what LightBurn sends: 800A = 1e4/f_kHz,
801E = 800A/5 (twice), 800B = Q-pulse[ns] * 20.

Env: FREQS (20) kHz list, QPS (10) ns list (every freq x every qp), ON_S (40),
     OFF_S (20), D_MM (5), SPEED (100 mm/s), PITCH (0.1 mm),
     FIELD_MM (field size the controller's 0..65535 range spans).
A file named STOP next to the script aborts at once (laser off).
Example: FREQS=20,25,30,40 QPS=2 python galvo_power_steps.py > steps.txt

Laser safety: wear goggles for the wavelength, keep the enclosure closed, and
defocus the beam on the absorber - a focused ns spot can damage the coating.
"""
import math, os, time
import usb.core, libusb_package
_find = usb.core.find
usb.core.find = lambda *a, **k: _find(*a, backend=libusb_package.get_libusb1_backend(), **k)
from galvo.controller import GalvoController

HERE = os.path.dirname(os.path.abspath(__file__)); STOP = os.path.join(HERE, "STOP")
FREQS = [float(x) for x in os.environ.get("FREQS", "20").split(",")]
QPS = [float(x) for x in os.environ.get("QPS", "10").split(",")]
ON_S = float(os.environ.get("ON_S", "40")); OFF_S = float(os.environ.get("OFF_S", "20"))
R = float(os.environ.get("D_MM", "5")) / 2; SPEED = float(os.environ.get("SPEED", "100"))
PITCH = float(os.environ.get("PITCH", "0.1")); GPM = 0x10000 / float(os.environ.get("FIELD_MM", "365")); C = 0x8000

# Archimedean spiral r = PITCH*theta/2pi, points every ~0.2 mm
pts, th = [], 0.0
while True:
    r = PITCH * th / (2 * math.pi)
    if r > R: break
    pts.append((r * math.cos(th), r * math.sin(th)))
    th += min(0.5, 0.2 / max(r, 0.05))
cyc = pts + pts[::-1][1:]
L = sum(math.dist(a, b) for a, b in zip(cyc, cyc[1:]))
n = max(1, round(ON_S * SPEED / L))
g = lambda p: (int(C + p[0] * GPM), int(C + p[1] * GPM))
print(f"disk {2*R:g} mm, path {L:.0f} mm/cycle, {n} cycles = {n*L/SPEED:.1f} s per step at {SPEED:g} mm/s", flush=True)

c = GalvoController(galvos_per_mm=GPM, mark_speed=SPEED, travel_speed=2000.0, power=None, frequency=None, usb_log=lambda m: None)
c.connect_if_needed()
try:
    for F in FREQS:
        for qp in QPS:
            if os.path.exists(STOP): raise KeyboardInterrupt
            mf = int(round(10000.0 / F))
            t0 = time.time()
            with c.marking():
                c.list_mark_frequency(mf)
                c.list_set_co2_fpk(int(round(mf / 5)), int(round(mf / 5)))
                c.list_mark_power_ratio(int(round(qp * 20)))
                c.goto(*g(cyc[0]))
                for _ in range(n):
                    for p in cyc[1:]:
                        c.mark(*g(p))
            while c.is_busy():  # controller buffers the list: wait until it has really finished
                if os.path.exists(STOP): c.abort(); raise KeyboardInterrupt
                time.sleep(0.1)
            t1 = time.time()
            print(f"{time.strftime('%H:%M:%S', time.localtime(t1 - n*L/SPEED))} - {time.strftime('%H:%M:%S', time.localtime(t1))}"
                  f"  {F:g} kHz  QP {qp:g} ns  (800A={mf}, 800B={round(qp*20)})", flush=True)
            for _ in range(int(OFF_S * 10)):
                if os.path.exists(STOP): raise KeyboardInterrupt
                time.sleep(0.1)
except KeyboardInterrupt:
    print("STOP", flush=True)
finally:
    try: c.abort()
    except Exception: pass
    c.port_off(bit=c.laser_pin); c.write_port(); c.disconnect()
    print(time.strftime("%H:%M:%S"), "laser off, disconnected", flush=True)
