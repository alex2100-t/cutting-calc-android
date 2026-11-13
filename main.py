"""
Калькулятор режимов резания — Android-прототип на Kivy/KivyMD.

Дизайн повторяет десктопную версию (PyQt6):
тёмная тема, баннер статуса, карточки результатов 2 колонки,
индикатор загрузки мощности, цветные замечания.

Автор: Aleksey Tikhonov

Запуск на ПК:
    pip install kivy kivymd
    python main.py

Сборка APK:
    buildozer android debug   (см. buildozer.spec и README.md)
"""
import os

os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDTextButton
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

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
    "text": get_color_from_hex("#d8dee6"),
    "muted": get_color_from_hex("#8d99a6"),
    "accent": get_color_from_hex("#3d8bfd"),
    "ok": get_color_from_hex("#3fb950"),
    "warn": get_color_from_hex("#e3a008"),
    "err": get_color_from_hex("#f05252"),
    "info": get_color_from_hex("#4c9aff"),
}
LEVEL_COLOR = {Level.OK: C["ok"], Level.INFO: C["info"], Level.WARNING: C["warn"], Level.ERROR: C["err"]}
LEVEL_ICON = {Level.OK: "✔", Level.INFO: "ℹ", Level.WARNING: "⚠", Level.ERROR: "⛔"}


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


def styled_label(text, size="14sp", color=None, bold=False, halign="left", h=None):
    lbl = Label(text=text, font_size=size, halign=halign, valign="middle",
                color=color or C["text"], size_hint_y=None, height=h or 32)
    lbl.bold = bold
    lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
    return lbl


class Card(MDCard):
    """Карточка результата как в десктопной версии: заголовок / значение / единица."""

    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = C["card"]
        self.radius = [8]
        self.padding = "8dp"
        self.size_hint_y = None
        self.height = 92
        box = BoxLayout(orientation="vertical", spacing=0, padding="4dp")
        self.t = styled_label(title, size="11sp", color=C["muted"], h=20)
        self.v = styled_label("—", size="22sp", bold=True, h=34)
        self.u = styled_label("", size="11sp", color=C["muted"], h=18)
        box.add_widget(self.t)
        box.add_widget(self.v)
        box.add_widget(self.u)
        self.add_widget(box)

    def set(self, value, unit="", level=Level.OK):
        self.v.text = str(value)
        self.u.text = unit
        col = C["text"]
        if level == Level.WARNING:
            col = C["warn"]
        elif level == Level.ERROR:
            col = C["err"]
        self.v.color = col


class SectionCard(MDCard):
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = C["card"]
        self.radius = [10]
        self.padding = "12dp"
        self.size_hint_y = None
        self.box = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        self.box.bind(minimum_height=self.box.setter("height"))
        self.add_widget(styled_label(title, size="13sp", color=C["muted"], bold=True, h=24))
        self.add_widget(self.box)


class InputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="input", **kwargs)
        self._build_ui()
        Clock.schedule_once(lambda *_: self._apply_operation_defaults(), 0.1)

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")
        root.add_widget(MDTopAppBar(title=APP_TITLE, md_bg_color=C["card"],
                                     specific_text_color=C["text"]))

        scroll = ScrollView()
        outer = BoxLayout(orientation="vertical", spacing=10, padding=10, size_hint_y=None)
        outer.bind(minimum_height=outer.setter("height"))
        scroll.add_widget(outer)
        root.add_widget(scroll, 1)

        # --- Операция ---
        sec = SectionCard("ОПЕРАЦИЯ")
        sec.box.add_widget(styled_label("Вид обработки / операция"))
        self.sp_op = Spinner(text="", size_hint_y=None, height=48)
        self.sp_op.values = [op.title for op in Operation]
        self.sp_op.text = Operation.TURN_ROUGH.title
        self.sp_op.bind(text=self._on_operation_changed)
        sec.box.add_widget(self.sp_op)
        self.lbl_desc = styled_label("", size="13sp", color=C["muted"], h=40)
        sec.box.add_widget(self.lbl_desc)
        outer.add_widget(sec)

        # --- Материал ---
        sec = SectionCard("МАТЕРИАЛ")
        sec.box.add_widget(styled_label("Марка / материал (ГОСТ/ISO)"))
        self.sp_mat = Spinner(text="", size_hint_y=None, height=48)
        self.sp_mat.values = [m.name for m in cat.MATERIALS.values()]
        self.sp_mat.text = cat.MATERIALS["st45"].name
        sec.box.add_widget(self.sp_mat)
        self.lbl_mat_info = styled_label("", size="12sp", color=C["muted"], h=44)
        self.lbl_mat_info.bind(text=self._on_material_changed)
        sec.box.add_widget(self.lbl_mat_info)
        outer.add_widget(sec)

        # --- Инструмент ---
        sec = SectionCard("ИНСТРУМЕНТ")
        sec.box.add_widget(styled_label("Тип инструмента"))
        self.sp_tool = Spinner(text="", size_hint_y=None, height=48)
        self.sp_tool.values = [t.name for t in cat.TOOL_TYPES.values()]
        self.sp_tool.text = cat.TOOL_TYPES["carbide"].name
        sec.box.add_widget(self.sp_tool)
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=44)
        row.add_widget(styled_label("Покрытие (TiN / TiAlN)"))
        self.chk_coat = CheckBox(active=True)
        row.add_widget(self.chk_coat)
        sec.box.add_widget(row)
        self.inputs = {}

        def add_num(key, hint, default):
            ti = MDTextField(hint_text=hint, text=str(default), mode="rectangle",
                             size_hint_y=None, height=52, font_size="16sp")
            sec.box.add_widget(ti)
            self.inputs[key] = ti

        add_num("d", "Диаметр D / сечение, мм", 25)
        add_num("z", "Число зубьев z", 1)
        add_num("l", "Вылет L, мм", 40)
        add_num("r", "Радиус при вершине r, мм", 0.8)
        outer.add_widget(sec)

        # --- Параметры ---
        sec = SectionCard("ПАРАМЕТРЫ ОПЕРАЦИИ")
        self.inputs = {**self.inputs}

        def add_num2(key, hint, default):
            ti = MDTextField(hint_text=hint, text=str(default), mode="rectangle",
                             size_hint_y=None, height=52, font_size="16sp")
            sec.box.add_widget(ti)
            self.inputs[key] = ti

        add_num2("dw", "Диаметр обработки, мм", 60)
        add_num2("length", "Длина обработки, мм", 50)
        add_num2("ap", "Глубина резания ap, мм", 2.5)
        add_num2("ae", "Ширина фрезерования ae, мм", 10)
        add_num2("life", "Стойкость инструмента T, мин", 60)
        sec.box.add_widget(styled_label("Требуемая шероховатость Ra, мкм"))
        self.sp_ra = Spinner(text="6.3", values=[str(v) for v in cat.RA_VALUES],
                             size_hint_y=None, height=48)
        sec.box.add_widget(self.sp_ra)
        outer.add_widget(sec)

        # --- Станок ---
        sec = SectionCard("СТАНOK / СПИД")
        add_num3 = lambda k, h, d: self._add_machine_field(sec, k, h, d)
        add_num3("n_max", "n_max станка, об/мин", 2000)
        add_num3("power", "Мощность станка, кВт", 10)
        add_num3("eta", "КПД привода (0.3–1.0)", 0.85)
        sec.box.add_widget(styled_label("Жёсткость СПИД"))
        self.sp_rig = Spinner(text=cat.RIGIDITY["medium"][0], size_hint_y=None, height=48)
        self.sp_rig.values = [v[0] for v in cat.RIGIDITY.values()]
        sec.box.add_widget(self.sp_rig)
        outer.add_widget(sec)

        btn = MDRaisedButton(text="РАССЧИТАТЬ", size_hint_y=None, height=56,
                             font_size="18sp", md_bg_color=C["accent"])
        btn.bind(on_press=self._on_calculate)
        outer.add_widget(btn)

        btn_about = MDTextButton(text="О программе", size_hint_y=None, height=44)
        btn_about.bind(on_press=self._on_about)
        outer.add_widget(btn_about)

        self.add_widget(root)
        self._update_mat_info()

    def _add_machine_field(self, sec, key, hint, default):
        ti = MDTextField(hint_text=hint, text=str(default), mode="rectangle",
                         size_hint_y=None, height=52, font_size="16sp")
        sec.box.add_widget(ti)
        self.inputs[key] = ti

    # ---------- Логика (без изменений) ----------
    def operation(self):
        for op in Operation:
            if op.title == self.sp_op.text:
                return op
        return Operation.TURN_ROUGH

    def _on_operation_changed(self, *args):
        self._apply_operation_defaults()

    def _on_material_changed(self, *args):
        self._update_mat_info()

    def _update_mat_info(self):
        m = self._material()
        self.lbl_mat_info.text = (
            f"ISO {m.iso} · kc1.1={m.kc11:.0f} · vc={m.vc_ref:.0f} м/мин · HB≈{m.hb_ref:.0f}"
            + (f" · {m.source}" if m.source else ""))

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
        for t in cat.TOOL_TYPES.values():
            if t.name == self.sp_tool.text:
                return t
        return cat.TOOL_TYPES["carbide"]

    def _rigidity_key(self):
        for k, (name, _) in cat.RIGIDITY.items():
            if name == self.sp_rig.text:
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
                coated=bool(self.chk_coat.active and tt.supports_coating),
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
            Popup(title="Ошибка данных", msg=str(e), size_hint=(0.85, 0.4)).open()
            return
        except Exception as e:  # noqa: BLE001
            Popup(title="Ошибка расчёта", msg=str(e), size_hint=(0.85, 0.4)).open()
            return
        self.parent.get_screen("result").show_result(inp, res)
        self.parent.current = "result"

    def _on_about(self, *args):
        Popup(title="О программе",
              msg=f"{APP_TITLE}\nKivy-прототип для Android\n\nСоздано: {AUTHOR}",
              size_hint=(0.85, 0.45)).open()


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="result", **kwargs)
        root = BoxLayout(orientation="vertical")
        root.add_widget(MDTopAppBar(title="Результаты расчёта", md_bg_color=C["card"],
                                     specific_text_color=C["text"]))

        # Баннер статуса (как в десктопной версии)
        self.banner = Label(text="", size_hint_y=None, height=52, font_size="15sp",
                            halign="center", valign="middle", bold=True)
        self.banner.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        root.add_widget(self.banner)

        scroll = ScrollView()
        outer = BoxLayout(orientation="vertical", spacing=10, padding=10, size_hint_y=None)
        outer.bind(minimum_height=outer.setter("height"))
        scroll.add_widget(outer)
        root.add_widget(scroll, 1)

        # Сетка карточек 2 колонки (на телефоне удобнее, чем 4)
        self.grid = GridLayout(cols=2, spacing=8, size_hint_y=None)
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
        self.bar = ProgressBar(max=150, value=0, size_hint_y=None, height=24)
        outer.add_widget(styled_label("Загрузка мощности станка", size="13sp", color=C["muted"], h=24))
        outer.add_widget(self.bar)
        self.bar_label = styled_label("", size="14sp", h=24)
        outer.add_widget(self.bar_label)

        # Замечания
        outer.add_widget(styled_label("ЗАМЕЧАНИЯ И ПРЕДУПРЕЖДЕНИЯ", size="13sp",
                                      color=C["muted"], bold=True, h=28))
        self.msgs = BoxLayout(orientation="vertical", spacing=4, size_hint_y=None)
        self.msgs.bind(minimum_height=self.msgs.setter("height"))
        outer.add_widget(self.msgs)

        btn_back = MDRaisedButton(text="‹ Назад к вводу", size_hint_y=None, height=52,
                                  md_bg_color=C["accent"])
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

        self.bar.value = min(150, r.load_pct)
        self.bar_label.text = f"Загрузка мощности: {r.load_pct:.0f} %"

        overall = r.overall
        if overall == L.ERROR:
            self.banner.text = f"⛔ {inp.operation.title} · {inp.material.name} — превышены ограничения"
            self.banner.color = C["err"]
        elif overall == L.WARNING:
            self.banner.text = f"⚠ {inp.operation.title} · {inp.material.name} — есть предупреждения"
            self.banner.color = C["warn"]
        else:
            self.banner.text = f"✔ {inp.operation.title} · {inp.material.name} — режимы в норме"
            self.banner.color = C["ok"]

        self.msgs.clear_widgets()
        items = r.messages or []
        if not items:
            self.msgs.add_widget(styled_label("✔ Замечаний нет.", color=C["ok"], h=32))
        for m in items:
            lbl = styled_label(f"{LEVEL_ICON[m.level]}  {m.text}", size="13sp",
                               color=LEVEL_COLOR[m.level], h=44)
            self.msgs.add_widget(lbl)


class CuttingApp(MDApp):
    title = APP_TITLE

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.material_style = "M3"
        sm = ScreenManager()
        sm.add_widget(InputScreen())
        sm.add_widget(ResultScreen())
        return sm


if __name__ == "__main__":
    CuttingApp().run()
