#!/usr/bin/env python3
"""
Tramiune 12-Device, 12-Mail & Network-Isolated Tester Farm Manager (`run_12_testers.py`)
========================================================================================
Solves all 4 pillars of Google Play Console's 12-Tester / 14-Day Closed Testing requirement:
  1. 12 Distinct Hardware Devices: Controls `Tramiune_Tester_01`..`12` (Samsung, Pixel, Xiaomi,
     OnePlus, OPPO, vivo, realme, Motorola, Nothing, Sony, ASUS) + any USB/Wi-Fi real phones.
  2. 12 Gmail Accounts & CSV Export: Manages 12 tester emails in `testers_config.json`, exports
     `testers_emails.csv` for Play Console upload, and assists 1-time Google login via ADB.
  3. Network / IP Isolation: Supports per-device HTTP Proxy (`-http-proxy`) OR 3-Group 4G Hotspot
     IP Rotation (`--group A|B|C`), logging external IPs per session so all 12 testers don't
     appear from a single static IP at the same instant.
  4. Rolling Batch Automation (`--action daily-batch`): Boots 2 AVDs at a time on a 16GB RAM Mac,
     waits for Android + Play Services ready, runs human-like engagement on `002`, `004`, `005`, `006`,
     flushes Play Store telemetry, shuts down the batch, and repeats until all 12 devices finish.

Quick Commands:
  • Check status & 14-day progress matrix:
      python3 tools/tester_farm/run_12_testers.py --action status
  • Export 12 emails to CSV for Google Play Console -> Testers -> Upload CSV:
      python3 tools/tester_farm/run_12_testers.py --action export-emails
  • Check current public IP (before switching Wi-Fi / 4G Hotspot):
      python3 tools/tester_farm/run_12_testers.py --action check-ip
  • One-time Google Account Login Wizard (boots AVDs & opens Google Sign-In):
      python3 tools/tester_farm/run_12_testers.py --action login-wizard --tester 1
  • One-time Play Store Opt-In & Install Wizard (rolling batches of 2):
      python3 tools/tester_farm/run_12_testers.py --action install-wizard --app all
  • Daily Automated Rolling Batch (runs all 12 AVDs, 2 at a time, completely hands-free):
      python3 tools/tester_farm/run_12_testers.py --action daily-batch --app all --batch-size 2
"""

import argparse
import datetime
import json
import math
import os
import random
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "testers_config.json"
STATE_FILE = BASE_DIR / "tester_progress.json"
CSV_FILE = BASE_DIR / "testers_emails.csv"


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(data: dict):
    data["last_updated"] = datetime.datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_adb_bin(cfg: dict) -> str:
    sdk_adb = Path(cfg["sdk_path"]) / "platform-tools" / "adb"
    return str(sdk_adb) if sdk_adb.exists() else "adb"


def get_emulator_bin(cfg: dict) -> str:
    sdk_emu = Path(cfg["sdk_path"]) / "emulator" / "emulator"
    return str(sdk_emu) if sdk_emu.exists() else "emulator"


def run_adb(serial: str, args: list[str], timeout: int = 20) -> str:
    cfg = load_config()
    cmd = [get_adb_bin(cfg), "-s", serial] + args
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
        return out.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR: {e}"


def get_connected_devices() -> list[str]:
    cfg = load_config()
    try:
        out = subprocess.check_output([get_adb_bin(cfg), "devices"], stderr=subprocess.STDOUT).decode("utf-8")
    except Exception:
        return []
    serials = []
    for line in out.splitlines()[1:]:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def get_avd_name_for_serial(serial: str) -> str:
    if not serial.startswith("emulator-"):
        return serial
    out = run_adb(serial, ["emu", "avd", "name"], timeout=5)
    lines = [ln.strip() for ln in out.splitlines() if ln.strip() and ln.strip() != "OK"]
    return lines[0] if lines else serial


def get_host_public_ip() -> dict:
    try:
        req = urllib.request.Request("https://ipinfo.io/json", headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        try:
            with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=6) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"ip": "UNKNOWN", "error": str(e)}


def get_screen_size(serial: str) -> tuple[int, int]:
    out = run_adb(serial, ["shell", "wm", "size"])
    for line in out.splitlines():
        if "x" in line:
            try:
                dims = line.split(":")[-1].strip().split("x")
                return int(dims[0]), int(dims[1])
            except Exception:
                pass
    return 1080, 2400


