<div align="center">

# 🚀 Antigravity-i18n

**用于 Google Antigravity 桌面客户端的高性能动态汉化与本地化工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Electron-brightgreen.svg)]()
[![Entries](https://img.shields.io/badge/Dictionary-5900%2B%20Entries-orange.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-green.svg)]()

深度支持 Antigravity 客户端菜单、设置面板、权限管理、模型额度监控与上下文提示的全量汉化。

[功能特点](#-功能特点) • [快速开始](#-快速开始) • [词库扩展](#-词库扩展) • [技术原理](#-核心技术实现) • [一键还原](#-一键还原)

感谢仓库https://github.com/MIMICTE/Antigravity-zh-CN收集的翻译包

</div>

---

## ✨ 功能特点

- 🎯 **超全深度词库**：预置高达 **5900+ 条**精细翻译词条，全面覆盖通用设置（General）、权限管理（Permissions）、外观（Appearance）、通知（Notifications）、模型用量（Models & Usage）、侧边栏菜单等全方位界面。
- ⚡ **内存级无损重构**：采用纯 Python 实现的 Chromium Pickle / asar 内存重构算法，保留所有原生 unpacked 依赖和 SHA256 integrity 完整性，彻底杜绝 Electron `path-to-app` 报错。
- 🛡️ **双通道穿透注入**：针对现代高版本 Electron 的严格 CSP（内容安全策略）限制，采用“主进程特权级执行钩子 + 渲染层 Preload 共享 DOM 原生拦截”双通道机制，保证弹窗、右键菜单和动态加载内容毫秒级翻译且无闪烁。
- 🔤 **Unicode 空白符归一化**：内置对 `\u00A0`（`&nbsp;` 不换行空格）等特殊排版字符的自动折叠处理，解决界面中因特殊空格导致的漏翻问题。
- 🔁 **安全备份与一键秒级还原**：首次安装自动备份官方原版 `app.asar.backup`，双击还原批处理即可瞬间恢复官方英文原版。
- 🛠️ **词库自由扩展**：字典以标准的 `zh_cn.json` 形式独立存储，随时编辑增补词条，运行安装脚本即可全自动编译生效。

---

## 📦 目录结构说明

```text
├── zh_cn.json             # 核心词库文件 (包含 5900+ 条键值对，可直接修改扩充)
├── build_injector.py      # 词库编译器 (将 zh_cn.json 编译成高性能 JS 注入脚本)
├── patch_antigravity.py   # 主安装/注入/还原控制程序
├── 一键安装汉化.bat        # Windows 双击运行自动编译并注入 (带安全防冲突检测)
├── 一键恢复原版.bat        # Windows 双击运行瞬间恢复官方原版
├── i18n-injector.js       # 编译生成的独立注入引擎 (亦可单独作为油猴脚本使用)
├── .gitignore             # Git 忽略配置
├── LICENSE                # MIT 开源协议
└── README.md              # 项目说明文档
```

---

## 🚀 快速开始

### 方式一：双击一键安装（推荐）

1. **退出客户端**：确保已经完全退出 Antigravity 客户端。
2. **执行安装**：双击运行本目录下的 **`一键安装汉化.bat`**。
3. **打开客户端**：启动 Antigravity，即可畅享完整的中文界面！

> 💡 **提示**：脚本已内置进程安全保护，若检测到 Antigravity 正在运行中，会主动提示您先保存关闭，绝不强退您的会话。

### 方式二：命令行方式安装

如果你喜欢使用命令行：

```powershell
# 1. 编译词库并执行一键注入
python patch_antigravity.py install

# 2. 随时恢复原版英文
python patch_antigravity.py restore
```

---

## 🔄 一键还原官方英文

如果在任何时候你想切回原版官方英文界面：
* 直接双击运行 **`一键恢复原版.bat`**，或运行 `python patch_antigravity.py restore` 即可，秒级复原。

---

## 📝 自定义与词库扩展

如果你在日常使用中发现了未翻译的英文词条，添加非常简单：

1. 打开 **`zh_cn.json`**，按照 JSON 格式在末尾添加你的翻译词条：
   ```json
   "New English Phrase": "你的中文翻译"
   ```
2. 保存文件后，双击运行 **`一键安装汉化.bat`**（会自动读取最新修改并重新打包）。
3. 欢迎向本项目提交 Pull Request，共同完善词库！

---

## 🔬 核心技术实现

1. **高频 DOM 防抖与垃圾回收控制**：
   通过 `MutationObserver` 监听 DOM 树变动，并结合 `requestIdleCallback` 与 `requestAnimationFrame` 批量调度处理。在更新文本节点期间主动断开监听器，彻底避免了“修改文本 $\rightarrow$ 触发 Observer $\rightarrow$ 再次修改”的无限死循环。
2. **输入隔离与代码高亮保护**：
   严格过滤 `<code>`, `<pre>`, `<input>`, `<textarea>` 标签，绝不干扰用户输入的 Prompts 或智能体生成的代码内容。
3. **动态时间与数字捕获**：
   采用参数化正则替换策略，完美覆盖配额倒计时（如 `...refresh in X days, Y hours`）、Token 消耗等动态上下文提示。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。欢迎提交 Issue 和 Pull Request！
