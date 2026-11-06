#!/usr/bin/env python3
"""
One-Command Installer for Antigravity Multi-Chat Live Sync (Workspace + Global Skill).
Run in any project directory on any machine:
    curl -sL https://tramiune.github.io/install_multichat.py | python3
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

SYNC_CHATS_PY = r'''#!/usr/bin/env python3
"""
Multi-Chat Context Synchronizer for Antigravity Workspace.
Automatically indexes all conversations belonging to this workspace, extracts
user requests, agent responses, modified files, and artifacts, updates
.agents/state/ACTIVE_CHATS.md, and injects live cross-chat context on PreInvocation.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_STR = str(WORKSPACE_ROOT)
BRAIN_DIR = Path.home() / ".gemini" / "antigravity" / "brain"
STATE_DIR = WORKSPACE_ROOT / ".agents" / "state"
INDEX_FILE = STATE_DIR / "chats_index.json"
ACTIVE_CHATS_MD = STATE_DIR / "ACTIVE_CHATS.md"
SHARED_MEMORY_MD = STATE_DIR / "SHARED_MEMORY.md"

USER_REQ_RE = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.DOTALL)


def clean_user_content(raw: str) -> str:
    if not raw:
        return ""
    m = USER_REQ_RE.search(raw)
    if m:
        return m.group(1).strip()
    cleaned = re.sub(r"<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>", "", raw, flags=re.DOTALL)
    cleaned = re.sub(r"<USER_SETTINGS_CHANGE>.*?</USER_SETTINGS_CHANGE>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


def clean_arg_val(val) -> str:
    if not isinstance(val, str):
        return str(val)
    val = val.strip()
    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        val = val[1:-1]
    return val


def truncate_text(text: str, max_chars: int = 350) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def parse_transcript(transcript_path: Path, conv_id: str, force_belongs: bool = False):
    try:
        raw_text = transcript_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    belongs = force_belongs or (WORKSPACE_STR in raw_text)
    if not belongs:
        return None

    turns = []
    current_turn = None
    files_modified = []
    last_created_at = ""
    last_step_is_active = False

    lines = [ln for ln in raw_text.splitlines() if ln.strip()]
    for line in lines:
        try:
            step = json.loads(line)
        except Exception:
            continue

        step_type = step.get("type", "")
        created_at = step.get("created_at", "")
        if created_at:
            last_created_at = created_at

        if step_type == "USER_INPUT" and step.get("source") == "USER_EXPLICIT":
            user_text = clean_user_content(step.get("content", ""))
            if user_text:
                if current_turn is not None:
                    turns.append(current_turn)
                current_turn = {
                    "user": user_text,
                    "created_at": created_at,
                    "agent": "",
                    "files": [],
                }
                last_step_is_active = True

        elif step_type == "PLANNER_RESPONSE":
            content = (step.get("content") or "").strip()
            tool_calls = step.get("tool_calls") or []
            if current_turn is not None and content:
                current_turn["agent"] = content

            for tc in tool_calls:
                tname = tc.get("name", "")
                targs = tc.get("args") or {}
                if tname in ("write_file", "edit_file"):
                    p = clean_arg_val(targs.get("Path", ""))
                    if p and "/.agents/state/" not in p:
                        if p not in files_modified:
                            files_modified.append(p)
                        if current_turn is not None and p not in current_turn["files"]:
                            current_turn["files"].append(p)

            if content and not tool_calls:
                last_step_is_active = False
            else:
                last_step_is_active = True

    if current_turn is not None:
        turns.append(current_turn)

    conv_dir = transcript_path.parent.parent.parent
    artifacts = []
    if conv_dir.is_dir():
        for item in sorted(conv_dir.iterdir()):
            if item.is_file() and item.suffix in (".md", ".html") and not item.name.startswith("."):
                artifacts.append(str(item))

    return {
        "conversation_id": conv_id,
        "belongs_to_workspace": True,
        "updated_at": last_created_at,
        "is_running": last_step_is_active,
        "turn_count": len(turns),
        "turns": turns[-8:],
        "files_modified": files_modified[-20:],
        "artifacts": artifacts,
    }


def load_index() -> dict:
    if INDEX_FILE.is_file():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"conversations": {}}


