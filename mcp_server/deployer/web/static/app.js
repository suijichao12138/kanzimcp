/* kanzi-deployer 前端逻辑 */
'use strict';

const $ = (id) => document.getElementById(id);
let _taskTimer = null;
let _autoTimer = null;

// ══════════ 通用 ══════════

function toast(msg, kind) {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast ' + (kind === 'err' ? 'toast-err' : kind === 'ok' ? 'toast-ok' : '');
  setTimeout(() => t.classList.add('hidden'), 3600);
}

async function call(method, path, body) {
  const opt = { method, headers: {} };
  if (body !== undefined) {
    opt.headers['Content-Type'] = 'application/json';
    opt.body = JSON.stringify(body);
  }
  try {
    const r = await fetch(path, opt);
    const j = await r.json().catch(() => ({ ok: false, error: 'HTTP ' + r.status }));
    return j;
  } catch (e) {
    return { ok: false, error: '请求失败: ' + e.message };
  }
}

// ══════════ 标签切换 ══════════

document.querySelectorAll('.tab').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    $('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'logs') loadLog();
    if (btn.dataset.tab === 'settings' || btn.dataset.tab === 'config') loadWizard();
    if (btn.dataset.tab === 'config') loadConfig();
  };
});

// ══════════ 状态总览 ══════════

async function refreshStatus() {
  const r = await call('GET', '/api/status');
  if (!r.ok) {
    $('status-dot').className = 'dot dot-red';
    $('status-text').textContent = '离线';
    return;
  }
  const d = r.data;
  $('status-dot').className = 'dot dot-green';
  $('status-text').textContent = '运行中';
  $('ov-local').textContent = d.local_tag || '(未部署)';
  $('ov-latest').textContent = d.latest_tag || '(未检查)';
  const badge = $('upd-badge');
  badge.classList.toggle('hidden', !d.update_available);
  $('upg-target').textContent = d.latest_tag
    ? `目标版本：${d.latest_tag}` : '（先点“检查更新”获取远端版本）';

  const rows = d.components.map((c) => `
    <tr>
      <td><b>${c.name}</b></td>
      <td class="muted">${c.exe}</td>
      <td><span class="pill ${c.running ? 'pill-ok' : 'pill-bad'}">${c.running ? '运行中' : '未运行'}</span></td>
      <td class="muted">${c.health_detail}</td>
      <td class="muted">${c.pid || '—'}</td>
      <td>
        <button class="btn btn-sm" onclick="restartComp('${c.name}')">重启</button>
      </td>
    </tr>`).join('');
  $('ov-comps').innerHTML = rows || '<tr><td colspan="6" class="muted">无组件</td></tr>';
}

async function checkUpdate() {
  toast('正在检查…');
  const r = await call('GET', '/api/check_update');
  if (!r.ok) return toast(r.error || '检查失败', 'err');
  const d = r.data;
  toast(d.update_available
    ? `发现新版本 ${d.latest}（当前 ${d.local || '未部署'}）`
    : `已是最新版本 ${d.latest}`, 'ok');
  refreshStatus();
}

async function checkEnv() {
  const r = await call('GET', '/api/env');
  if (!r.ok) return toast(r.error || '检测失败', 'err');
  const items = r.data.items || [];
  $('ov-env').innerHTML = items.map((i) => `
    <tr>
      <td>${i.name}${i.required ? ' <span class="req">*</span>' : ''}</td>
      <td><span class="pill ${i.ok ? 'pill-ok' : 'pill-bad'}">${i.ok ? '可用' : '不可用'}</span></td>
      <td class="muted">${escapeHtml(i.detail || '')}</td>
    </tr>`).join('');
  $('env-card').style.display = '';
  toast(r.data.ok ? '环境检查通过' : '环境不满足编译条件', r.data.ok ? 'ok' : 'err');
}

async function restartComp(name) {
  const msg = name === 'all'
    ? '确认重启全部组件？\n\n⚠️ relay 重启会连带重启 http 和 feishu，服务会短暂中断。'
    : `确认重启 ${name}？` + (name === 'relay'
      ? '\n\n⚠️ relay 重启会连带重启 http 和 feishu。' : '');
  if (!confirm(msg)) return;
  toast('正在重启 ' + name + ' …');
  const r = await call('POST', '/api/restart', { name });
  if (!r.ok) return toast(r.error || '重启失败', 'err');
  toast('重启完成', 'ok');
  setTimeout(refreshStatus, 1500);
}