def check_installer(serial: str, pkg: str) -> str:
    out = run_adb(serial, ["shell", "pm", "list", "packages", "-i", pkg])
    if pkg not in out:
        return "❌ NOT INSTALLED"
    if "installer=com.android.vending" in out:
        return "✅ PLAY STORE (Valid Tester)"
    return f"⚠️ SIDELOADED ({out.split('installer=')[-1]})"


def check_google_account_logged_in(serial: str) -> list[str]:
    out = run_adb(serial, ["shell", "dumpsys", "account"])
    emails = []
    for line in out.splitlines():
        if "Account {" in line and "type=com.google" in line:
            try:
                name_part = line.split("name=")[1].split(",")[0].strip()
                if "@" in name_part and name_part not in emails:
                    emails.append(name_part)
            except Exception:
                pass
    return emails


def wake_and_unlock(serial: str):
    run_adb(serial, ["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    time.sleep(0.5)
    run_adb(serial, ["shell", "wm", "dismiss-keyguard"])
    w, h = get_screen_size(serial)
    run_adb(serial, ["shell", "input", "swipe", str(w // 2), str(int(h * 0.8)), str(w // 2), str(int(h * 0.25)), "300"])
    time.sleep(0.6)


def apply_device_identity_props(serial: str, tester_cfg: dict):
    """Applies timezone, locale hints, and keeps screen awake while plugged in."""
    tz = tester_cfg.get("timezone", "Asia/Ho_Chi_Minh")
    run_adb(serial, ["shell", "service", "call", "alarm", "3", "s16", tz])
    run_adb(serial, ["shell", "settings", "put", "global", "stay_on_while_plugged_in", "3"])
    run_adb(serial, ["shell", "settings", "put", "system", "screen_off_timeout", "600000"])


def trigger_rotating_proxy_if_configured(cfg: dict):
    """If rotating_proxy is enabled in testers_config.json, calls rotate_api_url BEFORE booting a batch."""
    rot = cfg.get("rotating_proxy", {})
    if not rot.get("enabled"):
        return
    api_url = rot.get("rotate_api_url", "").strip()
    wait_sec = int(rot.get("wait_after_rotate_sec", 6))
    if api_url:
        print(f"🔄 Calling Rotating Proxy API to get a fresh Sticky Residential IP...")
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace").strip()
                print(f"   ✅ Rotate API response: {body[:140]}")
        except Exception as e:
            print(f"   ⚠️ Rotate API warning (continuing with current proxy IP): {e}")
        time.sleep(wait_sec)


def boot_avd(tester_cfg: dict, port: int, cfg: dict) -> tuple[str, subprocess.Popen]:
    """Boots an AVD on the given console port (e.g. 5554 -> emulator-5554) and returns (serial, process)."""
    emu_bin = get_emulator_bin(cfg)
    avd_name = tester_cfg["avd_name"]
    serial = f"emulator-{port}"

    cmd = [
        emu_bin,
        "-avd",
        avd_name,
        "-port",
        str(port),
        "-gpu",
        "host",
        "-no-boot-anim",
        "-no-audio",
        "-timezone",
        tester_cfg.get("timezone", "Asia/Ho_Chi_Minh"),
    ]
    proxy = tester_cfg.get("proxy", "").strip()
    if not proxy and cfg.get("rotating_proxy", {}).get("enabled"):
        proxy = cfg.get("rotating_proxy", {}).get("proxy_server", "").strip()
    if proxy:
        cmd.extend(["-http-proxy", proxy])

    print(f"🚀 Booting [{avd_name}] ({tester_cfg['manufacturer']} {tester_cfg['model']}) on {serial}" + (f" via Proxy [{proxy}]..." if proxy else "..."))
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return serial, proc


def wait_for_boot(serial: str, timeout_sec: int = 140) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        if serial in get_connected_devices():
            booted = run_adb(serial, ["shell", "getprop", "sys.boot_completed"], timeout=6)
            if booted.strip() == "1":
                time.sleep(3.0)
                wake_and_unlock(serial)
                return True
        time.sleep(2.5)
    print(f"⚠️ Timeout waiting for {serial} to finish booting.")
    return False


def shutdown_avd(serial: str):
    print(f"🛑 Shutting down {serial}...")
    run_adb(serial, ["emu", "kill"], timeout=8)
    time.sleep(3.0)


def open_play_store(serial: str, pkg: str):
    wake_and_unlock(serial)
    run_adb(
        serial,
        [
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            f"market://details?id={pkg}",
            "com.android.vending",
        ],
    )


def open_optin_web_url(serial: str, optin_url: str):
    wake_and_unlock(serial)
    run_adb(
        serial,
        [
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            optin_url,
        ],
    )


def simulate_human_session_on_device(
    serial: str,
    tester_id: str,
    app_key: str,
    app_info: dict,
    duration_sec: int,
    stagger_sec: float = 0.0,
    ip_addr: str = "",
):
    if stagger_sec > 0:
        time.sleep(stagger_sec)

    pkg = app_info["package"]
    splash = app_info["splash"]

    print(f"📱 [{tester_id} | {serial}] Running {duration_sec}s session on App {app_key} ({pkg})...")
    wake_and_unlock(serial)

    run_adb(
        serial,
        [
            "shell",
            "am",
            "start",
            "-n",
            f"{pkg}/{splash}",
            "--ez",
            "auto_tester_tour",
            "true",
        ],
    )

    w, h = get_screen_size(serial)
    cx, cy = w // 2, int(h * 0.44)
    radius = int(min(w, h) * 0.28)

    start_ts = time.time()
    step = 0

    while (time.time() - start_ts) < duration_sec:
        step += 1
        elapsed = int(time.time() - start_ts)

        if step % 3 == 1:
            fg = run_adb(serial, ["shell", "dumpsys", "window", "displays"])
            if pkg not in fg and elapsed < duration_sec - 10:
                run_adb(serial, ["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])
                time.sleep(2.5)

        action_roll = random.random()
        if action_roll < 0.45:
            angle1 = random.uniform(0, 2 * math.pi)
            angle2 = angle1 + random.uniform(0.9, 2.2)
            x1 = int(cx + radius * math.cos(angle1))
            y1 = int(cy + radius * math.sin(angle1))
            x2 = int(cx + radius * math.cos(angle2))
            y2 = int(cy + radius * math.sin(angle2))
            dur_ms = random.randint(280, 750)
            run_adb(serial, ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(dur_ms)])
        elif action_roll < 0.75:
            tx = random.randint(int(w * 0.18), int(w * 0.82))
            ty = random.randint(int(h * 0.28), int(h * 0.78))
            run_adb(serial, ["shell", "input", "tap", str(tx), str(ty)])
        else:
            sx = int(w * random.uniform(0.35, 0.65))
            y_start = int(h * random.uniform(0.65, 0.78))
            y_end = int(h * random.uniform(0.32, 0.48))
            run_adb(serial, ["shell", "input", "swipe", str(sx), str(y_start), str(sx), str(y_end), "450"])

        time.sleep(random.uniform(3.5, 6.8))

    # Return to Home screen cleanly and wait 6s so Play Services flushes UsageStats
    run_adb(serial, ["shell", "input", "keyevent", "KEYCODE_HOME"])
    time.sleep(6.0)
    record_session_log(tester_id, app_key, duration_sec, ip_addr)
    print(f"✅ [{tester_id} | {serial}] Completed {duration_sec}s session for App {app_key} ({pkg})!")


def record_session_log(tester_id: str, app_key: str, duration_sec: int, ip_addr: str = ""):
    today = datetime.date.today().isoformat()
    data = load_state()

    app_log = data.setdefault(app_key, {})
    dev_days = app_log.setdefault(tester_id, [])
    if today not in dev_days:
        dev_days.append(today)

    ip_history = data.setdefault("ip_history", {}).setdefault(tester_id, [])
    if ip_addr and ip_addr not in ip_history:
        ip_history.append(ip_addr)

    save_state(data)


def manage_real_phone_multi_users(serial: str, action_mode: str, app_arg: str, cfg: dict, duration_sec: int):
    """
    Uses Android's native Multi-User isolation (`pm create-user` / `am switch-user`) on a real physical phone
    so 1 physical phone provides up to 4 completely isolated `MEETS_DEVICE_INTEGRITY` hardware testers!
    """
    max_out = run_adb(serial, ["shell", "pm", "get-max-users"])
    users_out = run_adb(serial, ["shell", "pm", "list", "users"])
    print(f"📱 Real Phone [{serial}] Multi-User Info:\n{max_out}\n{users_out}")

    # Parse existing user IDs
    user_ids = []
    for line in users_out.splitlines():
        if "UserInfo{" in line:
            try:
                uid = int(line.split("UserInfo{")[1].split(":")[0])
                user_ids.append(uid)
            except Exception:
                pass

    if action_mode == "create-users":
        target_total = 4
        while len(user_ids) < target_total:
            new_idx = len(user_ids)
            res = run_adb(serial, ["shell", "pm", "create-user", f"Tester_HW_{new_idx}"])
            print(f"   ➕ Created isolated hardware user: {res}")
            if "Success" not in res:
                break
            user_ids.append(-1)
        print("✅ Done creating isolated hardware users! Use `--action switch-phone-user --tester <user_id>` or `--action daily-phone-users` to run.")
        return

    apps = cfg["apps"]
    target_apps = list(apps.keys()) if app_arg == "all" else [app_arg]
    ip_addr = get_host_public_ip().get("ip", "")

    for uid in user_ids:
        print(f"\n🔀 Switching real phone [{serial}] to isolated Hardware User ID: {uid}...")
        run_adb(serial, ["shell", "am", "switch-user", str(uid)])
        time.sleep(6.0)
        wake_and_unlock(serial)
        for app_key in target_apps:
            if app_key not in apps:
                continue
            simulate_human_session_on_device(
                serial,
                f"{serial}_User{uid}",
                app_key,
                apps[app_key],
                duration_sec,
                0.0,
                ip_addr,
            )
    # Switch back to Owner (User 0) when finished
    run_adb(serial, ["shell", "am", "switch-user", "0"])
    print(f"✅ All {len(user_ids)} hardware users on [{serial}] completed daily sessions and returned to Owner (User 0)!")


def export_emails_csv(cfg: dict):
    testers = cfg["testers"]
    emails = [t["email"].strip() for t in testers if t.get("email", "").strip()]
    CSV_FILE.write_text("\n".join(emails) + "\n", encoding="utf-8")
    print("=" * 80)
    print(f"✅ Exported {len(emails)} tester emails to: {CSV_FILE}")
    print("=" * 80)
    print("📋 Copy-paste directly into Google Play Console -> Testers -> Email lists:")
    print(", ".join(emails))
    print("=" * 80)


def filter_testers(cfg: dict, tester_id: int | None, group_code: str | None) -> list[dict]:
    testers = cfg["testers"]
    if tester_id is not None:
        return [t for t in testers if t["id"] == tester_id]
    if group_code:
        g = group_code.upper()
        return [t for t in testers if f"GROUP_{g}" in t.get("network_group", "").upper()]
    return testers


def import_accounts_from_file(cfg: dict, file_path: str):
    """Imports lines of `email | password | recovery_email` into testers_config.json starting from first unconfigured slot."""
    p = Path(file_path).expanduser()
    if not p.exists():
        print(f"❌ File not found: {p}")
        return
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if "|" in ln or "@" in ln]
    testers = cfg["testers"]
    idx = 0
    for t in testers:
        # Keep already logged_in accounts unless user overwrites
        if t.get("logged_in"):
            continue
        if idx >= len(lines):
            break
        parts = [x.strip() for x in lines[idx].split("|")]
        t["email"] = parts[0]
        if len(parts) > 1:
            t["password"] = parts[1]
        if len(parts) > 2:
            t["recovery_email"] = parts[2]
        idx += 1
        print(f"✅ Mapped Tester #{t['id']:02d} ({t['avd_name']}) -> {t['email']} (Recovery: {t.get('recovery_email', '')})")

    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    export_emails_csv(cfg)


def run_login_wizard(cfg: dict, tester_id: int | None, group_code: str | None):
    target_testers = filter_testers(cfg, tester_id, group_code)
    for t in target_testers:
        trigger_rotating_proxy_if_configured(cfg)
        serial, _ = boot_avd(t, 5554, cfg)
        if not wait_for_boot(serial):
            shutdown_avd(serial)
            continue

        apply_device_identity_props(serial, t)
        logged_emails = check_google_account_logged_in(serial)
        if logged_emails:
            print(f"✅ [{t['avd_name']}] Already logged into Google Account(s): {', '.join(logged_emails)}")
        else:
            print(f"🔑 [{t['avd_name']}] Opening Google Account Sign-In screen for: {t['email']}")
            run_adb(
                serial,
                [
                    "shell",
                    "am",
                    "start",
                    "-a",
                    "android.settings.ADD_ACCOUNT_SETTINGS",
                    "--esa",
                    "authorities",
                    "com.google",
                ],
            )
            if t.get("email"):
                print(f"   👉 Configured Email: {t['email']}")
            print("   👉 Complete the sign-in on the Emulator window (or press Enter here once signed in)...")
            try:
                input("   Press [Enter] when finished signing in on this emulator to save & close -> ")
            except EOFError:
                time.sleep(15)

        logged_after = check_google_account_logged_in(serial)
        state = load_state()
        state.setdefault("accounts_logged_in", {})[t["avd_name"]] = logged_after or [t["email"]]
        save_state(state)
        shutdown_avd(serial)


def run_install_wizard(cfg: dict, app_arg: str, tester_id: int | None, group_code: str | None):
    target_testers = filter_testers(cfg, tester_id, group_code)
    apps = cfg["apps"]
    target_apps = list(apps.keys()) if app_arg == "all" else [app_arg]

    batch_size = 2
    for i in range(0, len(target_testers), batch_size):
        batch = target_testers[i : i + batch_size]
        trigger_rotating_proxy_if_configured(cfg)
        booted = []
        for idx, t in enumerate(batch):
            port = 5554 + idx * 2
            serial, _ = boot_avd(t, port, cfg)
            booted.append((serial, t))

        for serial, t in booted:
            if wait_for_boot(serial):
                apply_device_identity_props(serial, t)
                for app_key in target_apps:
                    pkg = apps[app_key]["package"]
                    status = check_installer(serial, pkg)
                    print(f"📦 [{t['avd_name']}] App {app_key} ({pkg}): {status}")
                    if "PLAY STORE" not in status:
                        open_play_store(serial, pkg)
                        time.sleep(2.0)

        print("\n👉 Click [Install] inside Google Play Store on the open emulator(s).")
        try:
            input("   Press [Enter] once Play Store finishes installing to verify & move to next batch -> ")
        except EOFError:
            time.sleep(20)

        for serial, t in booted:
            for app_key in target_apps:
                pkg = apps[app_key]["package"]
                print(f"🔍 [{t['avd_name']}] Verified {app_key}: {check_installer(serial, pkg)}")
            shutdown_avd(serial)


def run_daily_rolling_batch(
    cfg: dict,
    app_arg: str,
    duration_sec: int,
    batch_size: int,
    tester_id: int | None,
    group_code: str | None,
):
    target_testers = filter_testers(cfg, tester_id, group_code)
    apps = cfg["apps"]
    target_apps = list(apps.keys()) if app_arg == "all" else [app_arg]

    ip_info = get_host_public_ip()
    current_ip = ip_info.get("ip", "UNKNOWN")
    org_info = ip_info.get("org", "")
    print("=" * 84)
    print(f"🌐 Current Network Public IP: {current_ip} ({org_info})")
    print(f"🤖 Starting Daily Rolling Batch: {len(target_testers)} Testers | Batch Size: {batch_size} | Apps: {', '.join(target_apps)}")
    print("=" * 84)

    for i in range(0, len(target_testers), batch_size):
        batch = target_testers[i : i + batch_size]
        print(f"\n🔄 --- BATCH {i // batch_size + 1} / {math.ceil(len(target_testers) / batch_size)}: {[t['avd_name'] for t in batch]} ---")
        trigger_rotating_proxy_if_configured(cfg)

        booted = []
        for idx, t in enumerate(batch):
            port = 5554 + idx * 2
            serial, _ = boot_avd(t, port, cfg)
            booted.append((serial, t))

        ready_pairs = []
        for serial, t in booted:
            if wait_for_boot(serial):
                apply_device_identity_props(serial, t)
                ready_pairs.append((serial, t))

        for app_key in target_apps:
            if app_key not in apps:
                continue
            app_info = apps[app_key]
            threads = []
            for idx, (serial, t) in enumerate(ready_pairs):
                jitter = idx * random.uniform(2.0, 5.0)
                dur = max(45, duration_sec + random.randint(-10, 20))
                th = threading.Thread(
                    target=simulate_human_session_on_device,
                    args=(serial, t["avd_name"], app_key, app_info, dur, jitter, current_ip),
                )
                th.start()
                threads.append(th)
            for th in threads:
                th.join()

        for serial, _ in booted:
            shutdown_avd(serial)

        print(f"✅ Batch {i // batch_size + 1} completed and RAM freed.")

    print("\n🎉 ALL TESTER BATCHES COMPLETED FOR TODAY!")


def print_status(cfg: dict):
    state = load_state()
    ip_info = get_host_public_ip()
    connected = get_connected_devices()

    print("=" * 95)
    print(f"🌐 CURRENT NETWORK IP : {ip_info.get('ip', 'UNKNOWN')} ({ip_info.get('org', '')} | {ip_info.get('city', '')})")
    print(f"🔌 LIVE ADB DEVICES   : {len(connected)} currently running ({', '.join(connected) if connected else 'None'})")
    print("=" * 95)
    print(f"{'ID':<4} {'AVD Name':<20} {'Device Profile':<20} {'Tester Email':<28} {'Net Group':<20} {'002 | 004 | 005 | 006 (Days/14)'}")
    print("-" * 95)

    for t in cfg["testers"]:
        avd = t["avd_name"]
        prof = f"{t['manufacturer']} {t['model']}"[:19]
        email = t["email"][:27]
        net = t.get("network_group", "")[:19]

        counts = []
        for app_key in ["002", "004", "005", "006"]:
            days = len(state.get(app_key, {}).get(avd, []))
            counts.append(f"{days:02d}d")
        progress_str = " | ".join(counts)
        print(f"#{t['id']:02d}  {avd:<20} {prof:<20} {email:<28} {net:<20} {progress_str}")

    print("=" * 95)


def main():
    parser = argparse.ArgumentParser(description="Tramiune 12-Device, 12-Mail & Network-Isolated Tester Farm")
    parser.add_argument(
        "--action",
        choices=[
            "status",
            "export-emails",
            "import-accounts",
            "check-ip",
            "login-wizard",
            "install-wizard",
            "daily-batch",
            "create-phone-users",
            "daily-phone-users",
            "open-play",
            "daily-run",
            "feedback",
        ],
        default="status",
        help="Farm action to execute",
    )
    parser.add_argument("--app", default="all", help="App code ('002', '004', '005', '006', or 'all')")
    parser.add_argument("--duration", type=int, default=90, help="Session duration in seconds per app (default: 90s)")
    parser.add_argument("--batch-size", type=int, default=2, help="Number of AVDs to run simultaneously (default: 2 for 16GB RAM)")
    parser.add_argument("--tester", type=int, default=None, help="Run only a specific tester ID (1..15)")
    parser.add_argument("--group", type=str, default=None, help="Run only a specific network group ('A', 'B', or 'C')")
    parser.add_argument("--accounts-file", type=str, default="accounts.txt", help="Path to text file with `email | pass | recovery_email` lines")
    args = parser.parse_args()

    cfg = load_config()

    if args.action == "status":
        print_status(cfg)
    elif args.action == "export-emails":
        export_emails_csv(cfg)
    elif args.action == "import-accounts":
        import_accounts_from_file(cfg, args.accounts_file)
    elif args.action in ("create-phone-users", "daily-phone-users"):
        phys = [d for d in get_connected_devices() if not d.startswith("emulator-")]
        if not phys:
            print("❌ No physical USB phone detected. Plug in your Android phone first.")
            return
        mode = "create-users" if args.action == "create-phone-users" else "daily-run"
        for p_serial in phys:
            manage_real_phone_multi_users(p_serial, mode, args.app, cfg, args.duration)
    elif args.action == "check-ip":
        info = get_host_public_ip()
        print(json.dumps(info, indent=2, ensure_ascii=False))
    elif args.action == "login-wizard":
        run_login_wizard(cfg, args.tester, args.group)
    elif args.action == "install-wizard":
        run_install_wizard(cfg, args.app, args.tester, args.group)
    elif args.action == "daily-batch":
        run_daily_rolling_batch(cfg, args.app, args.duration, args.batch_size, args.tester, args.group)
    elif args.action in ("open-play", "feedback", "daily-run"):
        # Operate on already-running ADB devices (emulators or physical USB phones)
        devices = get_connected_devices()
        if not devices:
            print("❌ No running ADB devices found. Use `--action daily-batch` to auto-boot the 12 AVDs, or connect phones.")
            return
        apps = cfg["apps"]
        target_apps = list(apps.keys()) if args.app == "all" else [args.app]
        ip_addr = get_host_public_ip().get("ip", "")
        for app_key in target_apps:
            if app_key not in apps:
                continue
            pkg = apps[app_key]["package"]
            if args.action in ("open-play", "feedback"):
                for s in devices:
                    open_play_store(s, pkg)
            else:
                threads = []
                for idx, s in enumerate(devices):
                    avd_id = get_avd_name_for_serial(s)
                    th = threading.Thread(
                        target=simulate_human_session_on_device,
                        args=(s, avd_id, app_key, apps[app_key], args.duration, idx * 2.0, ip_addr),
                    )
                    th.start()
                    threads.append(th)
                for th in threads:
                    th.join()


if __name__ == "__main__":
    main()
