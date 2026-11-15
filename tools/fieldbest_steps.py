"""Find power steps in a FieldBest log and print one line per step.

Usage:  python fieldbest_steps.py log.csv [--on 0.3] [--window 20] [--min-s 15] [--after HH:MM] [--before HH:MM]

A step is a run of readings above --on watts. The meter needs about 10 s to
settle (>95 %), so each step is evaluated as the mean of the last --window
seconds before the reading falls off, i.e. before the last point that is still
within 1 % of the step's maximum.
"""
import argparse, csv
from datetime import datetime


def read_log(path):
    return [(datetime.fromisoformat(t), float(w)) for t, w in csv.reader(open(path)) if t != "time" and w]


def find_steps(rows, on=0.3, window=20, min_s=15):
    """Return a list of dicts: start, end, mean, min, max, n."""
    runs, cur = [], None
    for t, w in rows:
        if w > on:
            cur = (cur or []) + [(t, w)]
        elif cur:
            runs.append(cur); cur = None
    if cur:
        runs.append(cur)
    out = []
    for v in runs:
        if (v[-1][0] - v[0][0]).total_seconds() < min_s:
            continue
        mx = max(w for _, w in v)
        i = max(k for k, (_, w) in enumerate(v) if w >= 0.99 * mx)
        tend = v[i][0]
        win = [w for t, w in v[:i + 1] if (tend - t).total_seconds() <= window]
        out.append(dict(start=v[0][0], end=tend, mean=sum(win) / len(win), min=min(win), max=max(win), n=len(win)))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--on", type=float, default=0.3, help="threshold in W that marks 'laser on'")
    ap.add_argument("--window", type=float, default=20, help="averaging window in s before the step end")
    ap.add_argument("--min-s", type=float, default=15, help="ignore steps shorter than this (s)")
    ap.add_argument("--after", help="only steps starting at or after HH:MM[:SS]")
    ap.add_argument("--before", help="only steps starting before HH:MM[:SS]")
    a = ap.parse_args()
    print("start     end       mean_W   min_W    max_W    spread  n")
    for s in find_steps(read_log(a.csv), a.on, a.window, a.min_s):
        hms = s["start"].strftime("%H:%M:%S")
        if (a.after and hms < a.after) or (a.before and hms >= a.before):
            continue
        print(f"{hms}  {s['end']:%H:%M:%S}  {s['mean']:7.3f}  {s['min']:7.3f}  {s['max']:7.3f}  "
              f"{(s['max'] - s['min']) / s['mean'] * 100:5.1f} %  {s['n']}")
