"""Расчётное ядро: vc, обороты, подачи, мощность, проверки ограничений."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from . import catalog as cat
from .hardness import to_hb
from .models import (Category, CuttingInput, CuttingResult, Level, Message,
                     Material, Operation, ToolType)

O = Operation


class CalculationError(ValueError):
    """Ошибка входных данных, при которой расчёт невозможен."""


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def check_compatibility(mat: Material, tt: ToolType) -> Tuple[Optional[Level], str]:
    factor = tt.vc_factor.get(mat.iso)
    if factor is None:
        allowed = ", ".join(g for g, f in tt.vc_factor.items() if f is not None)
        return (Level.ERROR,
                f"«{tt.name}» не применяется для группы {mat.iso} ({mat.name}). "
                f"Допустимые группы ISO: {allowed}.")
    note = tt.notes.get(mat.iso)
    if note:
        return Level.WARNING, note
    return None, ""


def validate_input(inp: CuttingInput) -> None:
    op, t, p, m = inp.operation, inp.tool, inp.params, inp.machine
    fields = cat.OP_FIELDS[op]
    turning = op.category == Category.TURNING

    level, text = check_compatibility(inp.material, t.tool_type)
    if level == Level.ERROR:
        raise CalculationError(text)
    if t.diameter <= 0:
        raise CalculationError("Диаметр (сечение) инструмента должен быть > 0.")
    if t.teeth < 1:
        raise CalculationError("Число зубьев z должно быть ≥ 1.")
    if t.overhang <= 0:
        raise CalculationError("Вылет инструмента должен быть > 0.")
    if p.length <= 0:
        raise CalculationError("Длина обработки должна быть > 0.")
    if m.n_max <= 0 or m.power_kw <= 0:
        raise CalculationError("n_max и мощность станка должны быть > 0.")
    if not 0.3 <= m.efficiency <= 1.0:
        raise CalculationError("КПД η должен быть в диапазоне 0.3…1.0.")
    if turning:
        if p.workpiece_diameter <= 0:
            raise CalculationError("Диаметр обработки должен быть > 0.")
        if "ap" in fields and p.ap <= 0:
            raise CalculationError("Глубина резания ap должна быть > 0.")
        if op in (O.TURN_ROUGH, O.TURN_FINISH) and p.ap >= p.workpiece_diameter / 2:
            raise CalculationError("ap должна быть меньше радиуса заготовки.")
        if op in (O.TURN_ROUGH, O.TURN_FINISH, O.BORING) and t.corner_radius <= 0:
            raise CalculationError("Радиус при вершине r должен быть > 0.")
        if op is O.BORING and t.diameter >= p.workpiece_diameter:
            raise CalculationError("Диаметр борштанги должен быть меньше отверстия.")
        if op is O.THREADING and p.pitch <= 0:
            raise CalculationError("Шаг резьбы должен быть > 0.")
        if op is O.THREADING and p.pitch >= p.workpiece_diameter / 2:
            raise CalculationError("Шаг слишком велик для заданного диаметра.")
    else:
        if "ap" in fields and p.ap <= 0:
            raise CalculationError("Глубина резания ap должна быть > 0.")
        if "ae" in fields and not 0 < p.ae <= t.diameter:
            raise CalculationError("Ширина фрезерования: 0 < ae ≤ D.")
        if op is O.COUNTERBORING and not 0 <= p.pre_hole < t.diameter:
            raise CalculationError("Предв. отверстие должно быть меньше диаметра зенкера.")


@dataclass
class _Cut:
    ap: float
    ae: float
    D: float
    z: int
    pitch: float
    kappa: float


def _mean_chip_milling(fz: float, ae: float, D: float, kappa_deg: float) -> float:
    r = clamp(ae / D, 1e-4, 1.0)
    phi = math.acos(1 - 2 * r)
    return 2 * fz * r * math.sin(math.radians(kappa_deg)) / phi


def _chip_thinning(ae: float, D: float) -> float:
    r = clamp(ae / D, 1e-4, 1.0)
    if r >= 0.5:
        return 1.0
    phi = math.acos(1 - 2 * r)
    return clamp((2 / math.pi) / (2 * r / phi), 1.0, 2.0)


def _ra_feed_factor(ra: float) -> float:
    if ra <= 0.8:
        return 0.35
    if ra <= 1.6:
        return 0.5
    if ra <= 3.2:
        return 0.7
    return 1.0


def _cutting_load(op, kc11, mc, g: _Cut, fn, fz, vc, vf):
    """→ (P резания, кВт; kc, Н/мм²; h, мм). kc = kc1.1·h^(−mc)."""
    if op in (O.TURN_ROUGH, O.TURN_FINISH, O.BORING, O.PARTING):
        h = max(fn, 0.02)
        kc = kc11 * h ** (-mc)
        return kc * g.ap * h * vc / 60000.0, kc, h
    if op is O.THREADING:
        h = max(0.5 * g.ap, 0.02)
        kc = kc11 * h ** (-mc)
        return kc * g.pitch * h * vc / 60000.0, kc, h
    if op in (O.FACE_MILL, O.END_SLOT, O.END_CONTOUR):
        h = max(_mean_chip_milling(fz, g.ae, g.D, g.kappa), 0.005)
        kc = kc11 * h ** (-mc)
        return g.ap * g.ae * vf * kc / 60e6, kc, h
    if op is O.DRILLING:
        h = max(0.5 * fn * math.sin(math.radians(59)), 0.005)   # 2φ = 118°
        kc = kc11 * h ** (-mc)
        return vc * fn * g.D * kc / 240e3, kc, h
    h = max(fn / g.z * math.sin(math.radians(60)), 0.005)       # зенкерование
    kc = kc11 * h ** (-mc)
    return kc * g.ap * fn * vc / 60000.0, kc, h


def calculate(inp: CuttingInput) -> CuttingResult:
    validate_input(inp)
    op, mat, tool, par, mach = inp.operation, inp.material, inp.tool, inp.params, inp.machine
    tt = tool.tool_type
    turning = op.category == Category.TURNING
    D, z = tool.diameter, tool.teeth
    group = mat.iso

    msgs, flags = [], {}

    def note(level, text, flag=None):
        msgs.append(Message(level, text))
        if flag and level > flags.get(flag, Level.OK):
            flags[flag] = level

    # 1. Твёрдость
    hb = to_hb(inp.hardness.kind, inp.hardness.value, mat.hb_ref)
    ratio = hb / mat.hb_ref
    k_hard = clamp(ratio ** (-mat.v_hard_exp), 0.4, 1.6)
    kc11 = mat.kc11 * clamp(ratio ** 0.5, 0.75, 1.5)
    if inp.hardness.kind != "default" and not mat.hb_min <= hb <= mat.hb_max:
        note(Level.WARNING, f"Твёрдость {hb:.0f} HB вне типичного диапазона "
                            f"({mat.hb_min:.0f}…{mat.hb_max:.0f} HB) — результат менее достоверен.")

    # 2. Инструмент, стойкость, жёсткость
    level, text = check_compatibility(mat, tt)
    if level is not None:
        note(level, text)
    if group == "N" and tt.key == "carbide" and tool.coated:
        note(Level.INFO, "Для Al предпочтительны полированные/DLC-покрытия; TiAlN склонно к налипанию.")
    k_mat = float(tt.vc_factor[group])
    k_coat = tt.coating_factors[0] if (tool.coated and tt.supports_coating) else tt.coating_factors[1]
    life = clamp(par.tool_life, 5, 480)
    k_life = (60.0 / life) ** tt.taylor_n           # Тейлор: v·T^n = const
    k_op = cat.OP_VC_FACTOR[op]
    rig = cat.RIGIDITY[mach.rigidity][1]
    k_rig_v = math.sqrt(rig)

    ld = tool.overhang / D
    ld_warn, ld_crit = cat.OP_LD_LIMITS[op]
    k_oh = 1.0 if ld <= 3.0 else math.sqrt(3.0 / ld)
    if ld > ld_crit:
        note(Level.ERROR, f"L/D = {ld:.1f} > {ld_crit:.1f}: уменьшите вылет или сечение.", "rigidity")
    elif ld > ld_warn:
        note(Level.WARNING, f"Большой вылет L/D = {ld:.1f} (рек. ≤ {ld_warn:.1f}); режимы снижены (×{k_oh:.2f}).", "rigidity")
    if mach.rigidity == "low":
        note(Level.INFO, "Низкая жёсткость СПИД: подача и скорость снижены.")
    k_f = tt.feed_factor * rig * k_oh

    # 3. Подача
    kappa = cat.KAPPA.get(op, 90.0)
    ae, ap, passes, pitch = None, par.ap, 1, par.pitch
    if op is O.THREADING:
        fn = fz = pitch
        depth = 0.6134 * pitch
        ap = cat.THREAD_AP_PASS[group]
        passes = max(1, math.ceil(depth / ap))
        note(Level.INFO, f"Резьба: глубина профиля {depth:.2f} мм, {passes} проходов по {ap:.2f} мм.")
    elif turning:
        fn = cat.TURN_FEED[group] * cat.OP_FEED_TURN[op] * k_f
        r = tool.corner_radius
        if op in (O.TURN_ROUGH, O.TURN_FINISH, O.BORING):
            f_ra = math.sqrt(par.ra * 32.0 * r / 1000.0)
            if f_ra < fn:
                note(Level.INFO, f"Подача ограничена Ra {par.ra} / r = {r} мм.")
            fn = min(fn, f_ra, 0.8 * r)
        elif r > 0:
            fn = min(fn, 0.8 * r)
        fn = max(fn, 0.02)
        fz = fn
    elif op in (O.FACE_MILL, O.END_SLOT, O.END_CONTOUR):
        ae = D if op is O.END_SLOT else par.ae
        fz = cat.MILL_FZ[group] * cat.OP_FEED_MILL[op] * k_f
        if op is not O.FACE_MILL:
            fz *= clamp((D / 12.0) ** 0.3, 0.6, 1.3)
        else:
            fz /= math.sin(math.radians(kappa))
        fz *= _chip_thinning(ae, D) * _ra_feed_factor(par.ra)
        fn = fz * z
        if op is O.FACE_MILL:
            if par.ae > 0.8 * D:
                note(Level.WARNING, "ae > 0.8·D: для торцевой фрезы рекомендуется 0.6…0.75·D.")
            if ap > 0.25 * D:
                note(Level.WARNING, "ap > 0.25·D: проверьте допустимую глубину пластины.")
        elif ap > 1.5 * D:
            note(Level.WARNING, f"ap = {ap:g} > 1.5·D — риск вибраций.", "rigidity")
        if op is O.END_SLOT and ap > D:
            note(Level.WARNING, "Паз глубже 1·D: рекомендуется несколько проходов.")
    else:
        fn = max(clamp(cat.DRILL_COEF[group] * D, 0.02, 0.6) * k_f, 0.01)
        if op is O.COUNTERBORING:
            fn *= 1.8
        fz = fn / z
        ap = D / 2 if op is O.DRILLING else (D - par.pre_hole) / 2

    # 4. Скорость резания
    if turning:
        f_ref = 0.6 * cat.TURN_FEED[group]
        k_geom = (2.0 / ap) ** 0.12 * (f_ref / fn) ** 0.25
    elif op not in (O.THREADING, O.DRILLING, O.COUNTERBORING):
        hm0 = _mean_chip_milling(fz, ae, D, kappa)
        k_geom = (0.64 * cat.MILL_FZ[group] / max(hm0, 1e-3)) ** 0.25 * (3.0 / ap) ** 0.10
    else:
        k_geom = 1.0
    k_geom = clamp(k_geom, 0.6, 1.4)
    vc_target = max(1.0, mat.vc_ref * k_hard * k_mat * k_coat * k_life * k_op
                    * k_geom * k_rig_v * math.sqrt(k_oh))

    # 5. Обороты  n = vc·1000/(π·D)
    d_calc = par.workpiece_diameter if turning else D
    n_th = vc_target * 1000.0 / (math.pi * d_calc)
    if n_th > mach.n_max:
        n = max(1, int(mach.n_max))
        vc_lim = math.pi * d_calc * n / 1000.0
        note(Level.WARNING, f"Расчётные {n_th:.0f} об/мин > n_max = {mach.n_max:.0f}. "
                            f"vc снижена с {vc_target:.0f} до {vc_lim:.0f} м/мин "
                            f"(−{(1 - vc_lim / vc_target) * 100:.0f} %).", "n")
        flags["vc"] = Level.WARNING
    else:
        n = max(1, int(n_th))
    n0 = n

    # 6. Мощность: при превышении — снижаем подачу, затем обороты
    geom = _Cut(ap=ap, ae=ae or 0.0, D=D, z=z, pitch=pitch, kappa=kappa)
    adjustable = op is not O.THREADING

    def evaluate(fn_s, n_cur):
        fn_c, fz_c = fn * fn_s, fz * fn_s
        vc_c = math.pi * d_calc * n_cur / 1000.0
        vf_c = fn_c * n_cur
        p, kc, h = _cutting_load(op, kc11, mat.mc, geom, fn_c, fz_c, vc_c, vf_c)
        return fn_c, fz_c, vc_c, vf_c, p, kc, h

    fn_s = 1.0
    for _ in range(120):
        fn_c, fz_c, vc_c, vf_c, p_cut, kc, h = evaluate(fn_s, n)
        if p_cut / mach.efficiency <= mach.power_kw:
            break
        if adjustable and fn_s > 0.5:
            fn_s *= 0.97
        elif n > 0.6 * n0 and n > 1:
            n = max(1, int(n * 0.97))
        else:
            break
    fn_c, fz_c, vc_c, vf_c, p_cut, kc, h = evaluate(fn_s, n)

    p_spindle = p_cut / mach.efficiency
    load = p_spindle / mach.power_kw * 100.0
    if fn_s < 1.0:
        note(Level.WARNING, f"Подача снижена на {(1 - fn_s) * 100:.0f} % из-за мощности станка.", "vf")
    if n < n0:
        note(Level.WARNING, f"Обороты дополнительно снижены с {n0} до {n} об/мин по мощности.", "n")
        flags["vc"] = Level.WARNING
    if load > 100:
        note(Level.ERROR, f"Мощности не хватает: нужно {p_spindle:.1f} кВт при {mach.power_kw:.1f} кВт. "
                          f"Уменьшите ap/ae или выберите другой станок.", "power")
    elif load > 85:
        note(Level.WARNING, f"Высокая загрузка мощности: {load:.0f} %.", "power")

    fc = p_cut * 60000.0 / vc_c if vc_c > 0 else 0.0
    torque = p_cut * 9550.0 / n

    # 7. Производительность и время
    if op is O.THREADING:
        q = None
    elif turning:
        q = ap * fn_c * vc_c                     # численно = см³/мин
    elif op in (O.DRILLING, O.COUNTERBORING):
        d0 = par.pre_hole if op is O.COUNTERBORING else 0.0
        q = math.pi / 4.0 * (D ** 2 - d0 ** 2) * vf_c / 1000.0
    else:
        q = ap * (ae or 0.0) * vf_c / 1000.0     # Q = ap·ae·vf/1000, см³/мин
    time_min = par.length / vf_c * passes

    # 8. Ra и прогиб
    ra_est = None
    if op in (O.TURN_ROUGH, O.TURN_FINISH, O.BORING):
        ra_est = fn_c ** 2 / (32.0 * tool.corner_radius) * 1000.0
        if ra_est > par.ra * 1.05:
            note(Level.WARNING, f"Расчётная Ra {ra_est:.2f} > требуемой {par.ra}: увеличьте r или снизьте подачу.")
    deflection = None
    if op not in (O.DRILLING, O.COUNTERBORING):
        square = op in (O.TURN_ROUGH, O.TURN_FINISH, O.PARTING, O.THREADING)
        inertia = D ** 4 / 12.0 if square else math.pi * D ** 4 / 64.0
        e_mod = 210_000.0 if turning else tt.e_modulus
        deflection = fc * tool.overhang ** 3 / (3.0 * e_mod * inertia)
        allowed = (0.02 if par.ra <= 1.6 else 0.04 if par.ra <= 3.2 else 0.08) * rig
        if deflection > 2 * allowed:
            note(Level.ERROR, f"Прогиб ≈ {deflection:.3f} мм (доп. ≈ {allowed:.3f} мм). "
                              f"Уменьшите вылет, ap или подачу.", "rigidity")
        elif deflection > allowed:
            note(Level.WARNING, f"Повышенный прогиб ≈ {deflection:.3f} мм (доп. ≈ {allowed:.3f} мм).", "rigidity")
    if turning:
        note(Level.INFO, "Для токарных операций рекомендуется постоянная скорость резания (G96).")

    msgs.sort(key=lambda m: -int(m.level))
    factors = [("vc справочная, м/мин", mat.vc_ref), ("K твёрдости", k_hard),
               ("K материала инструмента", k_mat), ("K покрытия", k_coat),
               (f"K стойкости (T={life:g} мин)", k_life), ("K операции", k_op),
               ("K геометрии среза", k_geom), ("K жёсткости СПИД (vc)", k_rig_v),
               ("K вылета (vc)", math.sqrt(k_oh))]
    return CuttingResult(n=n, n_theoretical=n_th, vc=vc_c, vc_target=vc_target, fn=fn_c, fz=fz_c,
                         vf=vf_c, ap=ap, ae=ae, passes=passes, hm=h, kc=kc, fc=fc, p_cut=p_cut,
                         p_spindle=p_spindle, load_pct=load, torque=torque, q=q, time_min=time_min,
                         ra_est=ra_est, deflection=deflection, hb=hb, flags=flags,
                         messages=msgs, factors=factors)