def save_index(index_data: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = INDEX_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_file.replace(INDEX_FILE)


def sync_all_chats(current_conv_id: str = "") -> list:
    index_data = load_index()
    convs_cache = index_data.get("conversations", {})

    if current_conv_id:
        existing = convs_cache.get(current_conv_id, {})
        existing["conversation_id"] = current_conv_id
        existing["belongs_to_workspace"] = True
        convs_cache[current_conv_id] = existing

    if BRAIN_DIR.is_dir():
        for conv_dir in BRAIN_DIR.iterdir():
            if not conv_dir.is_dir() or conv_dir.name.startswith("."):
                continue
            cid = conv_dir.name
            t_path = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
            if not t_path.is_file():
                continue

            try:
                st = t_path.stat()
                mtime = st.st_mtime
                size = st.st_size
            except Exception:
                continue

            cached = convs_cache.get(cid)
            force_belongs = (cid == current_conv_id) or bool(cached and cached.get("belongs_to_workspace"))

            if (
                cached is not None
                and cached.get("mtime") == mtime
                and cached.get("size") == size
                and (not force_belongs or cached.get("belongs_to_workspace"))
            ):
                continue

            parsed = parse_transcript(t_path, cid, force_belongs=force_belongs)
            if parsed is not None:
                parsed["mtime"] = mtime
                parsed["size"] = size
                convs_cache[cid] = parsed
            else:
                convs_cache[cid] = {
                    "conversation_id": cid,
                    "belongs_to_workspace": False,
                    "mtime": mtime,
                    "size": size,
                }

    index_data["conversations"] = convs_cache
    save_index(index_data)

    workspace_chats = [
        c
        for c in convs_cache.values()
        if c.get("belongs_to_workspace") and (c.get("turn_count", 0) > 0 or c.get("conversation_id") == current_conv_id)
    ]
    workspace_chats.sort(
        key=lambda c: (c.get("updated_at") or "", c.get("mtime") or 0),
        reverse=True,
    )
    return workspace_chats


def write_active_chats_markdown(workspace_chats: list):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Active & Recent Chats in `{WORKSPACE_ROOT.name}`",
        f"> Auto-synced at `{now_str}`. Total tracked chats in project: **{len(workspace_chats)}**",
        "",
    ]

    for chat in workspace_chats:
        cid = chat.get("conversation_id", "")
        status = "🔄 Đang xử lý (Running)" if chat.get("is_running") else "✅ Đã phản hồi (Idle)"
        updated = chat.get("updated_at") or "N/A"
        turn_count = chat.get("turn_count", 0)
        lines.append(f"## Chat `{cid}`")
        lines.append(f"- **Status:** {status} | **Last Activity:** `{updated}` | **Turns:** {turn_count}")
        lines.append(f"- **Full Transcript:** `~/.gemini/antigravity/brain/{cid}/.system_generated/logs/transcript.jsonl`")

        files = chat.get("files_modified") or []
        if files:
            lines.append(f"- **Files Modified:** {', '.join(f'`{f}`' for f in files)}")

        artifacts = chat.get("artifacts") or []
        if artifacts:
            lines.append(f"- **Artifacts:** {', '.join(f'`{a}`' for a in artifacts)}")

        turns = chat.get("turns") or []
        if turns:
            lines.append("- **Recent Turns:**")
            for idx, t in enumerate(turns[-5:], 1):
                u_txt = truncate_text(t.get("user", ""), 500)
                a_txt = truncate_text(t.get("agent", ""), 700) or "_(Đang xử lý / chưa có phản hồi cuối)_"
                lines.append(f"  - **[{idx}] User:** {u_txt}")
                lines.append(f"    **Agent:** {a_txt}")
        lines.append("")

    ACTIVE_CHATS_MD.write_text("\n".join(lines), encoding="utf-8")