// ══════════ 部署 / 升级 ══════════

async function doUpgrade() {
  const latest = $('ov-latest').textContent;
  if (!confirm('确认升级？\n\n这将重新拉取源码、编译三个组件并重启服务。\n期间服务会短暂中断，正在执行的任务会结束。\n\n确认继续？')) return;
  const r = await call('POST', '/api/upgrade', {});
  if (!r.ok) return toast(r.error || '启动升级失败', 'err');
  watchTask(r.data.id);
}

async function doDeploy() {
  if (!confirm('确认一键部署？\n\n流程：拉源码 → 编译 → 生成配置 → 重启组件。\n期间服务会短暂中断。')) return;
  const r = await call('POST', '/api/deploy', {});
  if (!r.ok) return toast(r.error || '启动部署失败', 'err');
  watchTask(r.data.id);
}

function watchTask(id) {
  $('task-card').style.display = '';
  $('task-log').textContent = '';
  clearInterval(_taskTimer);
  _taskTimer = setInterval(async () => {
    const r = await call('GET', '/api/task?id=' + id);
    if (!r.ok) return;
    const t = r.data;
    $('task-title').textContent = t.title;
    $('task-bar').style.width = t.percent + '%';
    $('task-step').textContent = `[${t.status}] ${t.step} — ${t.detail || ''}`;
    $('task-log').textContent = (t.log || []).join('\n');
    $('task-log').scrollTop = $('task-log').scrollHeight;
    if (!t.running) {
      clearInterval(_taskTimer);
      _taskTimer = null;
      toast(t.status === 'success' ? '任务完成' : '任务失败：' + t.detail,
            t.status === 'success' ? 'ok' : 'err');
      refreshStatus();
    }
  }, 1500);
}

// ══════════ 配置 ══════════

async function loadConfig() {
  const name = $('cfg-sel').value;
  $('cfg-text').value = '加载中…';
  $('cfg-hint').textContent = '';
  const r = await call('GET', '/api/config?name=' + name);
  if (!r.ok) { $('cfg-text').value = ''; return toast(r.error || '读取失败', 'err'); }
  $('cfg-text').value = r.data.content || '';
  const rst = r.data.restart || [];
  $('cfg-hint').textContent = rst.length
    ? '保存后需重启：' + rst.join(', ')
    : '保存后无需重启（热更新）';
}

async function saveConfig() {
  const name = $('cfg-sel').value;
  const content = $('cfg-text').value;
  try { JSON.parse(content); }
  catch (e) { return toast('JSON 格式错误：' + e.message, 'err'); }
  const r = await call('POST', '/api/config', { name, content });
  if (!r.ok) return toast(r.error || '保存失败', 'err');
  toast('已保存' + ((r.data.restart || []).length
    ? '，需要重启：' + r.data.restart.join(', ') : ''), 'ok');
}

// ══════════ 首次配置向导 ══════════

let _wiz = null;

async function loadWizard() {
  const r = await call('GET', '/api/wizard');
  if (!r.ok) return;
  _wiz = r.data;
  renderWizard();
}

