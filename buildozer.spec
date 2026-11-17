[app]
title = Калькулятор режимов резания
package.name = cuttingcalc
package.domain = org.tikhonov
source.dir = .
source.include_exts = py,png,jpg,kv,md,txt
version = 2.0.0
requirements = python3==3.11.1, hostpython3==3.11.1, kivy==2.3.0
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
android.permissions = INTERNET
android.accept_sdk_license = True
android.api = 33
android.minapi = 24
android.ndk = 25c
android.archs = arm64-v8a

[buildozer]
log_level = 2
