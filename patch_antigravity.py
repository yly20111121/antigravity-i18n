# -*- coding: utf-8 -*-
"""
Antigravity 桌面客户端自动汉化注入与恢复工具
双通道注入体系：
1. 主进程全局 web-contents-created 钩子 (通过 executeJavaScript 在 Main World 强制注入)
2. 渲染层 preload.js 原生自启动 (在 DOMContentLoaded / readyState 阶段先行拦截)
彻底解决 CSP 拦截与内联 script 报错问题，实现 100% 界面实时汉化。
"""

import os
import sys
import shutil
import struct
import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INJECTOR_JS_SOURCE = os.path.join(SCRIPT_DIR, "i18n-injector.js")

CANDIDATE_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\antigravity"),
    os.path.expandvars(r"%PROGRAMFILES%\antigravity"),
    os.path.expandvars(r"%ProgramFiles(x86)%\antigravity"),
]


def find_antigravity_dir():
    """查找 Antigravity 安装目录"""
    for path in CANDIDATE_PATHS:
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "Antigravity.exe")):
            return path
    return None


def check_antigravity_running():
    """检查客户端进程是否正在运行"""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq Antigravity.exe"],
            creationflags=0x08000000,
            text=True,
            errors="ignore",
        )
        return "antigravity.exe" in output.lower()
    except Exception:
        return False


MAIN_HOOK_MARKER = "// === ANTIGRAVITY I18N MAIN HOOK ==="
MAIN_HOOK_CODE = """
// === ANTIGRAVITY I18N MAIN HOOK ===
try {
  const { app: _i18nApp } = require('electron');
  const _fs = require('fs');
  const _path = require('path');
  const _i18nFile = _path.join(__dirname, 'i18n-injector.js');
  if (_fs.existsSync(_i18nFile)) {
    const _i18nCode = _fs.readFileSync(_i18nFile, 'utf8');
    const _inject = (_wc) => {
      if (_wc && !_wc.isDestroyed()) {
        _wc.executeJavaScript(_i18nCode).catch(() => {});
      }
    };
    _i18nApp.on('web-contents-created', (_event, _contents) => {
      _contents.on('dom-ready', () => _inject(_contents));
      _contents.on('did-finish-load', () => _inject(_contents));
      _contents.on('did-navigate', () => _inject(_contents));
      _contents.on('did-navigate-in-page', () => _inject(_contents));
    });
  }
} catch (_err) {
  console.error('[i18n main hook error]', _err);
}
// === ANTIGRAVITY I18N MAIN HOOK END ===
"""


