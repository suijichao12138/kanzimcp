/* nlp_worker 控制台前端逻辑 */
"use strict";

const $ = (sel) => document.querySelector(sel);

function toast(msg, ok = true) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "show " + (ok ? "ok" : "err");
  setTimeout(() => { t.className = ""; }, 2500);
}

async function api(path, opts = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await resp.json().catch(() => ({ ok: false, error: "响应解析失败" }));
  if (!data.ok) throw new Error(data.error || "请求失败");
  return data;
}

function fmtTime(ts) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  return d.toLocaleString("zh-CN", { hour12: false });
}

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function headersStr(h) {
  if (!h || typeof h !== "object") return "";
  return Object.entries(h).map(([k, v]) => k + ": " + v).join("; ");
}

/* ── 导航 ── */
document.querySelectorAll("#topnav button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#topnav button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const v = btn.dataset.nav;
    switchView(v);
  });
});

function switchView(v) {
  ["sessions", "config", "env", "logs"].forEach((name) => {
    const el = $("#view-" + name);
    el.classList.toggle("active", name === v);
    el.hidden = name !== v;
  });
  if (v === "sessions") loadSessions();
  if (v === "config") loadGroups();
  if (v === "env") loadEnv();
  if (v === "logs") loadLogs();
}

/* ── 状态栏 ── */
async function loadStatus() {
  try {
    const d = await api("/api/status");
    const w = d.data.web;
    $("#statusbar").textContent =
      `通道 ${d.data.channel} · 模型 ${d.data.model} · 会话 ${d.data.session_count} · 控制台 ${w.listen_host}:${w.listen_port}`;
  } catch (e) {
    $("#statusbar").textContent = "状态获取失败";
  }
}

/* ── 会话管理 ── */
async function loadSessions() {
  try {
    const d = await api("/api/sessions");
    const rows = d.data.sessions;
    $("#session-count").textContent = `共 ${rows.length} 个会话`;
    const tb = $("#sessions-table tbody");
    tb.innerHTML = "";
    if (!rows.length) {
      tb.innerHTML = `<tr><td colspan="10" class="muted">暂无会话（发送消息后自动创建）</td></tr>`;
      return;
    }
    for (const r of rows) {
      const tr = document.createElement("tr");
      const statusCls =
        r.status === "active" ? "tag-active"
        : r.status === "error" || (r.last_error && r.status !== "active") ? "tag-error"
        : r.status === "resuming" || r.status === "busy" ? "tag-busy"
        : "tag-done";
      tr.innerHTML = `
        <td><span class="tag ${r.type === "子会话" ? "tag-sub" : "tag-main"}">${r.type}</span></td>
        <td>${esc(r.key)}</td>
        <td class="muted">${esc(r.session_id)}</td>
        <td>${esc(r.model)}</td>
        <td><span class="tag ${statusCls}">${esc(r.status)}</span></td>
        <td class="${r.connected ? "tag-connected" : "tag-offline"}">${r.connected ? "● 连接中" : "○ 持久化"}</td>
        <td class="muted">${fmtTime(r.created_at)}</td>
        <td class="muted">${fmtTime(r.updated_at)}</td>
        <td class="muted">${esc(r.last_error || "-")}</td>
        <td><button class="small" data-reset="${esc(r.key)}">重置</button></td>`;
      tb.appendChild(tr);
    }
    tb.querySelectorAll("[data-reset]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const key = btn.dataset.reset;
        if (!confirm(`重置会话「${key}」？将丢弃该会话的 SDK 历史并重建。`)) return;
        try {
          const d = await api("/api/sessions/reset", {
            method: "POST", body: JSON.stringify({ key }),
          });
          toast(`已重置 → ${d.data.new_session_id.slice(0, 8)}…`);
          loadSessions();
        } catch (e) { toast(e.message, false); }
      });
    });
  } catch (e) { toast(e.message, false); }
}

