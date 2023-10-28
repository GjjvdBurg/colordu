#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Colorful version of du

Author: G.J.J. van den Burg
License: See LICENSE file
Copyright:(c) 2022, G.J.J. van den Burg

"""

import math
import subprocess
import sys

from typing import List
from typing import TypedDict

from rich.console import Console
from rich.theme import Theme


class ColorScheme(TypedDict):
    # Labels are based on human.c, here:
    # https://github.com/coreutils/gnulib/blob/master/lib/human.c
    K: str
    M: str
    G: str
    T: str
    P: str
    E: str
    Z: str
    Y: str


MAX_SIZE = 512 * pow(1024, 3)

POWERS = {
    letter: pow(1024, k + 1)
    for k, letter in enumerate(
        [
            "K",
            "M",
            "G",
            "T",
            "P",
            "E",
            "Z",
            "Y",
        ]
    )
}

# Default colorscheme is based on this document:
# https://personal.sron.nl/~pault/data/colourschemes.pdf
DISCRETE_RAINBOW: ColorScheme = {
    "K": "#882E72",  #  9
    "M": "#1965B0",  # 10
    "G": "#7BAFDE",  # 14,
    "T": "#4EB265",  # 15,
    "P": "#CAE0AB",  # 17,
    "E": "#F7F056",  # 18,
    "Z": "#EE8026",  # 23,
    "Y": "#DC050C",  # 26,
}

# We're optimizing for the common case, so 0 will be the start and 1TB will be
# then end, then we interpolate between them.
# From
# https://personal.sron.nl/~pault/data/colourschemes.pdf
SMOOTH_RAINBOW = [
    "#E8ECFB",
    "#DDD8EF",
    "#D1C1E1",
    "#C3A8D1",
    "#B58FC2",
    "#A778B4",
    "#9B62A7",
    "#8C4E99",
    "#6F4C9B",
    "#6059A9",
    "#5568B8",
    "#4E79C5",
    "#4D8AC6",
    "#4E96BC",
    "#549EB3",
    "#59A5A9",
    "#60AB9E",
    "#69B190",
    "#77B77D",
    "#8CBC68",
    "#A6BE54",
    "#BEBC48",
    "#D1B541",
    "#DDAA3C",
    "#E49C39",
    "#E78C35",
    "#E67932",
    "#E4632D",
    "#DF4828",
    "#DA2222",
    "#B8221E",
    "#95211B",
    "#721E17",
    "#521A13",
]

# Full sunset
SUNSET = [
    "#364B9A",
    "#4A7BB7",
    "#6EA6CD",
    "#98CAE1",
    "#C2E4EF",
    "#EAECCC",
    "#FEDA8B",
    "#FDB366",
    "#F67E4B",
    "#DD3D2D",
    "#A50026",
]

# Fallback
FALLBACK_COLOR = "#666666"

SEQUENTIAL_YLORBR: ColorScheme = {
    "K": "#FFF7BC",
    "M": "#FEE391",
    "G": "#FEC44F",
    "T": "#FB9A29",
    "P": "#EC7014",
    "E": "#CC4C02",
    "Z": "#993404",
    "Y": "#662506",
}

PARTIAL_SUNSET: ColorScheme = {
    "K": "#FEDA8B",
    "M": "#FDB366",
    "G": "#F67E4B",
    "T": "#DD3D2D",
    "P": "#A50026",
    "E": "#A50026",
    "Z": "#A50026",
    "Y": "#A50026",
}


DEFAULT_COLORSCHEME = PARTIAL_SUNSET


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    lv = len(value)
    return tuple(
        int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3)
    )


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"#{red:02x}{green:02x}{blue:02x}"


def interpolate_hex_colors(hex_1: str, hex_2: str) -> str:
    r1, g1, b1 = hex_to_rgb(hex_1)
    r2, g2, b2 = hex_to_rgb(hex_2)

    r1, r2 = (r1, r2) if r1 < r2 else (r2, r1)
    g1, g2 = (g1, g2) if g1 < g2 else (g2, g1)
    b1, b2 = (b1, b2) if b1 < b2 else (b2, b1)

    nr = int(max(0, min(r1 + (r2 - r1) / 2, 255)))
    ng = int(max(0, min(g1 + (g2 - g1) / 2, 255)))
    nb = int(max(0, min(b1 + (b2 - b1) / 2, 255)))
    return rgb_to_hex((nr, ng, nb))


def add_markup_v2(
    line: str, colorscheme: ColorScheme = DEFAULT_COLORSCHEME
) -> str:
    line = line.decode("utf-8")  # TODO: not guaranteed
    if "\t" not in line:
        return line
    size, item = line.split("\t")
    power_letter = size[-1]
    if power_letter not in POWERS:
        return line
    # size in bytes
    realsize = float(size[:-1]) * POWERS[power_letter]
    logsize = math.log(realsize, 10)
    fraction = logsize / math.log(MAX_SIZE, 10)
    colors = SUNSET
    index = int(fraction * len(colors)) - 1
    next_index = index + 1
    if next_index >= len(colors):
        color = FALLBACK_COLOR
    else:
        color = interpolate_hex_colors(colors[index], colors[next_index])
    # print(f"{realsize=}, {index=}, {next_index=}, {color=}")
    return f"[{color}]{size}[/{color}]\t{item}"


def add_markup(
    line: str, colorscheme: ColorScheme = DEFAULT_COLORSCHEME
) -> str:
    line = line.decode("utf-8")  # TODO: not guaranteed
    if "\t" not in line:
        return line
    size, item = line.split("\t")
    power_letters = list(colorscheme.keys())
    if not any(size.endswith(letter) for letter in power_letters):
        return f"{size}\t{item}"
    power_letter = size[-1]
    color = colorscheme[power_letter]
    return f"[{color}]{size}[/{color}]\t{item}"


def run_du(args: List[str], colorscheme: ColorScheme = DEFAULT_COLORSCHEME):
    theme = Theme({}, inherit=False)
    console = Console(theme=theme)

    cmd = ["du", *args]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    for line in iter(p.stdout.readline, b""):
        console.print(add_markup_v2(line), end="")


def main():
    args = sys.argv[1:]
    run_du(args)


if __name__ == "__main__":
    main()