def patch_asar_in_place(source_asar_path, dest_asar_path, injector_js_path):
    """
    解析并重构 asar：
    1. 注入 dist/i18n-injector.js
    2. 主进程 dist/main.js 添加全局 web-contents-created 注入钩子
    3. 渲染层 dist/preload.js 内联嵌入自运行汉化逻辑
    """
    print("[*] 正在解析原始 app.asar 结构...")
    with open(source_asar_path, "rb") as f:
        magic = struct.unpack("<I", f.read(4))[0]
        payload_size = struct.unpack("<I", f.read(4))[0]
        header_size = struct.unpack("<I", f.read(4))[0]
        json_len = struct.unpack("<I", f.read(4))[0]
        header = json.loads(f.read(json_len).decode("utf-8"))

        base_offset = 8 + payload_size

        files_data = {}
        packed_nodes = []

        def collect_nodes(d, prefix=""):
            for k in sorted(d.keys()):
                v = d[k]
                if "files" in v:
                    collect_nodes(v["files"], prefix + "/" + k)
                else:
                    rel = (prefix + "/" + k).lstrip("/")
                    if not v.get("unpacked"):
                        f.seek(base_offset + int(v["offset"]))
                        files_data[rel] = f.read(v["size"])
                        packed_nodes.append((rel, v))

        collect_nodes(header["files"])

    print(f"[+] 读取原始模块完成，共 {len(files_data)} 个打包文件。")

    with open(injector_js_path, "rb") as inj_f:
        injector_bytes = inj_f.read()
    injector_text = injector_bytes.decode("utf-8")

    # 1. 注入 dist/i18n-injector.js
    files_data["dist/i18n-injector.js"] = injector_bytes
    inj_node = {"size": len(injector_bytes), "offset": "0"}
    header["files"]["dist"]["files"]["i18n-injector.js"] = inj_node
    if not any(r == "dist/i18n-injector.js" for r, _ in packed_nodes):
        packed_nodes.append(("dist/i18n-injector.js", inj_node))

    # 2. 注入主进程 dist/main.js (全局钩子，覆盖主窗口、弹窗、webview)
    if "dist/main.js" in files_data:
        main_content = files_data["dist/main.js"].decode("utf-8", errors="ignore")
        if MAIN_HOOK_MARKER not in main_content:
            main_content += "\n" + MAIN_HOOK_CODE
            files_data["dist/main.js"] = main_content.encode("utf-8")
            header["files"]["dist"]["files"]["main.js"]["size"] = len(files_data["dist/main.js"])
            print("[+] 已向主进程 dist/main.js 植入全局 WebContents 监听钩子。")

    # 3. 注入渲染进程 dist/preload.js (内联直接自运行，彻底避免 CSP 拦截)
    if "dist/preload.js" in files_data:
        preload_content = files_data["dist/preload.js"].decode("utf-8", errors="ignore")
        if "// === ANTIGRAVITY I18N INJECTOR START ===" in preload_content:
            preload_content = preload_content.split("// === ANTIGRAVITY I18N INJECTOR START ===")[0].strip()
        if "// === ANTIGRAVITY I18N INLINE START ===" in preload_content:
            preload_content = preload_content.split("// === ANTIGRAVITY I18N INLINE START ===")[0].strip()

        preload_content += f"\n\n// === ANTIGRAVITY I18N INLINE START ===\ntry {{\n{injector_text}\n}} catch (_e) {{ console.error('[preload i18n error]', _e); }}\n// === ANTIGRAVITY I18N INLINE END ===\n"
        files_data["dist/preload.js"] = preload_content.encode("utf-8")
        header["files"]["dist"]["files"]["preload.js"]["size"] = len(files_data["dist/preload.js"])
        print("[+] 已向渲染层 dist/preload.js 直接内联全量汉化与监听逻辑。")

    # 4. 顺序更新所有打包文件的 offset
    cur_offset = 0
    for rel, node in packed_nodes:
        node["offset"] = str(cur_offset)
        cur_offset += node["size"]

    # 5. 生成新 asar 头部并写出
    new_header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    new_json_len = len(new_header_json)
    padding_len = (4 - (new_json_len % 4)) % 4
    padded_json = new_header_json + (b"\x00" * padding_len)
    new_header_size = new_json_len + 4 + padding_len
    new_payload_size = new_header_size + 4

    temp_out = dest_asar_path + ".tmp"
    with open(temp_out, "wb") as out_f:
        out_f.write(struct.pack("<IIII", 4, new_payload_size, new_header_size, new_json_len))
        out_f.write(padded_json)
        for rel, node in packed_nodes:
            out_f.write(files_data[rel])

    if os.path.isfile(dest_asar_path):
        os.remove(dest_asar_path)
    os.rename(temp_out, dest_asar_path)
    print(f"[+] 汉化版 app.asar 生成完毕！大小: {os.path.getsize(dest_asar_path)} 字节。")