function renderWizard() {
  const w = _wiz || {};
  const repo = w.repo || {};
  const web = w.web || {};
  const fn = w.feishu_notify || {};
  const cp = w.comp_params || {};
  const http = cp.http || {};
  const fs = cp.feishu || {};

  $('wiz-body').innerHTML = `
  <div class="wiz-group">
    <h3>① 更新源（Gitee 仓库）</h3>
    ${field('仓库地址', 'repo-url', repo.url || '', '部署管理器从这里拉取源码并编译。填 Gitee 镜像地址。', true)}
    ${field('分支', 'repo-branch', repo.branch || 'main', '主分支名，一般为 main。')}
    ${field('检查间隔(秒)', 'repo-poll', repo.poll_interval_s || 60, '后台多久查一次远端版本。只做提示，不会自动升级。', false, 'number')}
  </div>

  <div class="wiz-group">
    <h3>② 管理页面</h3>
    ${field('监听地址', 'web-bind', web.bind || '0.0.0.0', '0.0.0.0 表示局域网内都可访问；改成 127.0.0.1 则只能本机访问。')}
    ${field('端口', 'web-port', web.port || 9100, '管理网页端口，注意避开 58080 / 9001 / 8081。', false, 'number')}
    ${field('访问用户名', 'web-user', (web.auth || {}).user || 'admin', '登录管理页面的用户名。')}
    ${field('访问密码', 'web-pass', '', '留空则不修改当前密码。首次配置建议设置。', false, 'password')}
  </div>

  <div class="wiz-group">
    <h3>③ relay 中继</h3>
    ${field('监听端口', 'relay-port', (cp.relay || {}).port || 58080, '中继服务端口，各组件都连它。一般不用改。', false, 'number')}
  </div>

  <div class="wiz-group">
    <h3>④ http 组件（MCP over HTTP）</h3>
    ${field('监听地址', 'http-listen', http.listen || '0.0.0.0:9001', '必须填 0.0.0.0:9001 才能让远程 Copilot 连进来。改成 127.0.0.1 则只能本机连。', true)}
    ${field('relay 地址', 'http-relay', http.relay_base || 'ws://127.0.0.1:58080', '中继地址。本机部署填 127.0.0.1；跨机部署填 relay 所在机器 IP。', true)}
    ${field('外置结果对外 IP', 'http-pubhost', http.result_public_host || '', '⚠️ 大结果落盘后 URL 里用的 IP，必须是 AI 能访问到的本机 IP。填 0.0.0.0 会导致下载失败。', false)}
    ${field('外置阈值(记录数)', 'http-ent', http.result_threshold_entries || 50, '返回结果超过这么多条就落盘成文件，只回 URL。', false, 'number')}
    ${field('外置阈值(字节)', 'http-bytes', http.result_threshold_bytes || 4096, '返回文本超过这么多字节就落盘。截图 base64 必然超，会被外置。', false, 'number')}
  </div>

  <div class="wiz-group">
    <h3>⑤ 飞书桥</h3>
    ${field('文件服务监听 IP', 'fs-host', fs.http_host || '0.0.0.0', '飞书文件服务的绑定地址，一般 0.0.0.0。')}
    ${field('文件服务端口', 'fs-port', fs.http_port || 8081, '飞书上传/下载文件用的端口。', false, 'number')}
    <div class="field">
      <label>白名单用户</label>
      <div class="desc">允许使用服务的用户名，一行一个。对应 relay 的通道名（如 suijichao）。</div>
      <textarea id="wiz-users" style="min-height:90px">${escapeHtml((w.users || []).join('\n'))}</textarea>
    </div>
    <p class="muted">飞书机器人（bot）先留空也能部署，后续在“配置”页编辑 feishu_config.json 添加。</p>
  </div>

  <div class="wiz-group">
    <h3>⑥ 飞书通知</h3>
    ${field('App ID', 'nt-appid', fn.app_id || '', '部署管理器发通知用的飞书应用 ID。')}
    ${field('App Secret', 'nt-secret', fn.app_secret || '', '已保存的密钥显示为掩码，不改就保留原值。', false, 'password')}
    ${field('接收人 ID', 'nt-recv', fn.receive_id || '', '接收通知的 open_id 或群 ID。')}
    ${field('ID 类型', 'nt-type', fn.receive_id_type || 'open_id', 'open_id / chat_id / user_id，一般用 open_id。')}
  </div>`;
}

function field(label, id, value, desc, required, type) {
  const t = type || 'text';
  return `<div class="field">
    <label>${label}${required ? ' <span class="req">*</span>' : ''}</label>
    <div class="desc">${desc || ''}</div>
    <input type="${t}" id="${id}" value="${escapeHtml(String(value))}">
  </div>`;
}

