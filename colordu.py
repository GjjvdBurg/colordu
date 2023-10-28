#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Colorful version of du

Author: G.J.J. van den Burg
License: See LICENSE file
Copyright:(c) 2022, G.J.J. van den Burg

"""

import math
import subprocess
import sys
import os

from typing import List, NewType

from rich.console import Console
from rich.theme import Theme

ColorScheme = NewType("ColorScheme", List[str])

POWER_BASE = 1024

# Maximum value in common usage, so we use the whole color range
MIN_SIZE = 4 * POWER_BASE
MAX_SIZE = 512 * pow(POWER_BASE, 3)
DU_UNITS = ["K", "M", "G", "T", "P", "E", "Z", "Y", "R", "Q"]
UNIT_TO_SIZE = {
    unit: pow(POWER_BASE, k + 1) for k, unit in enumerate(DU_UNITS)
}

# Colorschemes are based on this document:
# https://personal.sron.nl/~pault/data/colourschemes.pdf
COLORSCHEME_DISCRETE_RAINBOW = ColorScheme(
    [
        "#882E72",
        "#1965B0",
        "#7BAFDE",
        "#4EB265",
        "#CAE0AB",
        "#F7F056",
        "#EE8026",
        "#DC050C",
    ]
)
COLORSCHEME_SMOOTH_RAINBOW = ColorScheme(
    [
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
)
COLORSCHEME_SUNSET = ColorScheme(
    [
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
)
COLORSCHEME_YLORBR = ColorScheme(
    [
        "#FFF7BC",
        "#FEE391",
        "#FEC44F",
        "#FB9A29",
        "#EC7014",
        "#CC4C02",
        "#993404",
        "#662506",
    ]
)
COLORSCHEME_PARTIAL_SUNSET = ColorScheme(
    [
        "#FEDA8B",
        "#FDB366",
        "#F67E4B",
        "#DD3D2D",
        "#A50026",
        "#A50026",
        "#A50026",
        "#A50026",
    ]
)

KNOWN_COLORSCHEMES: dict[str, ColorScheme | None] = {
    "NONE": None,
    "DISCRETE_RAINBOW": COLORSCHEME_DISCRETE_RAINBOW,
    "SMOOTH_RAINBOW": COLORSCHEME_SMOOTH_RAINBOW,
    "SUNSET": COLORSCHEME_SUNSET,
    "YLORBR": COLORSCHEME_YLORBR,
    "PARTIAL_SUNSET": COLORSCHEME_PARTIAL_SUNSET,
}

DEFAULT_COLORSCHEME_NAME = "SUNSET"
FALLBACK_COLOR = "#666666"


class ParsingError(Exception):
    pass


def get_colorscheme(
    name: str = DEFAULT_COLORSCHEME_NAME,
) -> ColorScheme | None:
    name = os.getenv("COLORDU_SCHEME", name)
    if name not in KNOWN_COLORSCHEMES:
        schemes = ", ".join(list(KNOWN_COLORSCHEMES.keys()))
        raise KeyError(
            f"No colorscheme with name: {name}. Please choose from: {schemes}"
        )
    return KNOWN_COLORSCHEMES[name]


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


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


def parse_line(line: str) -> tuple[str, str, float]:
    if "\t" not in line:
        raise ParsingError(line)
    size, item = line.split("\t")
    unit = size[-1]
    if unit.isalpha():
        if unit not in UNIT_TO_SIZE:
            raise ParsingError(line)
        unit_factor = UNIT_TO_SIZE[unit]
        value = float(size[:-1])
    else:
        unit_factor = 1
        value = float(size) * 1024  # TODO: extract du block size

    filesize = value * unit_factor
    return size, item, filesize


def get_color(filesize: float, colorscheme: ColorScheme) -> str:
    logsize = math.log(filesize, 10)
    fraction = logsize / math.log(MAX_SIZE, 10)
    idx = int(fraction * len(colorscheme)) - 1
    if idx + 1 >= len(colorscheme):
        color = FALLBACK_COLOR
    else:
        color = interpolate_hex_colors(colorscheme[idx], colorscheme[idx + 1])
    return color


def add_markup(line: str, colorscheme: ColorScheme) -> str:
    try:
        size, item, realsize = parse_line(line)
    except ParsingError:
        return line
    color = get_color(realsize, colorscheme)
    return f"[{color}]{size}[/{color}]\t{item}"


def run_du(args: List[str]):
    theme = Theme({}, inherit=False)
    console = Console(theme=theme, force_terminal=True)
    colorscheme = get_colorscheme()

    cmd = ["du", *args]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    if p.stdout is None:
        return
    for line in iter(p.stdout.readline, b""):
        strline = line.decode("utf-8")  # TODO: not guaranteed
        if colorscheme is not None:
            console.print(add_markup(strline, colorscheme), end="")
        else:
            console.print(strline, end="")


def main():
    args = sys.argv[1:]
    run_du(args)


if __name__ == "__main__":
    main()
