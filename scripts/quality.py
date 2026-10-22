"""Data-quality report over every sport and league in data/matches.sqlite."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.quality import run  # noqa: E402

if __name__ == "__main__":
    rep = run(ROOT / "data" / "matches.sqlite")
    print(f"{'league':<14}{'sport':<8}{'rows':>7}{'1X2':>7}{'totals':>8}")
    for lg, s in sorted(rep.stats.items(), key=lambda kv: (kv[1]['sport'], kv[0])):
        print(f"{lg:<14}{s['sport']:<8}{s['rows']:>7}{s['with_1x2']:>7}{s['with_totals']:>8}")
    print()
    if not rep.issues:
        print("no issues")
    for i in sorted(rep.issues, key=lambda i: (i.severity != "error", i.check, i.league)):
        print(f"[{i.severity:<5}] {i.check:<28} {i.league:<14} n={i.count:<6} {i.note}")

    from sportdata_model.quality import install_view  # noqa: E402
    install_view(ROOT / "data" / "matches.sqlite")
    print("\ncanonical view matches_canonical installed")