async function saveWizard() {
  const body = {
    repo: {
      url: $('repo-url').value.trim(),
      branch: $('repo-branch').value.trim() || 'main',
      poll_interval_s: intVal('repo-poll', 60),
      use_tag: true,
    },
    web: {
      bind: $('web-bind').value.trim() || '0.0.0.0',
      port: intVal('web-port', 9100),
      auth: { enabled: true, user: $('web-user').value.trim() || 'admin' },
      password: $('web-pass').value,
    },
    comp_params: {
      relay: { port: intVal('relay-port', 58080) },
      http: {
        listen: $('http-listen').value.trim() || '0.0.0.0:9001',
        relay_base: $('http-relay').value.trim() || 'ws://127.0.0.1:58080',
        result_public_host: $('http-pubhost').value.trim(),
        result_threshold_entries: intVal('http-ent', 50),
        result_threshold_bytes: intVal('http-bytes', 4096),
      },
      feishu: {
        http_host: $('fs-host').value.trim() || '0.0.0.0',
        http_port: intVal('fs-port', 8081),
      },
    },
    users: $('wiz-users').value.split('\n').map((s) => s.trim()).filter(Boolean),
    feishu_notify: {
      enabled: true,
      app_id: $('nt-appid').value.trim(),
      app_secret: $('nt-secret').value.trim(),
      receive_id: $('nt-recv').value.trim(),
      receive_id_type: $('nt-type').value.trim() || 'open_id',
    },
  };
  const r = await call('POST', '/api/wizard', body);
  if (!r.ok) return toast(r.error || '保存失败', 'err');
  $('wiz-hint').textContent = '已保存，配置文件已生成到 conf/';
  toast('配置已保存并生成组件配置文件', 'ok');
  loadConfig();
}

function intVal(id, dflt) {
  const v = parseInt($(id).value, 10);
  return isNaN(v) ? dflt : v;
}

// ══════════ 设置（等同向导的 OTA 自身部分） ══════════

async function saveSettings() {
  await saveWizard();
}

async function restartSelf() {
  if (!confirm('确认保存并重启部署管理器？\n\n页面会短暂失联，约 3 秒后自动恢复。')) return;
  await saveWizard();
  await call('POST', '/api/restart_self', {});
  toast('正在重启，3 秒后请刷新页面', 'ok');
  setTimeout(() => location.reload(), 5000);
}

async function testNotify() {
  toast('正在发送…');
  const r = await call('POST', '/api/test_notify', {});
  const hint = $('notify-hint');
  hint.textContent = r.ok ? (r.data.detail || '已发送') : (r.error || '失败');
  toast(r.ok ? '通知已发送' : (r.error || '发送失败'), r.ok ? 'ok' : 'err');
}

// ══════════ 日志 ══════════

async function loadLog() {
  const name = $('log-sel').value;
  const lines = parseInt($('log-lines').value, 10);
  const r = await call('GET', `/api/logs?name=${name}&lines=${lines}`);
  if (!r.ok) { $('log-text').textContent = r.error || '读取失败'; return; }
  const d = r.data;
  const rot = (d.rotated || []).length;
  $('log-info').textContent = d.exists
    ? `${d.path} — ${fmtSize(d.size)}${rot ? `，另有 ${rot} 个轮转备份` : ''}`
    : `日志文件尚未生成：${d.path}`;
  $('log-text').textContent = (d.lines || []).join('\n') || '(空)';
  $('log-text').scrollTop = $('log-text').scrollHeight;
}

async function clearLog() {
  const name = $('log-sel').value;
  if (!confirm(`确认清空 ${name} 日志？`)) return;
  const r = await call('POST', '/api/logs/clear', { name });
  if (!r.ok) return toast(r.error || '清空失败', 'err');
  toast('已清空', 'ok');
  loadLog();
}

function autoRefresh() {
  clearInterval(_autoTimer);
  _autoTimer = setInterval(() => {
    if ($('tab-logs').classList.contains('active') && $('log-auto').checked) loadLog();
    if ($('tab-overview').classList.contains('active')) refreshStatus();
  }, 3000);
}

// ══════════ 工具 ══════════

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function fmtSize(n) {
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1024 / 1024).toFixed(2) + ' MB';
}

// ══════════ 启动 ══════════

refreshStatus();
loadWizard();
autoRefresh();
