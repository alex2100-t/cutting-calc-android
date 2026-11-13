"""Модели данных: перечисления, входные данные и результат расчёта."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Tuple


class Category(Enum):
    TURNING = "Токарная обработка"
    MILLING = "Фрезерная обработка"


class Operation(Enum):
    TURN_ROUGH = ("Точение черновое", Category.TURNING)
    TURN_FINISH = ("Точение чистовое", Category.TURNING)
    BORING = ("Растачивание", Category.TURNING)
    PARTING = ("Отрезка", Category.TURNING)
    THREADING = ("Нарезание резьбы (резцом)", Category.TURNING)
    FACE_MILL = ("Торцевое фрезерование", Category.MILLING)
    END_SLOT = ("Концевое фрезерование: паз", Category.MILLING)
    END_CONTOUR = ("Концевое фрезерование: контур", Category.MILLING)
    DRILLING = ("Сверление", Category.MILLING)
    COUNTERBORING = ("Зенкерование", Category.MILLING)

    def __init__(self, title: str, category: Category):
        self.title = title
        self.category = category


class Level(IntEnum):
    OK = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


@dataclass(frozen=True)
class Material:
    key: str
    name: str
    iso: str                  # группа ISO 6983: P, M, S, N, K, H
    kc11: float               # удельная сила резания kc1.1, Н/мм² (методика Sandvik)
    mc: float                 # показатель степени mc
    vc_ref: float             # справочная vc (тв. сплав с покрытием, T=60 мин), м/мин
    hb_ref: float             # типовая твёрдость HB
    hb_min: float
    hb_max: float
    v_hard_exp: float = 1.2   # чувствительность vc к твёрдости
    # расширенные справочные свойства (None = требует уточнения)
    density_g_cm3: Optional[float] = None   # плотность, г/см³
    e_gpa: Optional[float] = None            # модуль упругости E, ГПа
    rm_mpa: Optional[float] = None           # предел прочности Rm (min по ГОСТ), МПа
    ys_mpa: Optional[float] = None           # предел текучести, МПа
    applications: str = ""                   # типовые области применения
    source: str = ""                         # источник (стандарт / каталог)


@dataclass(frozen=True)
class ToolType:
    key: str
    name: str
    vc_factor: Dict[str, Optional[float]]    # множитель vc по группам ISO (None = нельзя)
    taylor_n: float                          # показатель стойкости (v·T^n = const)
    feed_factor: float
    coating_factors: Tuple[float, float]     # (с покрытием, без покрытия)
    supports_coating: bool
    e_modulus: float                         # Н/мм²
    notes: Dict[str, str] = field(default_factory=dict)


@dataclass
class HardnessSpec:
    kind: str = "default"    # default | HB | HRC | Rm
    value: float = 0.0


@dataclass
class ToolSpec:
    tool_type: ToolType
    coated: bool
    diameter: float          # D инструмента (у точения — сечение державки/борштанги), мм
    teeth: int               # z
    overhang: float          # вылет L, мм
    corner_radius: float     # радиус при вершине r, мм


@dataclass
class OperationParams:
    workpiece_diameter: float = 0.0
    length: float = 50.0
    ap: float = 0.0
    ae: float = 0.0
    ra: float = 3.2
    tool_life: float = 60.0
    pitch: float = 0.0
    pre_hole: float = 0.0


@dataclass
class MachineSpec:
    n_max: float             # об/мин
    power_kw: float          # кВт
    efficiency: float        # КПД привода η
    rigidity: str            # high | medium | low


@dataclass
class CuttingInput:
    operation: Operation
    material: Material
    hardness: HardnessSpec
    tool: ToolSpec
    params: OperationParams
    machine: MachineSpec


@dataclass
class Message:
    level: Level
    text: str


@dataclass
class CuttingResult:
    n: float
    n_theoretical: float
    vc: float
    vc_target: float
    fn: float
    fz: float
    vf: float
    ap: float
    ae: Optional[float]
    passes: int
    hm: float
    kc: float
    fc: float
    p_cut: float
    p_spindle: float
    load_pct: float
    torque: float
    q: Optional[float]
    time_min: float
    ra_est: Optional[float]
    deflection: Optional[float]
    hb: float
    flags: Dict[str, Level] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    factors: List[Tuple[str, float]] = field(default_factory=list)

    @property
    def overall(self) -> Level:
        worst = Level.OK
        for m in self.messages:
            if m.level in (Level.WARNING, Level.ERROR) and m.level > worst:
                worst = m.level
        return worst
