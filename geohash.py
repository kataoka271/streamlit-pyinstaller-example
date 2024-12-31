from collections import defaultdict
from math import ceil, cos, floor, pi, sqrt
from typing import Iterable, Iterator

import numpy as np

base = "0123456789bcdefghjkmnpqrstuvwxyz"


def create_rect(lat_min, lon_min, lat_max, lon_max, precision: int) -> Iterator[str]:
    """Create Geohashes containing the box of `(lat_min, lon_min, lat_max, lon_max)`"""
    code1 = encode(lat_min, lon_min, precision)
    lat1, lon1 = _split_bits(code1)
    code2 = encode(lat_max, lon_max, precision)
    lat2, lon2 = _split_bits(code2)
    lat2 = lat2 + 1
    lon2 = lon2 + 1
    for y in range(lat1, lat2):
        for x in range(lon1, lon2):
            yield _join_bits(y, x, precision)


def create_circle(lat: float, lon: float, radius: float, precision: int) -> Iterator[str]:
    code = encode(lat, lon, precision)
    lat_min, lon_min, lat_max, lon_max = decode(code)
    w, h = _grid_size(lat_max - lat_min, lon_max - lon_min, lat)
    lat_bits, lon_bits = _split_bits(code)
    rx, ry = (lon - lon_min) / (lon_max - lon_min), (lat - lat_min) / (lat_max - lat_min)
    pts = _grid_points(rx, ry, radius, w, h)
    for i, j in pts:
        yield _join_bits(lat_bits + j, lon_bits + i, precision)


def _grid_points(a: float, b: float, r: float, w: float, h: float) -> Iterator[tuple[int, int]]:
    def f(x: float):
        return pow(r, 2) - pow((a - x) * w, 2)

    x = ceil(a - r / w) - 1
    x_last = floor(a + r / w)
    while x <= x_last:
        p = sqrt(max(f(x + 1), f(x))) / h
        y = ceil(b - p) - 1
        y_last = floor(b + p)
        while y <= y_last:
            yield (x, y)
            y += 1
        x += 1


def _grid_size(lat_diff: float, lon_diff: float, lat: float) -> tuple[float, float]:
    R = 6378137  # 赤道半径
    w = lon_diff * (pi / 180.0) * R * cos(lat * pi / 180.0)
    h = lat_diff * (pi / 180.0) * R
    return (w, h)


def decode(code: str) -> tuple[float, float, float, float]:
    """convert Geohash `code` to `(lat_min, lon_min, lat_max, lon_max)`"""
    lat_max = 90
    lat_min = -90
    lon_max = 180
    lon_min = -180
    v = 0
    for c in code:
        v = (v << 5) | base.index(c)
    i = len(code) * 5 - 1
    while i >= 0:
        lon_mid = (lon_max + lon_min) / 2
        if (v >> i) & 1 == 1:
            lon_min = lon_mid
        else:
            lon_max = lon_mid
        i = i - 1
        if i < 0:
            break
        lat_mid = (lat_max + lat_min) / 2
        if (v >> i) & 1 == 1:
            lat_min = lat_mid
        else:
            lat_max = lat_mid
        i = i - 1
    return (lat_min, lon_min, lat_max, lon_max)


def neighbors(code: str) -> list[str]:
    """Get neighbor Geohashes

    >>> neighbors("bbccd")
    ['bbccd', 'bbccf', 'bbccc', 'bbcc9', 'bbcc3', 'bbcc6', 'bbcc7', 'bbcce', 'bbccg']
    """
    precision = len(code)
    lat, lon = _split_bits(code)
    north = _join_bits(lat + 1, lon, precision)
    west = _join_bits(lat, lon - 1, precision)
    south = _join_bits(lat - 1, lon, precision)
    east = _join_bits(lat, lon + 1, precision)
    nw = _join_bits(lat + 1, lon - 1, precision)
    sw = _join_bits(lat - 1, lon - 1, precision)
    se = _join_bits(lat - 1, lon + 1, precision)
    ne = _join_bits(lat + 1, lon + 1, precision)
    return [code, north, nw, west, sw, south, se, east, ne]