$("#btn-refresh").addEventListener("click", loadSessions);
$("#btn-clear").addEventListener("click", async () => {
  if (!confirm("清空全部会话？将丢弃所有会话的 SDK 历史并重建。")) return;
  try {
    const d = await api("/api/sessions/clear", { method: "POST", body: "{}" });
    toast(`已清空 ${d.data.count} 个会话`);
    loadSessions();
  } catch (e) { toast(e.message, false); }
});

/* ── 配置修改 ── */
let groupMeta = [];

async function loadGroups() {
  try {
    const d = await api("/api/config");
    groupMeta = d.data.groups;
    const nav = $("#group-nav");
    nav.innerHTML = "";
    groupMeta.forEach((g, i) => {
      const btn = document.createElement("button");
      btn.textContent = g.title;
      btn.dataset.group = g.key;
      if (i === 0) btn.classList.add("active");
      btn.addEventListener("click", () => {
        nav.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        loadGroup(g.key);
      });
      nav.appendChild(btn);
    });
    if (groupMeta.length) loadGroup(groupMeta[0].key);
  } catch (e) { toast(e.message, false); }
}

async function loadGroup(key) {
  try {
    const d = await api("/api/config/" + key);
    const g = d.data;
    $("#group-title").textContent = g.title;
    $("#group-desc").textContent = g.description || "";
    const form = $("#config-form");
    form.innerHTML = "";

    if (g.kind === "fields") {
      for (const f of g.fields) {
        const row = document.createElement("div");
        row.className = "form-row";
        const label = document.createElement("label");
        label.textContent = f.label;
        if (f.is_env_placeholder) {
          const tag = document.createElement("span");
          tag.className = "env-tag";
          tag.textContent = f.env ? `环境变量 ${f.env}` : "环境变量引用";
          label.appendChild(tag);
        }
        row.appendChild(label);

        let input;
        if (f.type === "bool") {
          input = document.createElement("select");
          input.innerHTML = `<option value="true">true</option><option value="false">false</option>`;
          input.value = String(f.value ?? f.default ?? false);
        } else if (f.type === "enum") {
          input = document.createElement("select");
          (f.enum_values || []).forEach((v) => {
            const opt = document.createElement("option");
            opt.value = v; opt.textContent = v;
            input.appendChild(opt);
          });
          input.value = String(f.value ?? f.default ?? "");
        } else if (f.type === "textarea") {
          input = document.createElement("textarea");
          input.value = f.value ?? f.default ?? "";
        } else if (f.type === "list") {
          input = document.createElement("input");
          input.type = "text";
          const arr = Array.isArray(f.value) ? f.value : (f.default || []);
          input.value = Array.isArray(arr) ? arr.join(", ") : String(arr ?? "");
        } else if (f.type === "int" || f.type === "float") {
          input = document.createElement("input");
          input.type = "number";
          input.step = f.type === "float" ? "0.1" : "1";
          input.value = f.value ?? f.default ?? "";
        } else if (f.type === "dict") {
          // dict 字段：每行一个 key → 逗号分隔值列表，可增删行
          input = document.createElement("div");
          const dictVal = (f.value && typeof f.value === "object") ? f.value : {};
          const addDictRow = (k, v) => {
            const line = document.createElement("div");
            line.className = "dict-row";
            line.innerHTML = `
              <input type="text" data-dict-key placeholder="类型名" value="${esc(k)}" style="width:150px">
              <input type="text" data-dict-val placeholder="skill1, skill2" value="${esc(v)}" style="width:420px">
              <button type="button" class="small danger" data-dict-del>删除</button>`;
            line.querySelector("[data-dict-del]").addEventListener("click", () => line.remove());
            input.appendChild(line);
          };
          Object.entries(dictVal).forEach(([k, v]) => addDictRow(k, Array.isArray(v) ? v.join(", ") : String(v)));
          const addBtn = document.createElement("button");
          addBtn.type = "button";
          addBtn.textContent = "+ 添加类型";
          addBtn.addEventListener("click", () => addDictRow("", ""));
          input.appendChild(addBtn);
        } else {
          input = document.createElement("input");
          input.type = "text";
          input.value = f.value ?? f.default ?? "";
        }
        input.dataset.key = f.key;
        input.dataset.type = f.type;
        if (f.missing_env) {
          input.classList.add("missing");
          const tip = document.createElement("div");
          tip.className = "missing-tip";
          tip.textContent = `⚠️ 环境变量 ${f.env} 缺失（.env 中未定义）`;
          row.appendChild(tip);
        }
        row.appendChild(input);
        if (f.help) {
          const help = document.createElement("div");
          help.className = "help";
          help.textContent = f.help;
          row.appendChild(help);
        }
        form.appendChild(row);
      }
    } else if (g.kind === "dict_of_servers") {
      // 每个 server 一个字段块
      const servers = g.servers || {};
      const names = Object.keys(servers);
      if (!names.length) {
        form.innerHTML = `<div class="muted">暂无 MCP 服务配置。</div>`;
      }
      const addServerBox = (name, s) => {
        const box = document.createElement("div");
        box.className = "form-row mcp-box";
        box.innerHTML = `
          <label>${esc(name)} <span class="env-tag">MCP 服务</span></label>
          <div class="mcp-grid">
            <div class="mcp-item">
              <div class="mcp-label">启用</div>
              <select class="mcp-select" data-mcp="${esc(name)}" data-mcp-field="enabled">
                <option value="true" ${s.enabled ? "selected" : ""}>true</option>
                <option value="false" ${!s.enabled ? "selected" : ""}>false</option>
              </select>
            </div>
            <div class="mcp-item mcp-wide">
              <div class="mcp-label">url</div>
              <input type="text" data-mcp="${esc(name)}" data-mcp-field="url" value="${esc(s.url)}">
            </div>
            <div class="mcp-item">
              <div class="mcp-label">type</div>
              <input type="text" data-mcp="${esc(name)}" data-mcp-field="type" value="${esc(s.type)}">
            </div>
            <div class="mcp-item mcp-wide">
              <div class="mcp-label">headers（如 X-Kanzi-User: suijichao; K2: v2）</div>
              <input type="text" data-mcp="${esc(name)}" data-mcp-field="headers" value="${esc(headersStr(s.headers))}">
            </div>
            <div class="mcp-item">
              <div class="mcp-label">timeout_seconds</div>
              <input type="text" data-mcp="${esc(name)}" data-mcp-field="timeout_seconds" value="${esc(s.timeout_seconds)}">
            </div>
            <div class="mcp-item">
              <div class="mcp-label">tools（如 ["*"]）</div>
              <input type="text" data-mcp="${esc(name)}" data-mcp-field="tools" value='${esc(JSON.stringify(s.tools))}'>
            </div>
          </div>
          <div class="mcp-footer">
            <button type="button" class="small danger" data-mcp-del="${esc(name)}">删除该服务</button>
          </div>`;
        box.querySelector("[data-mcp-del]").addEventListener("click", () => box.remove());
        form.appendChild(box);
      };
      for (const name of names) {
        addServerBox(name, servers[name]);
      }
      const addSrvBtn = document.createElement("button");
      addSrvBtn.type = "button";
      addSrvBtn.textContent = "+ 添加 MCP 服务";
      addSrvBtn.addEventListener("click", () => {
        const namesUsed = new Set(Array.from(form.querySelectorAll(".mcp-box label")).map(l => l.textContent.trim().split(" ")[0]));
        let n = 1;
        while (namesUsed.has("new-server-" + n)) n++;
        addServerBox("new-server-" + n, { enabled: true, type: "http", url: "", headers: {}, tools: ["*"], timeout_seconds: 300 });
      });
      form.appendChild(addSrvBtn);
    } else if (g.kind === "skill_entries") {
      // 大小限制字段（api 返回 max_file_bytes/max_total_bytes）
      const maxBox = document.createElement("div");
      maxBox.className = "form-row";
      maxBox.innerHTML = `
        <label>单个 skill 最大字节
          <input type="number" data-skill-maxfile value="${esc(g.max_file_bytes)}" style="width:120px">
        </label>
        <label>全部 skill 最大字节
          <input type="number" data-skill-maxtotal value="${esc(g.max_total_bytes)}" style="width:120px">
        </label>
        <div class="help">单个 skill 大小上限 + 全部 skill 总大小上限，超过会启动报错。</div>`;
      form.appendChild(maxBox);
      const addRow = (path, enabled) => {
        const row = document.createElement("div");
        row.className = "form-row";
        row.innerHTML = `
          <input type="text" data-skill-path placeholder="skill 目录路径" value="${esc(path)}" style="width:520px">
          <label style="display:inline;font-weight:normal">启用
            <select data-skill-enabled style="width:auto">
              <option value="true" ${enabled ? "selected" : ""}>true</option>
              <option value="false" ${!enabled ? "selected" : ""}>false</option>
            </select>
          </label>
          <button type="button" class="small danger" data-skill-del>删除</button>`;
        row.querySelector("[data-skill-del]").addEventListener("click", () => row.remove());
        form.appendChild(row);
      };
      (g.entries || []).forEach((e) => addRow(e.path, e.enabled));
      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.textContent = "+ 添加 skill 路径";
      addBtn.addEventListener("click", () => addRow("", true));
      form.appendChild(addBtn);
    }

    const saveBtn = document.createElement("button");
    saveBtn.id = "save-btn";
    saveBtn.textContent = "保存";
    saveBtn.type = "button";
    saveBtn.addEventListener("click", () => saveGroup(g));
    form.appendChild(saveBtn);
  } catch (e) { toast(e.message, false); }
}

