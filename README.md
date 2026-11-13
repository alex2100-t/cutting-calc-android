# Калькулятор режимов резания — Android-прототип (Kivy)

**Автор: Aleksey Tikhonov**

Прототип для Android на Python/Kivy. Расчётное ядро (`core/`) переиспользовано
из десктопной версии (PyQt6) **без изменений** — оно не зависит от интерфейса.

## Запуск на ПК (проверка)

```bash
pip install kivy
python main.py
```

## Сборка APK

Buildozer работает **только на Linux** (или в Docker / GitHub Actions).
На Windows напрямую собрать APK нельзя.

### Локально на Linux

```bash
pip install buildozer cython
buildozer android debug
```

Готовый APK: `bin/cuttingcalc-2.0.0-arm64-v8a_armeabi-v7a-debug.apk`

### Через GitHub Actions (без своего Linux)

В репозитории уже есть workflow `.github/workflows/build-apk.yml`:
Actions → Build Android APK → Run workflow → скачать APK из Artifacts.

## Что умеет прототип

- Выбор операции (10 операций: точение, фрезерование, сверление и т.д.)
- Выбор материала (24 марки из `core/catalog.py`, ГОСТ/ISO)
- Тип инструмента, покрытие, геометрия
- Параметры операции, станок, жёсткость
- Расчёт: n, vc, подачи, мощность, загрузка, время, замечания
- В «О программе»: **Создано: Aleksey Tikhonov**

## Структура

```
cutting_calc_kivy/
├── main.py            # интерфейс Kivy (экран ввода + экран результатов)
├── core/              # расчётное ядро (копия из десктопной версии)
├── buildozer.spec     # конфигурация сборки APK
├── requirements.txt
└── README.md
```