def _split_bits(code: str) -> tuple[int, int]:
    lat = 0
    lon = 0
    v = 0
    for c in code:
        v = (v << 5) | base.index(c)
    i = len(code) * 5 - 1
    while i >= 0:
        lon = (lon << 1) | ((v >> i) & 1)
        i = i - 1
        if i < 0:
            break
        lat = (lat << 1) | ((v >> i) & 1)
        i = i - 1
    return (lat, lon)


def _join_bits(lat: int, lon: int, precision: int) -> str:
    nbits = precision * 5
    c = []
    i = nbits // 2 - 1
    v = 0
    if nbits % 2 == 1:
        v = (v << 1) | ((lon >> i) & 1)
        while i >= 0:
            v = (v << 1) | ((lat >> i) & 1)
            v = (v << 1) | ((lon >> i) & 1)
            i -= 1
    else:
        while i >= 0:
            v = (v << 1) | ((lon >> i) & 1)
            v = (v << 1) | ((lat >> i) & 1)
            i -= 1
    for i in range(nbits - 5, -5, -5):
        c.append(base[(v >> i) & 0x1F])
    return "".join(c)


def encode(lat: float, lon: float, precision: int) -> str:
    lat_max = 90
    lat_min = -90
    lon_max = 180
    lon_min = -180
    value = 0
    i = 0
    code = []
    nbits = precision * 5

    # latitude, longitude
    while i < nbits:
        lon_mid = (lon_max + lon_min) / 2
        if lon_mid <= lon:
            value = (value << 1) | 1
            lon_min = lon_mid
        else:
            value = value << 1
            lon_max = lon_mid
        if i % 5 == 4:
            code.append(base[value & 0x1F])
        i += 1
        if i >= nbits:
            break
        lat_mid = (lat_max + lat_min) / 2
        if lat_mid <= lat:
            value = (value << 1) | 1
            lat_min = lat_mid
        else:
            value = value << 1
            lat_max = lat_mid
        if i % 5 == 4:
            code.append(base[value & 0x1F])
        i += 1

    return "".join(code)


def isin(poi, codes, arr):
    for i in range(poi.shape[0]):
        for j in range(codes.shape[0]):
            s = poi[i]
            t = codes[j]
            arr[i] = arr[i] or s.startswith(t) or t.startswith(s)


def isin_circle(poi, lat: float, lon: float, radius: float, precision: int):
    arr = np.empty(poi.shape)
    isin(poi, create_circle(lat, lon, radius, precision), arr)
    return arr


def many_neighbors(codes: Iterable[str]) -> set[str]:
    S = set()
    for code in codes:
        S.update(neighbors(code))
    return S


def compress(codes: Iterable[str], *, accuracy: float = 1.0) -> list[str]:
    """compress Geohashes

    >>> compress(["bcbcde", "bcbcde", "bcbcd", "bcbef"])
    ['bcbcd', 'bcbef']
    >>> compress(["bb"] + ["bcbc" + c for c in base] + ["be"])
    ['bb', 'be', 'bcbc']
    >>> compress(["bb"] + ["bcbc" + c for c in base[:26]] + ["be"], accuracy=0.8)
    ['bb', 'be', 'bcbc']
    >>> compress(["bb"] + ["bcb" + c + d for c in base[:25] for d in base[:26]] + ["bcbt"], accuracy=0.8)  # noqa: E501
    ['bb', 'bcb']
    >>> compress(["bc1", "bcb0", "bcb1", "bcc0", "bcc1"], accuracy=0.0625)
    ['bc']
    >>> compress(["b1", "bb", "be", "bc", "bcb1", "bcb2", "bcb3", "bcb4"], accuracy=0.125)
    ['b']
    >>> compress(["bcbc" + c for c in base[:26]] + ["bcb" + c for c in base if c != 'c'], accuracy=0.8)
    ['bcb']
    """
    while True:
        input_codes = []
        for code in sorted(codes, key=len):
            if not any(code.startswith(c) for c in input_codes):
                input_codes.append(code)
        d = defaultdict(list)
        for c in input_codes:
            d[c[:-1]].append(c)
        output_codes = []
        for c, v in d.items():
            if len(v) >= 32 * accuracy:
                output_codes.append(c)
            else:
                output_codes.extend(v)
        if len(input_codes) == len(output_codes):
            break
        codes = output_codes
    return output_codes