async function saveGroup(g) {
  try {
    const form = $("#config-form");
    const payload = { fields: {} };
    if (g.kind === "fields") {
      form.querySelectorAll("[data-key]").forEach((el) => {
        const key = el.dataset.key;
        const type = el.dataset.type;
        let val;
        if (type === "bool") val = el.value === "true";
        else if (type === "int") val = el.value === "" ? null : Number(el.value);
        else if (type === "float") val = el.value === "" ? null : Number(el.value);
        else if (type === "list") {
          val = el.value.split(",").map((x) => x.trim()).filter(Boolean);
        } else if (type === "dict") {
          const dict = {};
          el.querySelectorAll("[data-dict-key]").forEach((line) => {
            const k = line.value.trim();
            const v = line.closest(".dict-row").querySelector("[data-dict-val]").value;
            if (k) dict[k] = v.split(",").map((x) => x.trim()).filter(Boolean);
          });
          val = dict;
        } else val = el.value;
        payload.fields[key] = val;
      });
    } else if (g.kind === "dict_of_servers") {
      const servers = {};
      form.querySelectorAll("[data-mcp]").forEach((el) => {
        const name = el.dataset.mcp;
        const field = el.dataset.mcpField;
        if (!servers[name]) servers[name] = {};
        if (field === "enabled") servers[name][field] = el.value === "true";
        else if (field === "timeout_seconds") servers[name][field] = Number(el.value || 300);
        else if (field === "tools") {
          try { servers[name][field] = JSON.parse(el.value || '["*"]'); }
          catch { servers[name][field] = ["*"]; }
        } else if (field === "headers") {
          const h = {};
          String(el.value).split(";").forEach((pair) => {
            const idx = pair.indexOf(":");
            if (idx > 0) h[pair.slice(0, idx).trim()] = pair.slice(idx + 1).trim();
          });
          servers[name][field] = h;
        } else servers[name][field] = el.value;
      });
      payload.servers = servers;
    } else if (g.kind === "skill_entries") {
      const entries = [];
      form.querySelectorAll("[data-skill-path]").forEach((el) => {
        entries.push({
          path: el.value,
          enabled: el.closest(".form-row").querySelector("[data-skill-enabled]").value === "true",
        });
      });
      payload.entries = entries;
      payload.max_file_bytes = Number($("[data-skill-maxfile]").value || 131072);
      payload.max_total_bytes = Number($("[data-skill-maxtotal]").value || 524288);
    }
    const gkey = g.key || g.group;
    await api("/api/config/" + gkey, { method: "POST", body: JSON.stringify(payload) });
    toast("已保存（重启 nlp_worker 后完全生效）");
  } catch (e) { toast(e.message, false); }
}