def install_patch(app_dir=None):
    if not app_dir:
        app_dir = find_antigravity_dir()

    if not app_dir or not os.path.isdir(app_dir):
        print("[-] 未能自动找到 Antigravity 安装目录，请手动确认路径！")
        return False

    print(f"[+] 找到客户端目录: {app_dir}")

    if check_antigravity_running():
        print("=" * 60)
        print("【安全提醒】检测到 Antigravity 客户端当前正在运行中！")
        print("为了避免文件写入冲突：")
        print("请您先保存当前工作，并【手动退出/关闭 Antigravity 客户端】后再运行本脚本。")
        print("=" * 60)
        return False

    # 自动重新编译最新的 zh_cn.json
    zh_cn_json = os.path.join(SCRIPT_DIR, "zh_cn.json")
    build_script = os.path.join(SCRIPT_DIR, "build_injector.py")
    if os.path.isfile(zh_cn_json) and os.path.isfile(build_script):
        print("[*] 检测到自定义词库 zh_cn.json，正在自动编译到注入脚本...")
        try:
            from build_injector import build
            build()
            print("[+] 自定义词库编译完成！")
        except Exception:
            try:
                subprocess.run([sys.executable, build_script], check=True, stdout=subprocess.DEVNULL)
                print("[+] 自定义词库编译完成！")
            except Exception as e:
                print(f"[-] 编译自定义词库警告: {e}")

    res_dir = os.path.join(app_dir, "resources")
    asar_path = os.path.join(res_dir, "app.asar")
    asar_backup = os.path.join(res_dir, "app.asar.backup")
    app_extract_dir = os.path.join(res_dir, "app")

    if os.path.isdir(app_extract_dir):
        try:
            shutil.rmtree(app_extract_dir)
        except Exception:
            pass

    # 1. 备份原版 app.asar
    if os.path.isfile(asar_path) and not os.path.isfile(asar_backup):
        print(f"[*] 备份原始官方 app.asar -> {os.path.basename(asar_backup)}...")
        shutil.copy2(asar_path, asar_backup)
        print("[+] 官方原始文件备份成功！")

    source_for_patch = asar_backup if os.path.isfile(asar_backup) else asar_path
    if not os.path.isfile(source_for_patch):
        print("[-] 未找到 app.asar，无法进行注入！")
        return False

    if not os.path.isfile(INJECTOR_JS_SOURCE):
        print(f"[-] 错误: 未在当前目录找到 {INJECTOR_JS_SOURCE}")
        return False

    # 2. 执行双通道注入重构打包
    patch_asar_in_place(source_for_patch, asar_path, INJECTOR_JS_SOURCE)

    print("\n" + "=" * 50)
    print("【双通道汉化安装成功！】")
    print("已成功打通主进程 executeJavaScript 与 Preload 原生层。")
    print("现在启动 Antigravity 客户端即可享受完整的汉化界面！")
    print("=" * 50 + "\n")
    return True


def restore_original(app_dir=None):
    if not app_dir:
        app_dir = find_antigravity_dir()

    if not app_dir or not os.path.isdir(app_dir):
        print("[-] 未能自动找到 Antigravity 安装目录！")
        return False

    print(f"[+] 找到客户端目录: {app_dir}")

    if check_antigravity_running():
        print("=" * 60)
        print("【安全提醒】检测到 Antigravity 客户端当前正在运行中！")
        print("请您先【手动退出/关闭 Antigravity 客户端】后再运行恢复脚本。")
        print("=" * 60)
        return False

    res_dir = os.path.join(app_dir, "resources")
    asar_path = os.path.join(res_dir, "app.asar")
    asar_backup = os.path.join(res_dir, "app.asar.backup")
    app_extract_dir = os.path.join(res_dir, "app")

    # 1. 还原官方原版 app.asar
    if os.path.isfile(asar_backup):
        print(f"[*] 正在从备份恢复官方原始 app.asar...")
        if os.path.isfile(asar_path):
            os.remove(asar_path)
        shutil.copy2(asar_backup, asar_path)
        print("[+] 原版 app.asar 已成功恢复！")
    else:
        print("[*] 未发现 app.asar.backup，当前可能已经是原版。")

    # 2. 清理残留目录
    if os.path.isdir(app_extract_dir):
        try:
            shutil.rmtree(app_extract_dir)
            print("[+] 已清理残留解包目录。")
        except Exception:
            pass

    print("\n" + "=" * 50)
    print("【已恢复官方原版英文界面！】")
    print("重新启动 Antigravity 即可。")
    print("=" * 50 + "\n")
    return True


if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "install"
    custom_path = sys.argv[2] if len(sys.argv) > 2 else None

    if action == "restore":
        restore_original(custom_path)
    else:
        install_patch(custom_path)
