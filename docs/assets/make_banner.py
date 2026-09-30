"""README banner: four datasets, raw signals, the same metadata labels.

Needs cwru, jnu, dlr and hit_sm built, and matplotlib (in the dev group):

    uv run python docs/assets/make_banner.py [root]

Writes banner-light.png and banner-dark.png next to this script.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import bearing_datasets as bd

# (dataset, condition): the first signal with that condition is shown
PICKS = [("cwru", "inner"), ("jnu", "ball"), ("dlr", "outer"), ("hit_sm", "inner")]
WINDOW_S = 0.1  # seconds shown per signal

# background None = transparent. Light is opaque white (GitHub's light page), so it stays
# readable wherever <picture> is ignored; dark is only chosen on dark pages and blends in.
THEMES = {
    "light": {
        "background": "#ffffff",
        "primary": "#0b0b0b",
        "secondary": "#52514e",
        "series": "#2a78d6",
    },
    "dark": {"background": None, "primary": "#ffffff", "secondary": "#c3c2b7", "series": "#3987e5"},
}


def load(root):
    out = []
    for name, condition in PICKS:
        ds = bd.open(name, root=root)
        meta = ds.metadata()
        row = meta[meta.condition == condition].iloc[0]
        x = np.asarray(ds.signal(row.signal_id), dtype=float)[: int(WINDOW_S * row.fs)]
        x = x - x.mean()
        x = x / np.percentile(np.abs(x), 99.5)  # display scale only
        out.append((name, condition, row.fs, np.arange(len(x)) / row.fs, x))
    return out


def draw(signals, theme, path):
    c = THEMES[theme]
    fig = plt.figure(figsize=(12.8, 3.6), dpi=100)
    cols, rows = 2, 2
    left, right, top, bottom, gap = 0.04, 0.96, 0.86, 0.17, 0.05
    w = (right - left - gap) / cols
    h = (top - bottom) / rows
    for i, (name, condition, fs, t, x) in enumerate(signals):
        col, row = i % cols, i // cols
        ax = fig.add_axes([left + col * (w + gap), top - (row + 1) * h + 0.02, w, h - 0.12])
        ax.plot(t, x, color=c["series"], linewidth=0.8, solid_joinstyle="round")
        ax.set_xlim(0, WINDOW_S)
        ax.set_ylim(-1.1, 1.1)
        ax.axis("off")
        ax.text(
            0,
            1.06,
            name,
            transform=ax.transAxes,
            color=c["primary"],
            fontsize=14,
            weight="bold",
            va="bottom",
            family="monospace",
        )
        ax.text(
            0.15,
            1.06,
            f"condition={condition}  ·  {fs / 1000:g} kHz",
            transform=ax.transAxes,
            color=c["secondary"],
            fontsize=14,
            va="bottom",
            family="monospace",
        )
    fig.text(
        0.5,
        0.05,
        "Different rigs, sensors and sampling rates. Same columns, same labels.",
        color=c["secondary"],
        fontsize=15,
        ha="center",
    )
    if c["background"] is None:
        fig.savefig(path, transparent=True, dpi=100)
    else:
        fig.savefig(path, facecolor=c["background"], dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    signals = load(sys.argv[1] if len(sys.argv) > 1 else None)
    here = Path(__file__).parent
    for theme in THEMES:
        draw(signals, theme, here / f"banner-{theme}.png")
