#!/usr/bin/env python3
"""
Provisions 12 isolated, Google-Play-Store-enabled Android Virtual Devices (AVDs)
(`Tramiune_Tester_01` .. `Tramiune_Tester_12`) on macOS (Apple Silicon arm64).

Each AVD has:
  - PlayStore.enabled=true (Google Play Store & Google Play Services pre-installed)
  - Unique hardware fingerprint (Manufacturer, Model, Device Code, LCD Resolution, DPI, Hash)
  - Optimized 2.5GB sparse data partition (`disk.dataPartition.size=2560M`) & 2048MB RAM
    so all 12 AVDs fit comfortably on disk and can run 2-3 at a time in Rolling Batch mode.
"""

import hashlib
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "testers_config.json"


def provision_avds(force_overwrite: bool = False):
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    avd_root = Path(cfg["avd_dir"]).expanduser()
    avd_root.mkdir(parents=True, exist_ok=True)

    sys_image = cfg["system_image"]
    target_api = cfg["target_api"]
    testers = cfg["testers"]

    created_count = 0
    for t in testers:
        avd_name = t["avd_name"]
        ini_file = avd_root / f"{avd_name}.ini"
        avd_folder = avd_root / f"{avd_name}.avd"
        config_ini = avd_folder / "config.ini"

        avd_folder.mkdir(parents=True, exist_ok=True)

        # 1. Write ~/.android/avd/Tramiune_Tester_XX.ini
        ini_content = (
            "avd.ini.encoding=UTF-8\n"
            f"path={avd_folder}\n"
            f"path.rel=avd/{avd_name}.avd\n"
            f"target={target_api}\n"
        )
        ini_file.write_text(ini_content, encoding="utf-8")

        # 2. Generate unique device hash so Play Services sees distinct hardware profile
        raw_fp = f"{avd_name}:{t['manufacturer']}:{t['model']}:{t['device_code']}:{t['lcd_width']}x{t['lcd_height']}@{t['lcd_density']}"
        md5_hash = hashlib.md5(raw_fp.encode("utf-8")).hexdigest()

        display_name = f"Tester {t['id']:02d} ({t['manufacturer']} {t['model']})"

        # Only write config.ini if it doesn't exist or force_overwrite is True
        if not config_ini.exists() or force_overwrite:
            config_content = f"""AvdId={avd_name}
PlayStore.enabled=true
abi.type=arm64-v8a
avd.ini.displayname={display_name}
avd.ini.encoding=UTF-8
disk.dataPartition.size=2560M
emulator.dev.xr.glasses_display=monocular_right
fastboot.chosenSnapshotFile=
fastboot.forceChosenSnapshotBoot=no
fastboot.forceColdBoot=no
fastboot.forceFastBoot=yes
hw.accelerometer=yes
hw.arc=false
hw.audioInput=yes
hw.battery=yes
hw.camera.back=virtualscene
hw.camera.front=emulated
hw.cpu.arch=arm64
hw.cpu.ncore=4
hw.dPad=no
hw.device.hash2=MD5:{md5_hash}
hw.device.manufacturer={t['manufacturer']}
hw.device.name={t['device_code']}
hw.gps=yes
hw.gpu.enabled=yes
hw.gpu.mode=auto
hw.gyroscope=yes
hw.initialOrientation=portrait
hw.keyboard=yes
hw.lcd.density={t['lcd_density']}
hw.lcd.height={t['lcd_height']}
hw.lcd.width={t['lcd_width']}
hw.mainKeys=no
hw.ramSize=2048
hw.sdCard=yes
hw.sensors.light=yes
hw.sensors.magnetic_field=yes
hw.sensors.orientation=yes
hw.sensors.pressure=yes
hw.sensors.proximity=yes
hw.trackBall=no
image.sysdir.1={sys_image}
runtime.network.latency=none
runtime.network.speed=full
sdcard.size=256M
showDeviceFrame=yes
skin.dynamic=yes
tag.display=Google APIs PlayStore
tag.displaynames=Google APIs PlayStore,Page Size 16KB
tag.id=google_apis_playstore
tag.ids=google_apis_playstore,page_size_16kb
target={target_api}
vm.heapSize=256
"""
            config_ini.write_text(config_content, encoding="utf-8")
            created_count += 1
            print(f"✅ Provisioned [{avd_name}] -> {display_name} ({t['lcd_width']}x{t['lcd_height']} @{t['lcd_density']}dpi | Hash: {md5_hash[:10]}...)")
        else:
            print(f"ℹ️  Already exists [{avd_name}] -> {display_name}")

    print("=" * 80)
    print(f"🎉 Total 12 Tester AVDs ready in {avd_root} (Newly created/updated: {created_count}/12)")
    print("=" * 80)


if __name__ == "__main__":
    provision_avds(force_overwrite=True)