/* ── 环境变量 ── */
async function loadEnv() {
  try {
    const d = await api("/api/env");
    const items = d.data.env;
    const missing = d.data.missing || [];
    $("#env-missing").textContent = missing.length
      ? `⚠️ 被 config 引用但 .env 缺失: ${missing.join(", ")}`
      : `共 ${items.length} 个环境变量`;
    const tb = $("#env-table tbody");
    tb.innerHTML = "";
    for (const it of items) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${esc(it.key)}</td>
        <td>${esc(it.masked || "（空）")}</td>
        <td class="muted">${it.refs.length ? esc(it.refs.join(", ")) : "-"}</td>
        <td><button class="small" data-env-del="${esc(it.key)}">删除</button></td>`;
      tb.appendChild(tr);
    }
    tb.querySelectorAll("[data-env-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const key = btn.dataset.envDel;
        if (!confirm(`删除环境变量 ${key}？`)) return;
        try {
          await api("/api/env/" + encodeURIComponent(key), { method: "DELETE" });
          toast("已删除");
          loadEnv();
        } catch (e) { toast(e.message, false); }
      });
    });
  } catch (e) { toast(e.message, false); }
}

$("#btn-env-refresh").addEventListener("click", loadEnv);
$("#btn-env-add").addEventListener("click", async () => {
  const key = $("#env-new-key").value.trim();
  const value = $("#env-new-value").value;
  if (!key) { toast("请输入 KEY", false); return; }
  try {
    await api("/api/env", { method: "POST", body: JSON.stringify({ key, value }) });
    toast("已添加");
    $("#env-new-key").value = ""; $("#env-new-value").value = "";
    loadEnv();
  } catch (e) { toast(e.message, false); }
});

/* ── 日志 ── */
async function loadLogs() {
  try {
    const lines = $("#logs-lines").value || 200;
    const d = await api("/api/logs?lines=" + lines);
    const data = d.data;
    const box = $("#logs-box");
    box.textContent = (data.lines || []).join("\n") + (data.truncated ? "\n…（仅显示尾部 " + lines + " 行，共 " + data.total + " 行）" : "");
    box.scrollTop = box.scrollHeight;
    $("#logs-info").textContent = data.log_path
      ? `日志: ${data.log_path}`
      : "未配置日志文件（config.logging.file）";
  } catch (e) { toast(e.message, false); }
}

$("#btn-logs-refresh").addEventListener("click", loadLogs);
$("#logs-lines").addEventListener("change", loadLogs);
$("#btn-restart").addEventListener("click", async () => {
  if (!confirm("重启 nlp_worker？将断开当前连接并重新拉起进程（约 10-30 秒）。")) return;
  try {
    const d = await api("/api/restart", { method: "POST", body: "{}" });
    toast("已触发重启，新进程 PID " + d.data.pid + "，旧进程即将退出…");
  } catch (e) {
    // 旧进程可能已开始退出，连接中断也算预期
    toast("重启已触发（连接可能中断，页面稍后刷新）");
  }
  setTimeout(() => location.reload(), 3000);
});

/* ── 启动 ── */
loadStatus();
setInterval(loadStatus, 15000);
loadSessions();
