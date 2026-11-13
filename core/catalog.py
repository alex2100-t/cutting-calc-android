"""Справочник материалов, режущего инструмента и оборудования.

ВЕРСИЯ 2.0 (2025). Все справочные таблицы — ТОЛЬКО здесь.

ИСТОЧНИКИ (см. также поле source каждой записи):
  ГОСТ 1050-2013 (стали углеродистые), ГОСТ 4543-2016 (легированные),
  ГОСТ 5632-2014 (нерж./жаропрочные), ГОСТ 5950-2000 (инструментальные),
  ГОСТ 801-78 (ШХ15), ГОСТ 19265-73 (Р6М5, Р18), ГОСТ 3882-74 (ВК/ТК сплавы),
  ГОСТ 1412-85 (СЧ), ГОСТ 7293-85 (ВЧ), ГОСТ 4784-2019 (Al деформируемые),
  ГОСТ 1583-93 (Al литейные), ГОСТ 859-2001 (медь), ГОСТ 15527-2004 (латунь),
  ГОСТ 18175-78 (бронза), ГОСТ 19807-91 (титан), ASTM B637 / AMS 5662 (Inconel 718),
  паспорта станков 16К20, 1К62, 6Р13, 2Н135; каталоги Haas VF-2, DMG MORI DMU 50;
  методика kc1.1/mc и справочные vc — Sandvik Coromant (ориентировочно).

None + «требует уточнения» = надёжных данных нет; «среднее» не подставляем.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Tuple

from .models import Material, Operation, ToolType

O = Operation
CATALOG_VERSION = "2.0 (2025)"

ISO_GROUPS: Dict[str, str] = {
    "P": "P — углеродистые и легированные стали",
    "M": "M — нержавеющие стали",
    "S": "S — жаропрочные сплавы и титан",
    "N": "N — алюминий и цветные сплавы",
    "K": "K — чугуны",
    "H": "H — закалённые стали (≥ 45 HRC)",
}


def _m(key, name, iso, *, kc11, mc, vc, hb_ref, hb_min, hb_max, v_hard_exp=1.2,
       density=None, e_gpa=None, rm=None, ys=None, apps="", source="") -> Material:
    """Конструктор материала. Единицы: г/см³, ГПа, МПа, HB, м/мин."""
    return Material(key=key, name=name, iso=iso, kc11=kc11, mc=mc, vc_ref=vc,
                    hb_ref=hb_ref, hb_min=hb_min, hb_max=hb_max, v_hard_exp=v_hard_exp,
                    density_g_cm3=density, e_gpa=e_gpa, rm_mpa=rm, ys_mpa=ys,
                    applications=apps, source=source)


_MATERIALS = [
    # Углеродистые стали — ГОСТ 1050-2013
    _m("st20", "Сталь 20", "P", kc11=1500, mc=0.25, vc=250, hb_ref=140, hb_min=110, hb_max=170,
       density=7.85, e_gpa=210, rm=412, ys=245, apps="валы, оси, крепёж; хорошо цементируется",
       source="ГОСТ 1050-2013"),
    _m("st35", "Сталь 35", "P", kc11=1600, mc=0.25, vc=215, hb_ref=180, hb_min=150, hb_max=210,
       density=7.85, e_gpa=210, rm=530, ys=315, apps="улучшаемые детали: валы, шестерни",
       source="ГОСТ 1050-2013"),
    _m("st45", "Сталь 45", "P", kc11=1650, mc=0.25, vc=205, hb_ref=200, hb_min=170, hb_max=240,
       density=7.85, e_gpa=210, rm=598, ys=353, apps="универсальная конструкционная сталь",
       source="ГОСТ 1050-2013"),
    # Легированные — ГОСТ 4543-2016 (свойства после улучшения)
    _m("st40h", "Сталь 40Х", "P", kc11=1750, mc=0.25, vc=185, hb_ref=230, hb_min=200, hb_max=280,
       density=7.82, e_gpa=210, rm=980, ys=785, apps="валы, шестерни, пальцы",
       source="ГОСТ 4543-2016"),
    _m("st30hgsa", "Сталь 30ХГСА", "P", kc11=1900, mc=0.25, vc=160, hb_ref=250, hb_min=220, hb_max=300,
       density=7.76, e_gpa=210, rm=1080, ys=835, apps="высокопрочные детали (шасси)",
       source="ГОСТ 4543-2016"),
    # Нержавеющие — ГОСТ 5632-2014
    _m("12h18n10t", "12Х18Н10Т", "M", kc11=1950, mc=0.21, vc=130, hb_ref=170, hb_min=140, hb_max=200,
       density=7.90, e_gpa=196, rm=520, ys=205, apps="пищевое/химическое оборудование, трубопроводы",
       source="ГОСТ 5632-2014"),
    _m("10h17n13m3t", "10Х17Н13М3Т", "M", kc11=2050, mc=0.21, vc=115, hb_ref=180, hb_min=150, hb_max=210,
       density=7.95, e_gpa=196, rm=530, ys=235, apps="агрессивные среды, нефтехимия",
       source="ГОСТ 5632-2014"),
    _m("20h13", "20Х13 (после т/о)", "M", kc11=1800, mc=0.22, vc=150, hb_ref=220, hb_min=190, hb_max=260,
       density=7.75, e_gpa=210, rm=660, ys=440, apps="клапаны, лопатки, арматура",
       source="ГОСТ 5632-2014"),
    _m("40h13", "40Х13 (закалённая ~50 HRC)", "H", kc11=3400, mc=0.25, vc=70, hb_ref=500, hb_min=450, hb_max=550,
       density=7.75, e_gpa=210, rm=None, ys=None,  # требует уточнения: зависит от отпуска
       apps="ножи, инструмент, коррозионностойкие подшипники", source="ГОСТ 5632-2014"),
    # Жаропрочные и титан (S)
    _m("hn77tyur", "ХН77ТЮР (ЭИ437Б)", "S", kc11=2600, mc=0.25, vc=40, hb_ref=290, hb_min=255, hb_max=321,
       density=8.20, e_gpa=210, rm=950, ys=None, apps="детали ГТД до ~800 °C",
       source="ГОСТ 5632-2014 (HB 255–321)"),
    _m("in718", "Inconel 718 (состаренный)", "S", kc11=2900, mc=0.25, vc=35, hb_ref=350, hb_min=331, hb_max=388,
       density=8.19, e_gpa=205, rm=1240, ys=1035, apps="диски/валы ГТД, крепёж до ~650 °C",
       source="ASTM B637 / AMS 5662-5663"),
    _m("vt6", "ВТ6 (Ti-6Al-4V)", "S", kc11=1400, mc=0.23, vc=55, hb_ref=330, hb_min=300, hb_max=370,
       density=4.43, e_gpa=112, rm=900, ys=830, apps="лопатки компрессора, авиадетали",
       source="ГОСТ 19807-91 / AMS 4928"),
    _m("vt10", "ВТ1-0", "S", kc11=1100, mc=0.23, vc=70, hb_ref=150, hb_min=120, hb_max=200,
       density=4.50, e_gpa=105, rm=343, ys=275, apps="сварные конструкции, листы",
       source="ГОСТ 19807-91 (отожжённый)"),
    # Алюминий — ГОСТ 4784-2019 / ГОСТ 1583-93
    _m("d16t", "Д16Т", "N", kc11=700, mc=0.25, vc=400, hb_ref=110, hb_min=90, hb_max=130, v_hard_exp=0.4,
       density=2.78, e_gpa=71, rm=420, ys=294, apps="деформируемые полуфабрикаты, обшивка",
       source="ГОСТ 4784-2019"),
    _m("ak12", "АК12 (силумин, литьё)", "N", kc11=800, mc=0.25, vc=450, hb_ref=70, hb_min=50, hb_max=100, v_hard_exp=0.4,
       density=2.66, e_gpa=71, rm=160, ys=None,  # требует уточнения: зависит от способа литья
       apps="литые детали ДВС (картеры, поршни)", source="ГОСТ 1583-93"),
    _m("amg6", "АМг6", "N", kc11=650, mc=0.25, vc=350, hb_ref=75, hb_min=60, hb_max=90, v_hard_exp=0.4,
       density=2.66, e_gpa=70, rm=320, ys=160, apps="сварные конструкции, судостроение",
       source="ГОСТ 4784-2019"),
    _m("ad31t6", "АД31Т6 (≈6063-T6)", "N", kc11=600, mc=0.25, vc=500, hb_ref=75, hb_min=65, hb_max=85, v_hard_exp=0.4,
       density=2.70, e_gpa=69, rm=215, ys=170, apps="профили, радиаторы",
       source="ГОСТ 4784-2019"),
    # Медь/латунь/бронза
    _m("m1", "Медь М1 (мягкая)", "N", kc11=750, mc=0.25, vc=250, hb_ref=50, hb_min=45, hb_max=110, v_hard_exp=0.4,
       density=8.94, e_gpa=120, rm=220, ys=None, apps="токоведущие детали, теплообменники",
       source="ГОСТ 859-2001"),
    _m("l63", "Латунь Л63", "N", kc11=750, mc=0.25, vc=250, hb_ref=80, hb_min=60, hb_max=110, v_hard_exp=0.4,
       density=8.44, e_gpa=103, rm=340, ys=None, apps="хорошо обрабатывается резанием",
       source="ГОСТ 15527-2004"),
    _m("brazh94", "Бронза БрАЖ9-4", "N", kc11=900, mc=0.25, vc=180, hb_ref=140, hb_min=110, hb_max=180, v_hard_exp=0.4,
       density=7.50, e_gpa=110, rm=490, ys=None, apps="втулки, червячные колёса, арматура",
       source="ГОСТ 18175-78"),
    # Чугуны — ГОСТ 1412-85 / ГОСТ 7293-85
    _m("sch20", "СЧ20", "K", kc11=1100, mc=0.28, vc=180, hb_ref=205, hb_min=170, hb_max=241,
       density=7.15, e_gpa=100, rm=200, ys=None, apps="станины, корпуса, маховики",
       source="ГОСТ 1412-85"),
    _m("sch25", "СЧ25", "K", kc11=1250, mc=0.28, vc=165, hb_ref=215, hb_min=180, hb_max=250,
       density=7.20, e_gpa=105, rm=250, ys=None, apps="детали повышенной прочности",
       source="ГОСТ 1412-85"),
    _m("vch50", "ВЧ50", "K", kc11=1350, mc=0.28, vc=160, hb_ref=220, hb_min=170, hb_max=260,
       density=7.20, e_gpa=160, rm=500, ys=320, apps="коленвалы, шестерни (замена стали)",
       source="ГОСТ 7293-85"),
    # Закалённая сталь (H) — ГОСТ 801-78
    _m("shh15_60hrc", "ШХ15 закалённая (60–64 HRC)", "H", kc11=3800, mc=0.25, vc=60,
       hb_ref=620, hb_min=560, hb_max=650, density=7.80, e_gpa=210, rm=None, ys=None,
       apps="подшипники качения, детали ≥ 60 HRC", source="ГОСТ 801-78"),
]

MATERIALS: Dict[str, Material] = {m.key: m for m in _MATERIALS}


# ── Марки инструментальных материалов (единицы: HRC/HRA, °C, г/см³, ГПа, МПа, HV) ──
TOOL_GRADES = {
    "r6m5":     dict(kind="HSS", name="Р6М5", standard="ГОСТ 19265-73", hrc=(63, 66),
                     red_hardness_c=620, density_g_cm3=8.10, e_gpa=220, bend_mpa=(3000, 3500),
                     use="универсальная HSS: свёрла, фрезы, метчики"),
    "r6m5k5":   dict(kind="HSS-Co", name="Р6М5К5", standard="ГОСТ 19265-73", hrc=(64, 67),
                     red_hardness_c=640, density_g_cm3=8.10, e_gpa=220, bend_mpa=(2800, 3200),
                     use="HSS+Co: нержавеющие и жаропрочные стали"),
    "r18":      dict(kind="HSS", name="Р18", standard="ГОСТ 19265-73", hrc=(63, 65),
                     red_hardness_c=620, density_g_cm3=8.70, e_gpa=220, bend_mpa=(2700, 3400),
                     use="ходовая марка HSS"),
    "vk8":      dict(kind="WC-Co", name="ВК8", standard="ГОСТ 3882-74", hra=89.0,
                     bend_mpa=(1470, 1670), density_g_cm3=14.60, e_gpa=600,
                     use="чугуны, цветные металлы, черновая сталь"),
    "vk6":      dict(kind="WC-Co", name="ВК6", standard="ГОСТ 3882-74", hra=88.5,
                     bend_mpa=(1320, 1760), density_g_cm3=14.80, e_gpa=630,
                     use="универсальный сплав сталь/чугун"),
    "vk6om":    dict(kind="WC-Co мелкозернистый", name="ВК6-ОМ", standard="ГОСТ 3882-74",
                     hra=90.5, bend_mpa=(1470, 1760), density_g_cm3=14.90, e_gpa=640,
                     use="фрезерование с ударом, чистовая"),
    "t15k6":    dict(kind="WC-TiC-Co", name="Т15К6", standard="ГОСТ 3882-74", hra=90.0,
                     bend_mpa=(1130, 1320), density_g_cm3=11.10, e_gpa=540,
                     use="чистовая/получистовая сталь"),
    "t5k10":    dict(kind="WC-TiC-Co", name="Т5К10", standard="ГОСТ 3882-74", hra=91.0,
                     bend_mpa=(1270, 1470), density_g_cm3=12.30, e_gpa=560,
                     use="черновая сталь, прерывистое резание"),
    "t30k4":    dict(kind="WC-TiC-Co", name="Т30К4", standard="ГОСТ 3882-74", hra=92.0,
                     bend_mpa=(880, 1080), density_g_cm3=9.50, e_gpa=480,
                     use="чистовая сталь на высоких скоростях"),
    "tin":      dict(kind="PVD-покрытие", name="TiN", microhardness_hv=(2000, 2400), max_temp_c=600,
                     use="универсальное покрытие HSS и тв. сплава"),
    "tialn":    dict(kind="PVD-покрытие", name="TiAlN/AlTiN", microhardness_hv=(3000, 3500), max_temp_c=900,
                     use="скоростная обработка стали, сухое резание"),
    "dlc":      dict(kind="покрытие", name="DLC", microhardness_hv=(2000, 3000), max_temp_c=400,  # требует уточнения
                     use="алюминий: предотвращает налипание"),
    "pcd":      dict(kind="PCD", name="Поликристаллический алмаз", hardness_hv=None, max_temp_c=600,  # требует уточнения
                     use="Al с высоким Si, композиты, медь; НЕ для стали"),
    "cbn":      dict(kind="CBN", name="Кубический нитрид бора", hardness_hv=(3000, 4500), max_temp_c=1200,
                     use="закалённые стали 45–65 HRC, отбеленный чугун"),
}


def _vc(P=None, M=None, S=None, N=None, K=None, H=None) -> Dict[str, Optional[float]]:
    return {"P": P, "M": M, "S": S, "N": N, "K": K, "H": H}


TOOL_TYPES: Dict[str, ToolType] = {
    "carbide": ToolType("carbide", "Твёрдый сплав (пластины/монолит)",
                        _vc(P=1.0, M=1.0, S=1.0, N=1.0, K=1.0, H=1.0),
                        taylor_n=0.25, feed_factor=1.0, coating_factors=(1.0, 0.8),
                        supports_coating=True, e_modulus=500_000,
                        notes={"H": "На закалённых сталях низкая стойкость — лучше CBN."}),
    "hss": ToolType("hss", "Быстрорежущая сталь HSS (Р6М5, Р6М5К5, Р18 — см. TOOL_GRADES)",
                    _vc(P=0.22, M=0.18, S=0.10, N=0.25, K=0.20, H=None),
                    taylor_n=0.125, feed_factor=0.6, coating_factors=(1.25, 1.0),
                    supports_coating=True, e_modulus=210_000,
                    notes={"S": "HSS на жаропрочных сплавах — крайне низкая стойкость."}),
    "pcd": ToolType("pcd", "PCD (поликристаллический алмаз)", _vc(N=2.2),
                    taylor_n=0.35, feed_factor=0.9, coating_factors=(1.0, 1.0),
                    supports_coating=False, e_modulus=210_000),
    "cbn": ToolType("cbn", "CBN (кубический нитрид бора)", _vc(S=3.0, K=3.0, H=2.8),
                    taylor_n=0.35, feed_factor=0.5, coating_factors=(1.0, 1.0),
                    supports_coating=False, e_modulus=210_000,
                    notes={"S": "CBN на жаропрочных сплавах — ограниченно, чистовая."}),
}


# ── Классификация и примеры станков (единицы: power_kw — кВт, n_max — об/мин, mass_kg — кг) ──
MACHINE_CLASSES = {
    "lathe_universal": dict(name="Токарно-винторезный универсальный", power_kw=(5.5, 15.0),
                            n_max=(1000, 2000), source="паспорта 16К20, 1К62, CU-325"),
    "lathe_cnc":       dict(name="Токарный станок с ЧПУ", power_kw=(11.0, 30.0),
                            n_max=(3000, 6000), source="каталоги DMG MORI, Haas — сверьте по модели"),
    "drilling":        dict(name="Сверлильный станок", power_kw=(1.5, 7.5),
                            n_max=(500, 4000), source="паспорт 2Н135"),
    "boring":          dict(name="Расточной станок", power_kw=(5.5, 22.0),
                            n_max=(800, 3000), source="паспорта станков — требует уточнения по модели"),
    "mill_console":    dict(name="Вертикально-фрезерный консольный", power_kw=(4.0, 11.0),
                            n_max=(400, 2000), source="паспорт 6Р13"),
    "vmc":             dict(name="Вертикальный обрабатывающий центр", power_kw=(7.5, 30.0),
                            n_max=(6000, 15000), source="каталоги Haas VF, DMG MORI DMU"),
    "hmc":             dict(name="Горизонтальный обрабатывающий центр", power_kw=(15.0, 45.0),
                            n_max=(4000, 12000), source="каталоги DMG MORI NHX, Mazak HCN"),
    "grinder_cyl":     dict(name="Круглошлифовальный станок", power_kw=(2.2, 15.0),
                            n_max=(1000, 3000), source="паспорта — требует уточнения"),
}

MACHINE_EXAMPLES = [
    dict(model="16К20", cls="lathe_universal", power_kw=10.0, n_min=12.5, n_max=1600.0,
         mass_kg=2980, tool_magazine=None, source="паспорт 16К20 (завод «Красный пролетарий»)"),
    dict(model="1К62", cls="lathe_universal", power_kw=None,  # требует уточнения: 7,5–10 кВт по паспортам
         n_min=12.5, n_max=2000.0, mass_kg=None, tool_magazine=None, source="паспорт 1К62"),
    dict(model="6Р13", cls="mill_console", power_kw=7.5, n_min=40.0, n_max=2000.0,
         mass_kg=4250, tool_magazine=None, source="паспорт 6Р13"),
    dict(model="2Н135", cls="drilling", power_kw=4.0, n_min=31.5, n_max=1400.0,
         mass_kg=1200, tool_magazine=None, source="паспорт 2Н135"),
    dict(model="Haas VF-2", cls="vmc", power_kw=22.4, n_min=None, n_max=8100.0,
         mass_kg=3948, tool_magazine=21, source="haascnc.com (30 л.с. = 22,4 кВт; 20+1 в магазине)"),
    dict(model="DMG MORI DMU 50", cls="vmc", power_kw=15.0, n_min=None, n_max=20000.0,
         mass_kg=None,  # требует уточнения (~3,4 т)
         tool_magazine=30, source="dmgmori.com; 15 кВт — макс. исполнение, базовое 9 кВт"),
]

# Шаблоны для мастера (шаг «Станок»)
MACHINE_PRESETS = {
    "lathe_universal": dict(name="Токарно-винторезный универсальный (16К20 и др.)",
                            n_max=1600, power_kw=10.0, efficiency=0.80, rigidity="medium"),
    "lathe_cnc":       dict(name="Токарный станок с ЧПУ",
                            n_max=4000, power_kw=15.0, efficiency=0.85, rigidity="high"),
    "drilling":        dict(name="Сверлильный (2Н135 и др.)",
                            n_max=1400, power_kw=4.0, efficiency=0.75, rigidity="medium"),
    "boring":          dict(name="Расточной станок",
                            n_max=1250, power_kw=11.0, efficiency=0.82, rigidity="low"),
    "mill_console":    dict(name="Вертикально-фрезерный консольный (6Р13)",
                            n_max=2000, power_kw=7.5, efficiency=0.80, rigidity="medium"),
    "vmc":             dict(name="Вертикальный обрабатывающий центр (VF-2, DMU 50)",
                            n_max=8100, power_kw=22.0, efficiency=0.85, rigidity="high"),
    "hmc":             dict(name="Горизонтальный обрабатывающий центр",
                            n_max=6000, power_kw=30.0, efficiency=0.85, rigidity="high"),
    "grinder_cyl":     dict(name="Круглошлифовальный станок",
                            n_max=2000, power_kw=5.5, efficiency=0.75, rigidity="high"),
    "manual":          dict(name="Ввести вручную…", n_max=6000, power_kw=11.0,
                            efficiency=0.85, rigidity="medium"),
}


# ── Коэффициенты операций (ориентировочно, методика Sandvik) ──
OP_VC_FACTOR = {
    O.TURN_ROUGH: 0.85, O.TURN_FINISH: 1.15, O.BORING: 0.80, O.PARTING: 0.60,
    O.THREADING: 0.50, O.FACE_MILL: 1.00, O.END_SLOT: 0.65, O.END_CONTOUR: 0.85,
    O.DRILLING: 0.50, O.COUNTERBORING: 0.55,
}
TURN_FEED = {"P": 0.40, "M": 0.30, "S": 0.20, "N": 0.35, "K": 0.35, "H": 0.12}
OP_FEED_TURN = {O.TURN_ROUGH: 1.0, O.TURN_FINISH: 0.4, O.BORING: 0.7, O.PARTING: 0.25}
MILL_FZ = {"P": 0.12, "M": 0.10, "S": 0.06, "N": 0.15, "K": 0.12, "H": 0.04}
OP_FEED_MILL = {O.FACE_MILL: 1.0, O.END_SLOT: 0.8, O.END_CONTOUR: 1.0}
DRILL_COEF = {"P": 0.015, "M": 0.012, "S": 0.008, "N": 0.025, "K": 0.020, "H": 0.005}
THREAD_AP_PASS = {"P": 0.15, "M": 0.10, "S": 0.08, "N": 0.20, "K": 0.15, "H": 0.05}
KAPPA = {O.FACE_MILL: 45.0}
OP_LD_LIMITS = {
    O.TURN_ROUGH: (2.5, 4.0), O.TURN_FINISH: (2.5, 4.0), O.BORING: (4.0, 7.0),
    O.PARTING: (3.0, 5.0), O.THREADING: (2.5, 4.0), O.FACE_MILL: (2.0, 3.0),
    O.END_SLOT: (3.0, 5.0), O.END_CONTOUR: (3.0, 5.0),
    O.DRILLING: (4.0, 8.0), O.COUNTERBORING: (3.0, 5.0),
}
RIGIDITY = {
    "high": ("Высокая (жёсткая деталь, короткий вылет)", 1.00),
    "medium": ("Средняя (типовая система СПИД)", 0.85),
    "low": ("Низкая (тонкая деталь, длинный вылет, слабое крепление)", 0.70),
}
RA_VALUES = [12.5, 6.3, 3.2, 1.6, 0.8, 0.4]
OP_FIELDS: Dict[Operation, FrozenSet[str]] = {
    O.TURN_ROUGH: frozenset({"dw", "ap", "ra", "radius"}),
    O.TURN_FINISH: frozenset({"dw", "ap", "ra", "radius"}),
    O.BORING: frozenset({"dw", "ap", "ra", "radius"}),
    O.PARTING: frozenset({"dw", "ap", "radius"}),
    O.THREADING: frozenset({"dw", "pitch"}),
    O.FACE_MILL: frozenset({"ap", "ae", "ra", "z"}),
    O.END_SLOT: frozenset({"ap", "ra", "z"}),
    O.END_CONTOUR: frozenset({"ap", "ae", "ra", "z"}),
    O.DRILLING: frozenset({"z"}),
    O.COUNTERBORING: frozenset({"d0", "z"}),
}
OP_DESCRIPTIONS = {
    O.TURN_ROUGH: "Продольное точение, максимальный съём. Подача ограничена Ra и радиусом r.",
    O.TURN_FINISH: "Чистовое точение: подача определяется Ra и r (Ra ≈ f²/(32·r)).",
    O.BORING: "Растачивание борштангой. Важны вылет L/D и жёсткость оправки.",
    O.PARTING: "Отрезка/канавка. Ширина реза вводится как «глубина» ap.",
    O.THREADING: "Резьба резцом: подача = шаг; проходы — по глубине профиля.",
    O.FACE_MILL: "Торцевая фреза со сменными пластинами (κ = 45°).",
    O.END_SLOT: "Концевая фреза в полном контакте (ae = D): паз.",
    O.END_CONTOUR: "Концевая фреза, контур с ae < D (утонение стружки).",
    O.DRILLING: "Сверление; подача на оборот пропорциональна диаметру.",
    O.COUNTERBORING: "Зенкерование предварительного отверстия.",
}
TOOL_DEFAULTS = {
    O.TURN_ROUGH: dict(d=25, z=1, l=40, r=0.8), O.TURN_FINISH: dict(d=25, z=1, l=40, r=0.4),
    O.BORING: dict(d=20, z=1, l=80, r=0.4), O.PARTING: dict(d=25, z=1, l=30, r=0.2),
    O.THREADING: dict(d=25, z=1, l=35, r=0.1), O.FACE_MILL: dict(d=63, z=5, l=50, r=0.8),
    O.END_SLOT: dict(d=12, z=3, l=30, r=0.0), O.END_CONTOUR: dict(d=12, z=4, l=30, r=0.0),
    O.DRILLING: dict(d=12, z=2, l=40, r=0.0), O.COUNTERBORING: dict(d=20, z=3, l=40, r=0.0),
}
PARAM_DEFAULTS = {
    O.TURN_ROUGH: dict(dw=60, length=50, ap=2.5, ae=10, pitch=2, d0=0, ra=6.3),
    O.TURN_FINISH: dict(dw=60, length=50, ap=0.3, ae=10, pitch=2, d0=0, ra=1.6),
    O.BORING: dict(dw=40, length=40, ap=1.0, ae=10, pitch=2, d0=0, ra=3.2),
    O.PARTING: dict(dw=40, length=20, ap=3.0, ae=10, pitch=2, d0=0, ra=12.5),
    O.THREADING: dict(dw=24, length=30, ap=1, ae=10, pitch=2.0, d0=0, ra=6.3),
    O.FACE_MILL: dict(dw=60, length=200, ap=2.0, ae=40, pitch=2, d0=0, ra=3.2),
    O.END_SLOT: dict(dw=60, length=100, ap=6.0, ae=12, pitch=2, d0=0, ra=6.3),
    O.END_CONTOUR: dict(dw=60, length=150, ap=10.0, ae=3, pitch=2, d0=0, ra=3.2),
    O.DRILLING: dict(dw=60, length=30, ap=6, ae=12, pitch=2, d0=0, ra=12.5),
    O.COUNTERBORING: dict(dw=60, length=30, ap=2, ae=10, pitch=2, d0=16, ra=6.3),
}
HARDNESS_KINDS = [
    ("default", "Справочная (типовая для марки)"),
    ("HB", "Твёрдость по Бринеллю, HB"),
    ("HRC", "Твёрдость по Роквеллу, HRC"),
    ("Rm", "Предел прочности Rm, МПа"),
]