def build_ephemeral_context(workspace_chats: list, current_conv_id: str) -> str:
    other_chats = [c for c in workspace_chats if c.get("conversation_id") != current_conv_id and c.get("turn_count", 0) > 0]

    shared_mem = ""
    if SHARED_MEMORY_MD.is_file():
        try:
            content = SHARED_MEMORY_MD.read_text(encoding="utf-8").strip()
            if content:
                shared_mem = content
        except Exception:
            pass

    parts = [f"[MULTI-CHAT LIVE CONTEXT — Workspace: {WORKSPACE_STR} | Current Chat ID: {current_conv_id or 'unknown'}]"]

    if shared_mem:
        parts.append("\n### Shared Project Memory (`.agents/state/SHARED_MEMORY.md`):")
        parts.append(shared_mem[:3000])

    if not other_chats:
        parts.append("\n### Other Chats in Project:\nHiện chưa có cuộc trò chuyện nào khác có lịch sử trong project này.")
    else:
        parts.append(f"\n### Other Active/Recent Chats in Project ({len(other_chats)} chat(s)):")
        for chat in other_chats[:8]:
            cid = chat.get("conversation_id", "")
            status = "🔄 RUNNING" if chat.get("is_running") else "✅ IDLE"
            updated = chat.get("updated_at") or "N/A"
            t_count = chat.get("turn_count", 0)
            parts.append(f"\n- **Chat `{cid}`** [{status} | Updated: {updated} | Turns: {t_count}]")

            files = chat.get("files_modified") or []
            if files:
                short_files = [os.path.relpath(f, WORKSPACE_STR) if f.startswith(WORKSPACE_STR) else f for f in files[-8:]]
                parts.append(f"  - Files touched: {', '.join(f'`{f}`' for f in short_files)}")

            turns = chat.get("turns") or []
            for t in turns[-3:]:
                u_txt = truncate_text(t.get("user", ""), 280)
                a_txt = truncate_text(t.get("agent", ""), 380) or "(in progress...)"
                parts.append(f"  - User: {u_txt}")
                parts.append(f"    Agent: {a_txt}")

    parts.append(
        f"\n> Tip: Full details of all project chats are at `{ACTIVE_CHATS_MD}`. "
        "To inspect any chat's complete history, read `~/.gemini/antigravity/brain/<chat-id>/.system_generated/logs/transcript.jsonl`."
    )
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="PreInvocation", help="Hook event type")
    args = parser.parse_args()

    payload = {}
    try:
        if not sys.stdin.isatty():
            raw_in = sys.stdin.read().strip()
            if raw_in:
                payload = json.loads(raw_in)
    except Exception:
        payload = {}

    current_conv_id = payload.get("conversationId", "")
    workspace_chats = sync_all_chats(current_conv_id=current_conv_id)
    write_active_chats_markdown(workspace_chats)

    event = args.event
    if event == "PreInvocation":
        msg = build_ephemeral_context(workspace_chats, current_conv_id)
        print(json.dumps({"injectSteps": [{"ephemeralMessage": msg}]}, ensure_ascii=False))
    elif event == "Stop":
        print(json.dumps({"decision": "stop"}))
    else:
        print("{}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("{}")
'''

SKILL_MD = r'''---
name: multi-chat-sync
description: Automatically synchronize context, history, modified files, and shared memory across all parallel or sequential chat sessions within the same workspace/project. Activate when the user asks to enable multi-chat context sync, share history between chats in a project, or check other chats in the workspace.
---

# Multi-Chat Live Context Synchronization Skill

This skill enables all chat sessions in a workspace to automatically know each other's prompts, responses, modified files, and shared architecture decisions via Antigravity Lifecycle Hooks (`PreInvocation`, `SessionStart`, `Stop`).

## Quick Setup in Any Workspace
Run the bundled installer in the workspace root directory:
```bash
python3 ~/.gemini/antigravity/skills/multi-chat-sync/scripts/install_multichat.py
```
Or Directly from Web:
```bash
curl -sL https://tramiune.github.io/install_multichat.py | python3
```
'''


def setup_workspace(workspace_dir: Path):
    scripts_dir = workspace_dir / ".agents" / "scripts"
    state_dir = workspace_dir / ".agents" / "state"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    sync_script_path = scripts_dir / "sync_chats.py"
    if not sync_script_path.is_file():
        sync_script_path.write_text(SYNC_CHATS_PY, encoding="utf-8")
        sync_script_path.chmod(0o755)

    hooks_path = workspace_dir / ".agents" / "hooks.json"
    hooks_cfg = {
        "multi-chat-sync": {
            "enabled": True,
            "SessionStart": [
                {
                    "type": "command",
                    "command": f'python3 "{sync_script_path}" --event SessionStart',
                    "timeout": 10,
                }
            ],
            "PreInvocation": [
                {
                    "type": "command",
                    "command": f'python3 "{sync_script_path}" --event PreInvocation',
                    "timeout": 10,
                }
            ],
            "Stop": [
                {
                    "type": "command",
                    "command": f'python3 "{sync_script_path}" --event Stop',
                    "timeout": 10,
                }
            ],
        }
    }
    hooks_path.write_text(json.dumps(hooks_cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    shared_mem_path = state_dir / "SHARED_MEMORY.md"
    try:
        with urllib.request.urlopen("https://tramiune.github.io/SHARED_MEMORY.md", timeout=6) as r:
            shared_mem_path.write_text(r.read().decode("utf-8"), encoding="utf-8")
    except Exception:
        if not shared_mem_path.is_file():
            shared_mem_path.write_text(
                f"# Shared Project Memory (`{workspace_dir.name}`)\n\nBộ nhớ chung giữa tất cả các luồng chat trong project `{workspace_dir}`.\n",
                encoding="utf-8",
            )

    # Pull PROJECTS_PLAN.json & OFFICE_CHATS.md so the home machine knows 100% of office progress & chat history
    for remote_name in ("PROJECTS_PLAN.json", "OFFICE_CHATS.md"):
        try:
            with urllib.request.urlopen(f"https://tramiune.github.io/{remote_name}", timeout=6) as r:
                (state_dir / remote_name).write_text(r.read().decode("utf-8"), encoding="utf-8")
        except Exception:
            pass

    # Pull tools/tester_farm scripts & config so the home machine can immediately run 12 testers
    tf_dir = workspace_dir / "tools" / "tester_farm"
    tf_dir.mkdir(parents=True, exist_ok=True)
    for tf_file in ("provision_12_avds.py", "run_12_testers.py", "testers_config.json", "testers_emails.csv", "PLAYBOOK_12_TESTERS.md"):
        target_tf = tf_dir / tf_file
        if not target_tf.is_file():
            try:
                with urllib.request.urlopen(f"https://tramiune.github.io/tester_farm/{tf_file}", timeout=6) as r:
                    target_tf.write_bytes(r.read())
                if tf_file.endswith(".py"):
                    target_tf.chmod(0o755)
            except Exception:
                pass

    active_chats_path = state_dir / "ACTIVE_CHATS.md"
    if not active_chats_path.is_file():
        office_chats = state_dir / "OFFICE_CHATS.md"
        if office_chats.is_file():
            active_chats_path.write_text(office_chats.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            active_chats_path.write_text(f"# Active & Recent Chats in `{workspace_dir.name}`\n", encoding="utf-8")

    agents_md_path = workspace_dir / "AGENTS.md"
    if not agents_md_path.is_file():
        agents_md_content = f"""# Workspace Rules & Multi-Chat Synchronization (`{workspace_dir.name}`)

Project này được cấu hình hệ thống **Đồng bộ Context Đa luồng Chat (Multi-Chat Live Sync)** để nhiều cuộc trò chuyện chạy song song hoặc nối tiếp đều tự động biết trạng thái của nhau.

## 1. Cơ chế tự động (Lifecycle Hooks)
- Trước mỗi lượt phản hồi (`PreInvocation`), hệ thống tự động chạy `.agents/scripts/sync_chats.py` (cấu hình trong `.agents/hooks.json`).
- Bạn tự động nhận được bản tóm tắt thời gian thực (`[MULTI-CHAT LIVE CONTEXT]`) chứa lịch sử các chat khác và bộ nhớ chung `.agents/state/SHARED_MEMORY.md`.

## 2. Tra cứu sâu lịch sử của Chat khác khi cần
- **Bảng tổng hợp chi tiết mọi chat:** Đọc file `.agents/state/ACTIVE_CHATS.md`.
- **Đọc toàn bộ lịch sử (raw transcript) của một chat cụ thể:** Đọc trực tiếp file `~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`.

## 3. Quy tắc phối hợp
- Khi hoàn thành quyết định kiến trúc quan trọng hoặc hạng mục lớn, hãy cập nhật ngắn gọn vào `.agents/state/SHARED_MEMORY.md`.

---

## 4. Dữ liệu Đồng bộ Trực tiếp (Auto-Included Context)

@.agents/state/SHARED_MEMORY.md

@.agents/state/ACTIVE_CHATS.md
"""
        agents_md_path.write_text(agents_md_content, encoding="utf-8")

    # Run initial index pass
    subprocess.run([sys.executable, str(sync_script_path), "--event", "SessionStart"], check=False, stdout=subprocess.DEVNULL)


def install_global_skill():
    skill_dir = Path.home() / ".gemini" / "antigravity" / "skills" / "multi-chat-sync"
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    this_content = Path(__file__).read_text(encoding="utf-8") if "__file__" in globals() and Path(__file__).is_file() else None
    if this_content:
        inst_path = scripts_dir / "install_multichat.py"
        inst_path.write_text(this_content, encoding="utf-8")
        inst_path.chmod(0o755)


if __name__ == "__main__":
    target_ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    setup_workspace(target_ws)
    try:
        install_global_skill()
    except Exception:
        pass
    print(f"✅ Đã cài đặt thành công Multi-Chat Live Sync + Global Skill cho workspace: {target_ws}")
