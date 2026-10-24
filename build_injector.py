# -*- coding: utf-8 -*-
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ZH_CN_PATH = os.path.join(SCRIPT_DIR, "zh_cn.json")
OUT_PATH = os.path.join(SCRIPT_DIR, "i18n-injector.js")

def build():
    if not os.path.isfile(ZH_CN_PATH):
        print(f"[-] 错误: 未找到词库文件 {ZH_CN_PATH}")
        return False

    with open(ZH_CN_PATH, "r", encoding="utf-8") as f:
        zh_dict = json.load(f)

    dict_json_str = json.dumps(zh_dict, ensure_ascii=False, indent=2)

    template = """// ==UserScript==
// @name         Antigravity UI 动态汉化与本地化注入脚本 (zh_cn 完整词库版)
// @namespace    https://github.com/
// @version      2.0.0
// @description  用于 Electron/Web 客户端的前端文本实时捕获与汉化替换，集成 5900+ 条完整 zh_cn 官方词库
// @match        *://*/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  // ==========================================
  // 1. 汉化词库 (用户提供的 zh_cn.json 完整集合: 5900+ 条)
  // ==========================================
  const RAW_ZH_CN = __RAW_DICT_PLACEHOLDER__;

  // 双索引查找表：原样匹配与首尾去空匹配
  const EXACT_MAP = new Map();
  const TRIMMED_MAP = new Map();

  for (const key in RAW_ZH_CN) {
    const val = RAW_ZH_CN[key];
    if (!val || val === key) continue;
    EXACT_MAP.set(key, val);
    const trimmedKey = key.trim();
    if (trimmedKey && !TRIMMED_MAP.has(trimmedKey)) {
      TRIMMED_MAP.set(trimmedKey, val.trim());
    }
  }

  // 正则动态匹配规则 (模式 -> 替换模板)
  const REGEX_RULES = [
    // 匹配完整配额警告提示
    {
      regex: /Your plan's baseline quota will refresh on\\s+([0-9\\/\\-:\\s]+)\\.\\s*To continue using this model now,\\s*enable AI Credit overages\\.?/i,
      replacer: '您套餐的基础配额将于 $1 刷新。若要立即继续使用此模型，请开启 AI 额度超额按量付费。'
    },
    {
      regex: /Your plan's baseline quota will refresh on\\s+([0-9\\/\\-:\\s]+)\\.?/i,
      replacer: '您套餐的基础配额将于 $1 刷新。'
    },
    {
      regex: /Baseline quota will refresh on\\s+([A-Za-z0-9,:\\s\\-\\/]+)/i,
      replacer: '基线配额将于 $1 刷新'
    },
    {
      regex: /Tokens used:\\s*([0-9,]+)/i,
      replacer: '已消耗 Token：$1'
    },
    {
      regex: /Limit reached\\.\\s*Resets in\\s*(.+)/i,
      replacer: '已达到上限，将在 $1 后重置'
    },
    {
      regex: /Expires in\\s*(\\d+)\\s*days?/i,
      replacer: '$1 天后过期'
    },
    {
      regex: /You have used some of your weekly limit,\\s*it will fully refresh in\\s*([0-9A-Za-z,\\s]+)\\./i,
      replacer: '您已消耗了部分每周配额，将在 $1 后完全刷新。'
    },
    {
      regex: /You have used some of your 5-hour limit,\\s*it will fully refresh in\\s*([0-9A-Za-z,\\s]+)\\./i,
      replacer: '您已消耗了部分 5 小时配额，将在 $1 后完全刷新。'
    },
    {
      regex: /You have hit your weekly limit,\\s*it refreshes in\\s*([0-9A-Za-z,\\s]+)\\.\\s*If on a supported paid plan,\\s*you can use AI credits in the interim or upgrade to a higher tier\\./i,
      replacer: '您已达到每周配额上限，将在 $1 后刷新。如果是受支持的付费套餐，您可以临时使用 AI 积分或升级到更高级别套餐。'
    },
    {
      regex: /You have hit your weekly limit,\\s*the 5-hour limit does not currently apply\\.\\s*Your weekly limit will fully refresh in\\s*([0-9A-Za-z,\\s]+)\\./i,
      replacer: '您已达到每周配额上限，5 小时配额目前不适用。您的每周配额将在 $1 后完全刷新。'
    },
    {
      regex: /^New Conversation\\s+(Ctrl\\+[A-Za-z0-9\\+]+)$/i,
      replacer: '新建对话 $1'
    },
    {
      regex: /^Command Palette\\s+(Ctrl\\+[A-Za-z0-9\\+]+)$/i,
      replacer: '命令面板 $1'
    },
    {
      regex: /^(App version|Version)\\s+([0-9\\.]+)$/i,
      replacer: '版本 $2'
    },
    {
      regex: /^Skills\\s+(\\d+)$/i,
      replacer: '技能 $1'
    }
  ];

  // 属性汉化清单 (包含 placeholder、title 提示、无障碍标签等)
  const ATTR_NAMES = ['placeholder', 'title', 'aria-label', 'data-tooltip'];

  // 忽略的标签（避免损坏用户代码块、输入框实际输入内容或脚本）
  const IGNORE_TAGS = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA', 'INPUT']);

  // ==========================================
  // 2. 文本替换与翻译核心逻辑
  // ==========================================

  /**
   * 规范化空白字符（将各种 Unicode 不换行空格、多余空白统一为标准空格）
   */
  function normalizeText(str) {
    return str ? str.replace(/[\\u00A0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000]/g, ' ').replace(/\\s+/g, ' ').trim() : '';
  }

  /**
   * 翻译纯文本字符串
   * @param {string} text 原始文本
   * @returns {string|null} 汉化后文本，若无需替换则返回 null
   */
  function translateString(text) {
    if (!text || !text.trim()) return null;

    // 1. 精确原样匹配 (O(1))
    if (EXACT_MAP.has(text)) {
      return EXACT_MAP.get(text);
    }

    const trimmed = text.trim();
    // 2. 去除首尾空格匹配 (O(1))
    if (TRIMMED_MAP.has(trimmed)) {
      const trans = TRIMMED_MAP.get(trimmed);
      return text.replace(trimmed, trans);
    }

    // 3. 规范化 Unicode 空白匹配 (O(1))
    const normalized = normalizeText(text);
    if (TRIMMED_MAP.has(normalized)) {
      const trans = TRIMMED_MAP.get(normalized);
      return text.replace(trimmed, trans);
    }

    // 4. 正则动态匹配
    for (let i = 0; i < REGEX_RULES.length; i++) {
      const rule = REGEX_RULES[i];
      if (rule.regex.test(text)) {
        return text.replace(rule.regex, rule.replacer);
      }
      if (rule.regex.test(normalized)) {
        return text.replace(trimmed, normalized.replace(rule.regex, rule.replacer));
      }
    }

    return null;
  }

  /**
   * 翻译目标 DOM 元素及其属性
   */
  function translateElementAttributes(el) {
    for (let i = 0; i < ATTR_NAMES.length; i++) {
      const attr = ATTR_NAMES[i];
      const val = el.getAttribute(attr);
      if (val) {
        const trans = translateString(val);
        if (trans && trans !== val) {
          el.setAttribute(attr, trans);
        }
      }
    }
  }

  // ==========================================
  // 3. 性能控制：批量防抖调度器 (Batch Scheduler)
  // ==========================================

  const pendingNodes = new Set();
  let isFrameScheduled = false;

  /**
   * 递归处理单个节点树的文本汉化
   */
  function processNode(node) {
    if (!node) return;

    // 检查元素节点
    if (node.nodeType === Node.ELEMENT_NODE) {
      if (IGNORE_TAGS.has(node.tagName)) return;
      translateElementAttributes(node);
    }

    // 处理纯文本节点
    if (node.nodeType === Node.TEXT_NODE) {
      const original = node.nodeValue;
      const translated = translateString(original);
      if (translated && translated !== original) {
        node.nodeValue = translated;
      }
      return;
    }

    // 递归遍历子节点
    let child = node.firstChild;
    while (child) {
      processNode(child);
      child = child.nextSibling;
    }
  }

  /**
   * 在微任务/帧空闲期执行批量处理，防止频繁触发导致卡顿与死循环
   */
  function flushBatch() {
    isFrameScheduled = false;

    // 临时暂停观察者，杜绝因替换文本导致的“修改-触发-修改”死循环
    observer.disconnect();

    try {
      pendingNodes.forEach((node) => {
        if (node.isConnected) {
          processNode(node);
        }
      });
    } finally {
      pendingNodes.clear();
      startObserving();
    }
  }

  function queueNodeForProcessing(node) {
    pendingNodes.add(node);
    if (!isFrameScheduled) {
      isFrameScheduled = true;
      if (typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(flushBatch, { timeout: 80 });
      } else {
        window.requestAnimationFrame(flushBatch);
      }
    }
  }

  // ==========================================
  // 4. MutationObserver 监听引擎
  // ==========================================

  const observer = new MutationObserver((mutations) => {
    for (let i = 0; i < mutations.length; i++) {
      const mutation = mutations[i];

      if (mutation.type === 'childList') {
        const addedCount = mutation.addedNodes.length;
        for (let j = 0; j < addedCount; j++) {
          const added = mutation.addedNodes[j];
          queueNodeForProcessing(added);
        }
      } else if (mutation.type === 'characterData') {
        queueNodeForProcessing(mutation.target);
      }
    }
  });

  function startObserving() {
    const root = document.body || document.documentElement;
    if (!root) return;

    observer.observe(root, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: false
    });
  }

  // ==========================================
  // 5. 启动与挂载
  // ==========================================

  function init() {
    console.log('%c[Antigravity-i18n] 完整词库引擎 (zh_cn ' + Object.keys(RAW_ZH_CN).length + ' 条) 挂载成功！', 'color: #10b981; font-weight: bold;');
    processNode(document.body || document.documentElement);
    startObserving();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
"""

    final_script = template.replace("__RAW_DICT_PLACEHOLDER__", dict_json_str)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(final_script)

    print(f"[+] 成功将 zh_cn.json (共 {len(zh_dict)} 条) 生成到 i18n-injector.js！大小: {os.path.getsize(OUT_PATH)} 字节")
    return True

if __name__ == "__main__":
    build()
