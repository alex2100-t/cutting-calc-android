[app]
title = Калькулятор режимов резания
package.name = cuttingcalc
package.domain = org.tikhonov
source.dir = .
source.include_exts = py,png,jpg,kv,md,txt
version = 2.0.0
requirements = python3,kivy==2.3.0,kivymd==1.2.0
p4a.python = 3.11
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2

[app:android]
permission = INTERNET
android.accept_sdk_license = True
# Для Android 10+ и scoped storage:
# android.private_storage = True
