"""Social preview (the card shown when the repository link is shared): 1280 x 640.

Needs cwru, jnu, dlr and hit_sm built, and matplotlib (in the dev group):

    uv run python docs/assets/make_social.py [root]

Writes social-preview.png next to this script; upload it in the repository settings
(General > Social preview).
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from make_banner import load

W, H = 1280, 640
BACKGROUND, PRIMARY, SECONDARY = "#1b1b1b", "#ffffff", "#c3c2b7"
MUTED, SERIES = "#8f8e88", "#3987e5"


def _text(fig, x, y, s, **kw):
    """Text at (x, y) pixels from the top left."""
    fig.text(x / W, 1 - y / H, s, **kw)


def draw(signals, path):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BACKGROUND)
    _text(fig, 70, 160, "bearing-datasets", color=PRIMARY, fontsize=40, weight="bold", va="center")
    _text(fig, 70, 240, "Public bearing fault datasets", color=SECONDARY, fontsize=24, va="center")
    _text(fig, 70, 282, "→ one Parquet format", color=SECONDARY, fontsize=24, va="center")
    _text(fig, 70, 324, "same columns, same labels", color=SECONDARY, fontsize=24, va="center")
    _text(
        fig, 86, 420, "pip install bearing-datasets", color=PRIMARY, fontsize=19,
        family="monospace", va="center",
        bbox={"boxstyle": "round,pad=0.6,rounding_size=0.3", "facecolor": "#2a2a2a",
              "edgecolor": "none"},
    )  # fmt: skip
    _text(fig, 70, 530, "Python · pandas · NumPy · polars", color=MUTED, fontsize=16, va="center")
    _text(fig, 70, 565, "checksum-verified downloads", color=MUTED, fontsize=16, va="center")

    left, width, top, step = 700, 530, 62, 131
    for i, (name, fault_type, fs, t, x) in enumerate(signals):
        y = top + i * step
        _text(fig, left, y + 16, name, color=PRIMARY, fontsize=14, weight="bold",
              family="monospace", va="center")  # fmt: skip
        _text(fig, left + 88, y + 16, f"fault_type={fault_type} · {fs / 1000:g} kHz",
              color=SECONDARY, fontsize=14, family="monospace", va="center")  # fmt: skip
        ax = fig.add_axes([left / W, 1 - (y + 125) / H, width / W, 90 / H])
        ax.plot(t, x, color=SERIES, linewidth=0.9, solid_joinstyle="round")
        ax.set_xlim(t[0], t[-1])
        ax.set_ylim(-1.1, 1.1)
        ax.axis("off")
    fig.savefig(path, facecolor=BACKGROUND, dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    signals = load(sys.argv[1] if len(sys.argv) > 1 else None)
    draw(signals, Path(__file__).parent / "social-preview.png")
