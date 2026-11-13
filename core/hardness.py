"""Перевод твёрдости/прочности в HB (для сталей)."""
from bisect import bisect_left

_HRC_HB = [(20, 226), (25, 253), (30, 286), (35, 327), (40, 371),
           (45, 421), (50, 481), (55, 543), (60, 613), (65, 739)]


def hrc_to_hb(hrc: float) -> float:
    pts = _HRC_HB
    if hrc <= pts[0][0]:
        return float(pts[0][1])
    if hrc >= pts[-1][0]:
        return float(pts[-1][1])
    xs = [p[0] for p in pts]
    i = bisect_left(xs, hrc)
    (x0, y0), (x1, y1) = pts[i - 1], pts[i]
    return y0 + (y1 - y0) * (hrc - x0) / (x1 - x0)


def rm_to_hb(rm_mpa: float) -> float:
    """HB ≈ Rm / 3.45 (эмпирика для сталей)."""
    return rm_mpa / 3.45


def to_hb(kind: str, value: float, default_hb: float) -> float:
    if kind == "HB":
        return value
    if kind == "HRC":
        return hrc_to_hb(value)
    if kind == "Rm":
        return rm_to_hb(value)
    return default_hb
