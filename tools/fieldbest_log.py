"""Log FieldBest readings to CSV (ISO timestamp, watts).

Usage:  python fieldbest_log.py [out.csv] [--port COM10|/dev/ttyACM0] [--dt 0.5] [--max-s 10800]

Appends to an existing file. Stops on Ctrl+C, after --max-s seconds, or when a
file named STOP_FIELDBEST appears next to the CSV (handy when the logger runs
detached). A failed read is written as an empty value; the logger keeps going.
"""
import argparse, datetime, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fieldbest import FieldBest

ap = argparse.ArgumentParser()
ap.add_argument("out", nargs="?", default=datetime.datetime.now().strftime("fieldbest_%Y%m%d_%H%M%S.csv"))
ap.add_argument("--port")
ap.add_argument("--dt", type=float, default=0.5, help="seconds between readings (min. ~0.3)")
ap.add_argument("--max-s", type=float, default=10800)
a = ap.parse_args()

stop = os.path.join(os.path.dirname(os.path.abspath(a.out)), "STOP_FIELDBEST")
if os.path.exists(stop):
    os.remove(stop)

with FieldBest(a.port) as fb, open(a.out, "a", buffering=1) as f:
    print(f"logging {fb.port} -> {a.out}", file=sys.stderr)
    if f.tell() == 0:
        f.write("time,watts\n")
    t0 = time.time()
    try:
        while time.time() - t0 < a.max_s and not os.path.exists(stop):
            t = time.time()
            w = fb.read_watts()
            f.write(f"{datetime.datetime.now().isoformat(timespec='milliseconds')},{'' if w is None else w}\n")
            time.sleep(max(0, a.dt - (time.time() - t)))
    except KeyboardInterrupt:
        pass
