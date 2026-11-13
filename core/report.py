"""Экспорт отчёта: Markdown / CSV."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from . import catalog as cat
from .models import CuttingInput, CuttingResult

Row = Tuple[str, str, str, str]


def _f(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}".rstrip("0").rstrip(".") if nd else f"{x:.0f}"


def hardness_text(inp: CuttingInput, hb: float) -> str:
    h = inp.hardness
    if h.kind == "default":
        return f"справочная, ≈ {hb:.0f} HB"
    unit = {"HB": "HB", "HRC": "HRC", "Rm": "МПа"}[h.kind]
    return f"{_f(h.value, 1)} {unit} (≈ {hb:.0f} HB)"


def input_rows(inp: CuttingInput, hb: float | None = None) -> List[Row]:
    m, t, p, ma = inp.material, inp.tool, inp.params, inp.machine
    fl = cat.OP_FIELDS[inp.operation]
    hb = hb if hb is not None else m.hb_ref
    rows: List[Row] = [
        ("Операция", "Вид обработки", inp.operation.category.value, ""),
        ("Операция", "Операция", inp.operation.title, ""),
        ("Материал", "Марка", m.name, ""),
        ("Материал", "Группа ISO", m.iso, ""),
        ("Материал", "Твёрдость/прочность", hardness_text(inp, hb), ""),
        ("Материал", "kc1.1", _f(m.kc11, 0), "Н/мм²"),
        ("Материал", "mc", _f(m.mc, 2), ""),
    ]
    if m.density_g_cm3 is not None:
        rows.append(("Материал", "Плотность ρ", _f(m.density_g_cm3, 2), "г/см³"))
    if m.e_gpa is not None:
        rows.append(("Материал", "Модуль упругости E", _f(m.e_gpa, 0), "ГПа"))
    if m.rm_mpa is not None:
        rows.append(("Материал", "Предел прочности Rm", _f(m.rm_mpa, 0), "МПа"))
    if m.ys_mpa is not None:
        rows.append(("Материал", "Предел текучести", _f(m.ys_mpa, 0), "МПа"))
    if m.applications:
        rows.append(("Материал", "Типовое применение", m.applications, ""))
    if m.source:
        rows.append(("Материал", "Источник", m.source, ""))
    rows += [("Инструмент", "Тип", t.tool_type.name, ""),
             ("Инструмент", "Покрытие", "да" if t.coated else "нет", ""),
             ("Инструмент", "Диаметр D (сечение)", _f(t.diameter), "мм")]
    if "z" in fl:
        rows.append(("Инструмент", "Число зубьев z", str(t.teeth), "шт"))
    rows.append(("Инструмент", "Вылет L", _f(t.overhang), "мм"))
    if "radius" in fl:
        rows.append(("Инструмент", "Радиус при вершине r", _f(t.corner_radius), "мм"))
    if "dw" in fl:
        rows.append(("Параметры", "Диаметр обработки", _f(p.workpiece_diameter), "мм"))
    if "ap" in fl:
        rows.append(("Параметры", "Ширина реза" if inp.operation.name == "PARTING" else "Глубина ap",
                     _f(p.ap), "мм"))
    if "ae" in fl:
        rows.append(("Параметры", "Ширина фрезерования ae", _f(p.ae), "мм"))
    if "pitch" in fl:
        rows.append(("Параметры", "Шаг резьбы", _f(p.pitch, 3), "мм"))
    if "d0" in fl:
        rows.append(("Параметры", "Диаметр предв. отверстия", _f(p.pre_hole), "мм"))
    if "ra" in fl:
        rows.append(("Параметры", "Требуемая Ra", _f(p.ra, 1), "мкм"))
    rows += [("Параметры", "Длина обработки/глубина", _f(p.length), "мм"),
             ("Параметры", "Стойкость T", _f(p.tool_life, 0), "мин"),
             ("Станок", "n_max", _f(ma.n_max, 0), "об/мин"),
             ("Станок", "Мощность привода", _f(ma.power_kw), "кВт"),
             ("Станок", "КПД η", _f(ma.efficiency), ""),
             ("Станок", "Жёсткость СПИД", cat.RIGIDITY[ma.rigidity][0], "")]
    return rows


def result_rows(inp: CuttingInput, r: CuttingResult) -> List[Row]:
    rows: List[Row] = [
        ("Режимы", "Частота вращения n", _f(r.n, 0), "об/мин"),
        ("Режимы", "Скорость резания vc (факт.)", _f(r.vc, 1), "м/мин"),
        ("Режимы", "Скорость резания vc (расчётная)", _f(r.vc_target, 1), "м/мин"),
        ("Режимы", "Подача на оборот fn", _f(r.fn, 3), "мм/об"),
        ("Режимы", "Подача на зуб fz", _f(r.fz, 3), "мм/зуб"),
        ("Режимы", "Минутная подача vf", _f(r.vf, 0), "мм/мин"),
        ("Режимы", "Глубина ap" + (" (за проход)" if r.passes > 1 else ""), _f(r.ap), "мм"),
    ]
    if r.ae is not None:
        rows.append(("Режимы", "Ширина фрезерования ae", _f(r.ae), "мм"))
    if r.passes > 1:
        rows.append(("Режимы", "Число проходов", str(r.passes), "шт"))
    rows += [
        ("Силы/мощность", "Толщина стружки h", _f(r.hm, 3), "мм"),
        ("Силы/мощность", "Удельная сила kc", _f(r.kc, 0), "Н/мм²"),
        ("Силы/мощность", "Сила резания Fc", _f(r.fc, 0), "Н"),
        ("Силы/мощность", "Мощность резания", _f(r.p_cut, 2), "кВт"),
        ("Силы/мощность", "Мощность на шпинделе", _f(r.p_spindle, 2), "кВт"),
        ("Силы/мощность", "Загрузка мощности", _f(r.load_pct, 0), "%"),
        ("Силы/мощность", "Крутящий момент", _f(r.torque, 1), "Н·м"),
        ("Производительность", "Съём Q", "—" if r.q is None else _f(r.q, 1), "см³/мин"),
        ("Производительность", "Основное время", _f(r.time_min, 2), "мин"),
    ]
    if r.ra_est is not None:
        rows.append(("Качество", "Расчётная Ra", _f(r.ra_est, 2), "мкм"))
    if r.deflection is not None:
        rows.append(("Качество", "Прогиб инструмента (оценка)", _f(r.deflection, 3), "мм"))
    return rows


def to_markdown(inp: CuttingInput, r: CuttingResult) -> str:
    L = [f"# Карта режимов резания — {inp.operation.title}", "",
         f"*Сформировано: {datetime.now():%d.%m.%Y %H:%M}*", "",
         "## 1. Исходные данные", "", "| Раздел | Параметр | Значение |", "|---|---|---|"]
    for s, n, v, u in input_rows(inp, r.hb):
        L.append(f"| {s} | {n} | {v} {u} |".replace("  |", " |"))
    L += ["", "## 2. Рассчитанные режимы", "", "| Раздел | Параметр | Значение |", "|---|---|---|"]
    for s, n, v, u in result_rows(inp, r):
        L.append(f"| {s} | {n} | **{v}** {u} |")
    L += ["", "## 3. Замечания", ""]
    icons = {0: "✅", 1: "ℹ️", 2: "⚠️", 3: "⛔"}
    L += [f"- {icons[int(m.level)]} {m.text}" for m in r.messages] or ["- ✅ Замечаний нет."]
    L += ["", "## 4. Коэффициенты vc", "", "| Коэффициент | Значение |", "|---|---|"]
    L += [f"| {n} | {_f(v, 3)} |" for n, v in r.factors]
    L += ["", "## 5. Формулы", "",
          "- n = vc·1000/(π·D);  vf = fz·z·n",
          "- Q = ap·ae·vf/1000 (фрезерование), см³/мин;  Q = ap·f·vc (точение)",
          "- kc = kc1.1·h^(−mc);  P = ap·ae·vf·kc/(60·10⁶) (фрезерование)",
          "- vc = vc_ref·K_тверд·K_инстр·K_покр·(60/T)^n·K_опер·K_геом·K_жёстк",
          "- Ra ≈ f²/(32·r)·1000 (точение)", "",
          "> Ориентировочный расчёт (источники — в core/catalog.py). "
          "Окончательные режимы — по каталогу производителя инструмента.", ""]
    return "\n".join(L)


def to_csv(inp: CuttingInput, r: CuttingResult) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Раздел", "Параметр", "Значение", "Ед. изм."])
    for row in input_rows(inp, r.hb) + result_rows(inp, r):
        w.writerow(row)
    for m in r.messages:
        w.writerow(["Замечания", m.level.name, m.text, ""])
    return buf.getvalue()


def save_report(path: str, inp: CuttingInput, r: CuttingResult) -> None:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        p.write_text(to_csv(inp, r), encoding="utf-8-sig", newline="")
    else:
        p.write_text(to_markdown(inp, r), encoding="utf-8")
