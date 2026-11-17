"""
Калькулятор режимов резания — Android-версия на Kivy.

Дизайн повторяет десктопную версию (PyQt6):
тёмная тема, карточки разделов, баннер статуса,
карточки результатов 2 колонки, индикатор загрузки мощности,
цветные замечания.

Автор: Aleksey Tikhonov

Запуск на ПК:
    pip install kivy
    python main.py

Сборка APK:
    buildozer android debug   (см. buildozer.spec и README.md)
"""
import os

os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex

from core import catalog as cat
from core.calculator import CalculationError, calculate
from core.models import (
    CuttingInput, HardnessSpec, Level, MachineSpec, Operation, OperationParams, ToolSpec,
)

APP_TITLE = "Калькулятор режимов резания"
AUTHOR = "Aleksey Tikhonov"

# Палитра десктопной версии (dark)
C = {
    "bg": get_color_from_hex("#1e2227"),
    "card": get_color_from_hex("#262b32"),
    "field": get_color_from_hex("#2f3640"),
    "text": get_color_from_hex("#d8dee6"),
    "muted": get_color_from_hex("#8d99a6"),
    "accent": get_color_from_hex("#3d8bfd"),
    "ok": get_color_from_hex("#3fb950"),
    "warn": get_color_from_hex("#e3a008"),
    "err": get_color_from_hex("#f05252"),
    "info": get_color_from_hex("#4c9aff"),
}
LEVEL_COLOR = {Level.OK: C["ok"], Level.INFO: C["info"], Level.WARNING: C["warn"], Level.ERROR: C["err"]}
# Текстовые метки вместо эмодзи: в шрифте Roboto нет глифов ✔ ℹ ⚠ ⛔ (показываются квадратиками)
LEVEL_ICON = {Level.OK: "[OK]", Level.INFO: "[INFO]", Level.WARNING: "[ВНИМАНИЕ]", Level.ERROR: "[ОШИБКА]"}

# Короткие подписи для списков (полные названия — в core/catalog.py)
TOOL_SHORT = {
    "carbide": "Твёрдый сплав",
    "hss": "Быстрорежущая сталь (HSS)",
    "pcd": "PCD (поликристаллический алмаз)",
    "cbn": "CBN (кубический нитрид бора)",
}
RIG_SHORT = {"high": "Высокая", "medium": "Средняя", "low": "Низкая"}


def fnum(text, default):
    try:
        return float(str(text).replace(",", ".").strip())
    except (ValueError, AttributeError):
        return default


def inum(text, default):
    try:
        return int(float(str(text).replace(",", ".").strip()))
    except (ValueError, AttributeError):
        return default


def make_label(text, size="14sp", color=None, bold=False, halign="left"):
    """Подпись с автоматической высотой (перенос строк, без обрезки)."""
    lbl = Label(text=text, font_size=size, halign=halign, valign="top",
                color=color or C["text"], size_hint_y=None, height=dp(22))
    lbl.bold = bold
    lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))

    def _fit(i, ts):
        i.height = max(dp(22), ts[1] + dp(6))

    lbl.bind(texture_size=_fit)
    return lbl


def make_input(default, hint=""):
    return TextInput(text=str(default), hint_text=hint, multiline=False,
                     font_size="16sp", size_hint_y=None, height=dp(52),
                     background_color=C["field"], foreground_color=C["text"],
                     hint_text_color=C["muted"],
                     padding=[dp(12), dp(14), dp(12), dp(14)],
                     cursor_color=C["accent"])


def make_spinner(values, text, font_size="14sp"):
    return Spinner(values=values, text=text, size_hint_y=None, height=dp(48),
                   font_size=font_size, color=C["text"],
                   background_color=C["field"])


def make_button(text, bg=None, height=None, font_size="16sp"):
    bg = bg or C["field"]
    return Button(text=text, size_hint_y=None, height=height or dp(52),
                  font_size=font_size, color=C["text"], bold=True,
                  background_color=bg)


def show_popup(title, msg):
    content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
    content.add_widget(make_label(msg, size="14sp"))
    Popup(title=title, content=content, size_hint=(0.9, 0.45)).open()


class Header(BoxLayout):
    """Верхняя панель с заголовком экрана."""

    def __init__(self, title, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(56),
                         padding=[dp(16), 0, dp(16), 0], **kwargs)
        with self.canvas.before:
            Color(rgba=C["card"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)
        lbl = Label(text=title, font_size="17sp", bold=True, color=C["text"],
                    halign="left", valign="middle")
        lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        self.add_widget(lbl)

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


class SectionCard(BoxLayout):
    """Карточка раздела: тёмный фон, автоматическая высота по содержимому."""

    def __init__(self, title, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8),
                         padding=[dp(14), dp(12), dp(14), dp(12)],
                         size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(rgba=C["card"])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(10)] * 4)
        self.bind(pos=self._sync, size=self._sync)
        self.add_widget(make_label(title, size="13sp", color=C["muted"], bold=True))
        self.box = self  # поля добавляются прямо в карточку

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


class Card(BoxLayout):
    """Карточка результата как в десктопной версии: заголовок / значение / единица."""

    def __init__(self, title, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(2),
                         padding=[dp(10), dp(8), dp(10), dp(8)],
                         size_hint_y=None, height=dp(100), **kwargs)
        with self.canvas.before:
            Color(rgba=C["card"])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[dp(8)] * 4)
        self.bind(pos=self._sync, size=self._sync)
        self.t = make_label(title, size="11sp", color=C["muted"])
        self.v = make_label("—", size="22sp", bold=True)
        self.u = make_label("", size="11sp", color=C["muted"])
        self.add_widget(self.t)
        self.add_widget(self.v)
        self.add_widget(self.u)

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set(self, value, unit="", level=Level.OK):
        self.v.text = str(value)
        self.u.text = unit
        col = C["text"]
        if level == Level.WARNING:
            col = C["warn"]
        elif level == Level.ERROR:
            col = C["err"]
        self.v.color = col


class Banner(BoxLayout):
    """Баннер статуса с фоном в цвет статуса."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(58),
                         padding=[dp(12), dp(6), dp(12), dp(6)], **kwargs)
        with self.canvas.before:
            self._col = Color(rgba=C["card"])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[0, 0, 0, 0])
        self.bind(pos=self._sync, size=self._sync)
        self.lbl = Label(text="", font_size="15sp", bold=True, halign="center",
                         valign="middle", color=C["text"])
        self.lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        self.add_widget(self.lbl)

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_status(self, text, color):
        self.lbl.text = text
        self.lbl.color = color
        r, g, b, _ = color
        self._col.rgba = (r, g, b, 0.22)


class PowerBar(BoxLayout):
    """Индикатор загрузки мощности: дорожка + цветная заливка."""

    MAX = 150.0

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(22), **kwargs)
        self._value = 0.0
        with self.canvas.before:
            Color(rgba=C["field"])
            self._track = RoundedRectangle(pos=self.pos, size=self.size,
                                           radius=[dp(6)] * 4)
            self._fill_col = Color(rgba=C["ok"])
            self._fill = RoundedRectangle(pos=self.pos, size=(0, self.height),
                                          radius=[dp(6)] * 4)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._track.pos = self.pos
        self._track.size = self.size
        w = self.width * min(1.0, self._value / self.MAX)
        self._fill.pos = self.pos
        self._fill.size = (w, self.height)

    def set_value(self, pct):
        self._value = float(pct)
        if pct <= 70:
            self._fill_col.rgba = C["ok"]
        elif pct <= 100:
            self._fill_col.rgba = C["warn"]
        else:
            self._fill_col.rgba = C["err"]
        self._sync()


class InputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="input", **kwargs)
        self._build_ui()
        Clock.schedule_once(lambda *_: self._apply_operation_defaults(), 0.1)

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")
        root.add_widget(Header(APP_TITLE))

        scroll = ScrollView()
        outer = BoxLayout(orientation="vertical", spacing=dp(10),
                          padding=dp(10), size_hint_y=None)
        outer.bind(minimum_height=outer.setter("height"))
        scroll.add_widget(outer)
        root.add_widget(scroll)

        # --- Операция ---
        sec = SectionCard("ОПЕРАЦИЯ")
        sec.box.add_widget(make_label("Вид обработки / операция"))
        self.sp_op = make_spinner([op.title for op in Operation], Operation.TURN_ROUGH.title)
        self.sp_op.bind(text=self._on_operation_changed)
        sec.box.add_widget(self.sp_op)
        self.lbl_desc = make_label("", size="13sp", color=C["muted"])
        sec.box.add_widget(self.lbl_desc)
        outer.add_widget(sec)

        # --- Материал ---
        sec = SectionCard("МАТЕРИАЛ")
        sec.box.add_widget(make_label("Марка / материал (ГОСТ/ISO)"))
        self.sp_mat = make_spinner([m.name for m in cat.MATERIALS.values()],
                                   cat.MATERIALS["st45"].name)
        sec.box.add_widget(self.sp_mat)
        self.lbl_mat_info = make_label("", size="12sp", color=C["muted"])
        self.lbl_mat_info.bind(text=self._on_material_changed)
        sec.box.add_widget(self.lbl_mat_info)
        outer.add_widget(sec)

        # --- Инструмент ---
        sec = SectionCard("ИНСТРУМЕНТ")
        sec.box.add_widget(make_label("Тип инструмента"))
        self.sp_tool = make_spinner([TOOL_SHORT[k] for k in cat.TOOL_TYPES],
                                    TOOL_SHORT["carbide"])
        self.sp_tool.bind(text=self._on_tool_changed)
        sec.box.add_widget(self.sp_tool)
        self.lbl_tool_info = make_label("", size="12sp", color=C["muted"])
        sec.box.add_widget(self.lbl_tool_info)
        self.coated = True
        self.btn_coat = make_button("Покрытие: ВКЛ", height=dp(48), font_size="14sp")
        self.btn_coat.bind(on_press=self._on_coat_toggle)
        sec.box.add_widget(self.btn_coat)
        self.inputs = {}
        self._add_field(sec, "d", "Диаметр D / сечение, мм", 25)
        self._add_field(sec, "z", "Число зубьев z", 1)
        self._add_field(sec, "l", "Вылет L, мм", 40)
        self._add_field(sec, "r", "Радиус при вершине r, мм", 0.8)
        outer.add_widget(sec)

        # --- Параметры ---
        sec = SectionCard("ПАРАМЕТРЫ ОПЕРАЦИИ")
        self._add_field(sec, "dw", "Диаметр обработки, мм", 60)
        self._add_field(sec, "length", "Длина обработки, мм", 50)
        self._add_field(sec, "ap", "Глубина резания ap, мм", 2.5)
        self._add_field(sec, "ae", "Ширина фрезерования ae, мм", 10)
        self._add_field(sec, "life", "Стойкость инструмента T, мин", 60)
        sec.box.add_widget(make_label("Требуемая шероховатость Ra, мкм"))
        self.sp_ra = make_spinner([str(v) for v in cat.RA_VALUES], "6.3")
        sec.box.add_widget(self.sp_ra)
        outer.add_widget(sec)

        # --- Станок ---
        sec = SectionCard("СТАНOK / СПИД")
        self._add_field(sec, "n_max", "n_max станка, об/мин", 2000)
        self._add_field(sec, "power", "Мощность станка, кВт", 10)
        self._add_field(sec, "eta", "КПД привода (0.3–1.0)", 0.85)
        sec.box.add_widget(make_label("Жёсткость СПИД"))
        self.sp_rig = make_spinner([RIG_SHORT[k] for k in cat.RIGIDITY], RIG_SHORT["medium"])
        self.sp_rig.bind(text=self._on_rigidity_changed)
        sec.box.add_widget(self.sp_rig)
        self.lbl_rig_info = make_label("", size="12sp", color=C["muted"])
        sec.box.add_widget(self.lbl_rig_info)
        outer.add_widget(sec)

        btn = make_button("РАССЧИТАТЬ", bg=C["accent"], height=dp(56), font_size="18sp")
        btn.bind(on_press=self._on_calculate)
        outer.add_widget(btn)

        btn_about = make_button("О программе", height=dp(44), font_size="14sp")
        btn_about.bind(on_press=self._on_about)
        outer.add_widget(btn_about)

        self.add_widget(root)
        self._update_mat_info()
        self._update_tool_info()
        self._update_rig_info()

    def _add_field(self, sec, key, hint, default):
        ti = make_input(default, hint)
        sec.box.add_widget(ti)
        self.inputs[key] = ti

    # ---------- Обработчики ----------
    def _on_coat_toggle(self, *args):
        self.coated = not self.coated
        self.btn_coat.text = "Покрытие: ВКЛ" if self.coated else "Покрытие: ВЫКЛ"

    def _on_operation_changed(self, *args):
        self._apply_operation_defaults()

    def _on_material_changed(self, *args):
        self._update_mat_info()

    def _on_tool_changed(self, *args):
        self._update_tool_info()

    def _on_rigidity_changed(self, *args):
        self._update_rig_info()

    def _update_mat_info(self):
        m = self._material()
        self.lbl_mat_info.text = (
            f"ISO {m.iso} · kc1.1={m.kc11:.0f} · vc={m.vc_ref:.0f} м/мин · HB≈{m.hb_ref:.0f}"
            + (f" · {m.source}" if m.source else ""))

    def _update_tool_info(self):
        self.lbl_tool_info.text = self._tool_type().name

    def _update_rig_info(self):
        self.lbl_rig_info.text = cat.RIGIDITY[self._rigidity_key()][0]

    # ---------- Логика (без изменений) ----------
    def operation(self):
        for op in Operation:
            if op.title == self.sp_op.text:
                return op
        return Operation.TURN_ROUGH

    def _apply_operation_defaults(self):
        op = self.operation()
        self.lbl_desc.text = cat.OP_DESCRIPTIONS.get(op, "")
        td = cat.TOOL_DEFAULTS.get(op, {})
        pd = cat.PARAM_DEFAULTS.get(op, {})
        defaults = {
            "d": td.get("d", 25), "z": td.get("z", 1), "l": td.get("l", 40), "r": td.get("r", 0.8),
            "dw": pd.get("dw", 60), "length": pd.get("length", 50),
            "ap": pd.get("ap", 2.5), "ae": pd.get("ae", 10), "life": 60,
        }
        for k, v in defaults.items():
            if k in self.inputs:
                self.inputs[k].text = str(v)
        if "ra" in pd:
            self.sp_ra.text = str(pd["ra"])

    def _material(self):
        for m in cat.MATERIALS.values():
            if m.name == self.sp_mat.text:
                return m
        return cat.MATERIALS["st45"]

    def _tool_type(self):
        for k, t in cat.TOOL_TYPES.items():
            if TOOL_SHORT[k] == self.sp_tool.text:
                return t
        return cat.TOOL_TYPES["carbide"]

    def _rigidity_key(self):
        for k, short in RIG_SHORT.items():
            if short == self.sp_rig.text:
                return k
        return "medium"

    def build_input(self):
        op = self.operation()
        tt = self._tool_type()
        fields = cat.OP_FIELDS[op]
        return CuttingInput(
            operation=op,
            material=self._material(),
            hardness=HardnessSpec("default", 0.0),
            tool=ToolSpec(
                tool_type=tt,
                coated=bool(self.coated and tt.supports_coating),
                diameter=fnum(self.inputs["d"].text, 25),
                teeth=inum(self.inputs["z"].text, 1) if "z" in fields else 1,
                overhang=fnum(self.inputs["l"].text, 40),
                corner_radius=fnum(self.inputs["r"].text, 0.8) if "radius" in fields else 0.0,
            ),
            params=OperationParams(
                workpiece_diameter=fnum(self.inputs["dw"].text, 60) if "dw" in fields else 0.0,
                length=fnum(self.inputs["length"].text, 50),
                ap=fnum(self.inputs["ap"].text, 2.5) if "ap" in fields else 0.0,
                ae=fnum(self.inputs["ae"].text, 10) if "ae" in fields else 0.0,
                ra=fnum(self.sp_ra.text, 6.3) if "ra" in fields else 12.5,
                tool_life=fnum(self.inputs["life"].text, 60),
                pitch=2.0 if op is Operation.THREADING else 0.0,
                pre_hole=0.0,
            ),
            machine=MachineSpec(
                n_max=fnum(self.inputs["n_max"].text, 2000),
                power_kw=fnum(self.inputs["power"].text, 10),
                efficiency=fnum(self.inputs["eta"].text, 0.85),
                rigidity=self._rigidity_key(),
            ),
        )

    def _on_calculate(self, *args):
        try:
            inp = self.build_input()
            res = calculate(inp)
        except CalculationError as e:
            show_popup("Ошибка данных", str(e))
            return
        except Exception as e:  # noqa: BLE001
            show_popup("Ошибка расчёта", str(e))
            return
        self.parent.get_screen("result").show_result(inp, res)
        self.parent.current = "result"

    def _on_about(self, *args):
        show_popup("О программе",
                   f"{APP_TITLE}\nKivy-версия для Android\n\nСоздано: {AUTHOR}")


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="result", **kwargs)
        root = BoxLayout(orientation="vertical")
        root.add_widget(Header("Результаты расчёта"))

        self.banner = Banner()
        root.add_widget(self.banner)

        scroll = ScrollView()
        outer = BoxLayout(orientation="vertical", spacing=dp(10),
                          padding=dp(10), size_hint_y=None)
        outer.bind(minimum_height=outer.setter("height"))
        scroll.add_widget(outer)
        root.add_widget(scroll)

        # Сетка карточек 2 колонки (на телефоне удобнее, чем 4)
        self.grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        outer.add_widget(self.grid)

        titles = ["Частота вращения n", "Скорость резания vc", "Минутная подача vf", "Подача",
                  "ap / ae", "Съём металла Q", "Мощность на шпинделе", "Загрузка станка",
                  "Крутящий момент", "Основное время", "Сила резания Fc", "Удельная сила kc",
                  "Прогиб инструмента", "Расчётная Ra", "Проходов", "Стойкость T"]
        self.cards = [Card(t) for t in titles]
        for c in self.cards:
            self.grid.add_widget(c)

        # Индикатор загрузки мощности
        outer.add_widget(make_label("Загрузка мощности станка", size="13sp", color=C["muted"]))
        self.bar = PowerBar()
        outer.add_widget(self.bar)
        self.bar_label = make_label("", size="14sp")
        outer.add_widget(self.bar_label)

        # Замечания
        outer.add_widget(make_label("ЗАМЕЧАНИЯ И ПРЕДУПРЕЖДЕНИЯ", size="13sp",
                                    color=C["muted"], bold=True))
        self.msgs = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None)
        self.msgs.bind(minimum_height=self.msgs.setter("height"))
        outer.add_widget(self.msgs)

        btn_back = make_button("‹ Назад к вводу", bg=C["accent"], height=dp(52))
        btn_back.bind(on_press=lambda *_: setattr(self.parent, "current", "input"))
        outer.add_widget(btn_back)

        self.add_widget(root)

    def show_result(self, inp, r):
        F, L = r.flags, Level
        c = self.cards
        milling = inp.operation.category.name == "MILLING"
        c[0].set(f"{r.n:.0f}", "об/мин", F.get("n", L.OK))
        c[1].set(f"{r.vc:.1f}", "м/мин", F.get("vc", L.OK))
        c[2].set(f"{r.vf:.0f}", "мм/мин", F.get("vf", L.OK))
        if milling:
            c[3].set(f"{r.fz:.3f}", "мм/зуб", F.get("vf", L.OK))
        else:
            c[3].set(f"{r.fn:.3f}", "мм/об", F.get("vf", L.OK))
        ae = f" / {r.ae:g}" if r.ae is not None else ""
        c[4].set(f"{r.ap:g}{ae}", "мм", L.OK)
        c[5].set("—" if r.q is None else f"{r.q:.1f}", "см³/мин")
        c[6].set(f"{r.p_spindle:.2f}", "кВт", F.get("power", L.OK))
        c[7].set(f"{r.load_pct:.0f}", "%", F.get("power", L.OK))
        c[8].set(f"{r.torque:.1f}", "Н·м")
        c[9].set(f"{r.time_min:.2f}", "мин")
        c[10].set(f"{r.fc:.0f}", "Н")
        c[11].set(f"{r.kc:.0f}", "Н/мм²", L.OK)
        c[12].set("—" if r.deflection is None else f"{r.deflection:.3f}", "мм", F.get("rigidity", L.OK))
        c[13].set("—" if r.ra_est is None else f"{r.ra_est:.2f}", "мкм")
        c[14].set(str(r.passes), "шт")
        c[15].set(f"{inp.params.tool_life:.0f}", "мин")

        self.bar.set_value(r.load_pct)
        self.bar_label.text = f"Загрузка мощности: {r.load_pct:.0f} %"

        overall = r.overall
        if overall == L.ERROR:
            self.banner.set_status(
                f"{inp.operation.title} · {inp.material.name} — превышены ограничения", C["err"])
        elif overall == L.WARNING:
            self.banner.set_status(
                f"{inp.operation.title} · {inp.material.name} — есть предупреждения", C["warn"])
        else:
            self.banner.set_status(
                f"{inp.operation.title} · {inp.material.name} — режимы в норме", C["ok"])

        self.msgs.clear_widgets()
        items = r.messages or []
        if not items:
            self.msgs.add_widget(make_label("[OK] Замечаний нет.", color=C["ok"]))
        for m in items:
            self.msgs.add_widget(make_label(f"{LEVEL_ICON[m.level]}  {m.text}", size="13sp",
                                            color=LEVEL_COLOR[m.level]))


class CuttingApp(App):
    title = APP_TITLE

    def build(self):
        Window.clearcolor = C["bg"]
        sm = ScreenManager()
        sm.add_widget(InputScreen())
        sm.add_widget(ResultScreen())
        return sm


if __name__ == "__main__":
    CuttingApp().run()
