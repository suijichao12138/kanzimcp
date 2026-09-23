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


// ══════════ 弹窗（模态框）══════════

let _modalOnOk = null;

/** 打开弹窗。okText 为空则不显示确认按钮。 */
function openModal({ title, html, okText, cancelText, onOk }) {
  $('modal-title').textContent = title || '提示';
  $('modal-body').innerHTML = html || '';
  const okBtn = $('modal-ok');
  okBtn.textContent = okText || '确定';
  okBtn.classList.toggle('hidden', !okText);
  $('modal-cancel').textContent = cancelText || '取消';
  _modalOnOk = onOk || null;
  $('modal-mask').classList.remove('hidden');
}

function closeModal() {
  $('modal-mask').classList.add('hidden');
  _modalOnOk = null;
}

/** 简短提示弹窗（只有「知道了」）。 */
function alertModal(title, html) {
  openModal({ title, html, okText: '知道了', cancelText: '关闭', onOk: null });
}

// ══════════ 标签切换 ══════════

/** 切到某个标签页（nav 点击 / 弹窗跳转共用）。 */
function goTab(name) {
  document.querySelectorAll('.tab').forEach((b) => {
    b.classList.toggle('active', b.dataset.tab === name);
  });
  document.querySelectorAll('.panel').forEach((p) => {
    p.classList.toggle('active', p.id === 'tab-' + name);
  });
  if (name === 'logs') loadLog();
  if (name === 'config' || name === 'settings') loadWizard();
  if (name === 'config') loadConfig();
  if (name === 'overview') refreshStatus();
  window.scrollTo(0, 0);
}

document.querySelectorAll('.tab').forEach((btn) => {
  btn.onclick = () => goTab(btn.dataset.tab);
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

  // 升级按钮状态：未部署过 / 已是最新 / 有任务在跑 → 置灰
  const upBtn = $('btn-upgrade');
  const tip = $('upg-target');
  const busy = !!d.task_running;
  let disabled = false;
  let why = '';
  if (!d.deployed) {
    disabled = true;
    why = '尚未部署过 —— 请先点「一键部署」完成首次部署';
  } else if (d.up_to_date) {
    disabled = true;
    why = `当前已是最新版本 ${d.local_tag}`;
  } else if (busy) {
    disabled = true;
    why = '有任务正在执行，请等它结束';
  } else if (!d.latest_tag) {
    disabled = true;
    why = '未取到远端版本 —— 先点「检查更新」';
  }
  if (upBtn) {
    upBtn.disabled = disabled;
    upBtn.classList.toggle('is-disabled', disabled);
  }
  if (tip) {
    tip.textContent = disabled ? why
      : `目标版本：${d.latest_tag}`;
  }

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
  const btn = $('btn-upgrade');
  if (btn && btn.disabled) return;              // 置灰时不该被点到
  if (!confirm('确认升级？\n\n这将重新拉取源码、编译三个组件并重启服务。\n期间服务会短暂中断，正在执行的任务会结束。\n\n确认继续？')) return;
  const r = await call('POST', '/api/upgrade', {});
  if (!r.ok) {
    // 后端兜底拦截：未部署过 / 已是最新
    toast(r.error || '启动升级失败', 'err');
    refreshStatus();
    return;
  }
  watchTask(r.data.id);
}

async function doDeploy() {
  // 不预查 /api/status（那会串行做组件探活，慢）：直接发部署请求，
  // 配置不合格时后端返回 409 + need_config，再弹窗引导去「配置」页。
  if (!confirm('确认一键部署？\n\n流程：拉源码 → 编译 → 生成配置 → 重启组件。\n期间服务会短暂中断。')) return;
  const r = await call('POST', '/api/deploy', {});
  if (!r.ok) {
    // 后端前置检查未通过 → 弹窗引导去配置页
    if (r.need_config) {
      showNeedConfigModal(r.reason || '', r.error || '');
      return;
    }
    return toast(r.error || '启动部署失败', 'err');
  }
  watchTask(r.data.id);
}

/** 「配置不全，先去配置页」弹窗。 */
function showNeedConfigModal(reason, detail) {
  const miss = /缺少配置文件/.test(reason)
    ? (reason.replace(/.*?：/, '') || '').split('、').filter(Boolean) : [];
  const lines = [];
  if (miss.length) {
    lines.push(`缺少配置文件：<b>${miss.map(escapeHtml).join('、')}</b>`);
  }
  if (/白名单/.test(reason)) {
    lines.push('<b>http 组件白名单为空</b>'
             + '<span class="muted">（白名单为空时 http 组件会拒绝启动，部署必然失败）</span>');
  }
  openModal({
    title: '还不能部署',
    html: '<p>请先把配置补全，再执行一键部署：</p>'
        + (lines.length ? '<ul>' + lines.map((t) => `<li>${t}</li>`).join('') + '</ul>'
                        : `<p>${escapeHtml(detail)}</p>`)
        + '<p class="muted">点「去配置」会跳到「配置」页，'
        + '填写并<b>保存</b>后回来再点部署。</p>',
    okText: '去配置',
    cancelText: '取消',
    onOk: () => goTab('config'),
  });
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
let _bots = [];
let _localIps = [];

async function loadWizard() {
  const r = await call('GET', '/api/wizard');
  if (!r.ok) return;
  _wiz = r.data;
  if (Array.isArray(r.data.local_ips) && r.data.local_ips.length) {
    _localIps = r.data.local_ips;
  }
  renderWizard();
  renderSettings();
  autoFillIps();
}

function renderWizard() {
  const w = _wiz || {};
  const cp = w.comp_params || {};
  const http = cp.http || {};
  const fs = cp.feishu || {};

  $('wiz-body').innerHTML = `
  <div class="wiz-group">
    <h3>① relay 中继</h3>
    ${field('监听端口', 'relay-port', (cp.relay || {}).port || 58080, '中继服务端口，各组件都连它。一般不用改。【relay 没有配置文件，只有这个端口】', false, 'number')}
  </div>

  <div class="wiz-group">
    <h3>② http 组件（MCP over HTTP）</h3>
    ${fieldGrid([
      {label: '监听地址', id: 'http-host', value: http.listen_host || '0.0.0.0'},
      {label: '端口', id: 'http-port', value: http.listen_port || 9001, type: 'number'},
    ], '监听地址填 0.0.0.0 才能让远程 Copilot 连进来；改成 127.0.0.1 则只能本机连。')}
    ${field('外置阈值(记录数)', 'http-ent', http.result_threshold_entries || 50, '返回结果超过这么多条就落盘成文件，只回 URL。', false, 'number')}
    ${field('外置阈值(字节)', 'http-bytes', http.result_threshold_bytes || 4096, '返回文本超过这么多字节就落盘。截图 base64 必然超，会被外置。', false, 'number')}
    <div class="field">
      <label>白名单用户</label>
      <div class="desc">允许使用 HTTP MCP 服务的用户名，一行一个。对应 relay 的通道名（如 suijichao）。保存到 conf/users.json，改它<b>不用重启</b>（热更新）。</div>
      <textarea id="wiz-users" style="min-height:90px">${escapeHtml((w.users || []).join('\n'))}</textarea>
    </div>
  </div>

  <div class="wiz-group">
    <h3>③ 飞书桥（多机器人）</h3>
    ${fieldGrid([
      {label: '文件服务监听 IP', id: 'fs-host', value: fs.http_host || '0.0.0.0'},
      {label: '文件服务端口', id: 'fs-port', value: fs.http_port || 8081, type: 'number'},
    ], '两个 bot 共用一个文件服务：0.0.0.0 = 所有网卡都监听（推荐），已自动填好本机 IP 作备选。')}
    <div class="bots-head">
      <span>机器人列表（每个 bot 一条独立中继通道）</span>
      <button class="btn small" id="add-bot-btn" type="button">+ 添加 Bot</button>
    </div>
    <div id="bots-list"></div>
    <p class="muted">通道名从「通道地址」最后一段自动取，可手改，但<b>必须唯一</b>（桥按名字路由文件）。</p>

    <div class="wiz-subgroup">
      <h4>inbox 自动清理（全局默认，各 bot 未填时继承这里）</h4>
      ${cleanupFields('gl', (fs.cleanup || {}), '')}
    </div>
  </div>

`;

  renderBots(fs.bots || []);
  autoFillIps();
  const addBtn = $('add-bot-btn');
  if (addBtn) addBtn.onclick = () => {
    _bots.push({ name: '', app_id: '', app_secret: '' });
    renderBots(_bots);
      autoFillIps();
  };
}

function field(label, id, value, desc, required, type) {
  const t = type || 'text';
  return `<div class="field">
    <label>${label}${required ? ' <span class="req">*</span>' : ''}</label>
    <div class="desc">${desc || ''}</div>
    <input type="${t}" id="${id}" value="${escapeHtml(String(value))}">
  </div>`;
}

/** 一行多列的纯字段（不带描述）—— 描述统一放在行上方，避免各列高低不齐。 */
function fieldGrid(cells, note) {
  const cols = cells.map((c) => `
    <div class="grid-cell">
      <label>${c.label}${c.required ? ' <span class="req">*</span>' : ''}</label>
      <input type="${c.type || 'text'}" id="${c.id}" value="${escapeHtml(String(c.value))}">
    </div>`).join('');
  return `<div class="grid-field">
    ${note ? `<div class="desc">${note}</div>` : ''}
    <div class="grid-cells" style="--cols:${cells.length}">${cols}</div>
  </div>`;
}

// ══════════ 本机 IP 自动获取 ══════════

/** 当前最该用的本机 IP：优先后端探测到的第一个。 */
function primaryIp() {
  return (_localIps && _localIps[0]) || '';
}

/** 输入框右侧的「本机」按钮：点一下填入本机 IP。 */
/** 把「填本机」按钮插到对应 input 的后面（字段是整块 div，按钮须进 div 内）。 */

/** 一键把所有能填 IP 的字段填成本机 IP。 */
function autoFillIps() {
  const ip = primaryIp();
  if (!ip) return;

  // 文件服务监听 IP（唯一还开放的 IP 字段）
  const fsHost = $('fs-host');
  if (fsHost && !(fsHost.value || '').trim()) fsHost.value = ip;
}

// ── 飞书 bot 卡片列表 ──


function renderBots(bots) {
  _bots = (bots || []).map((b) => Object.assign({}, b, { cleanup: b.cleanup || {} }));
  const box = $('bots-list');
  if (!box) return;
  if (!_bots.length) {
    box.innerHTML = '<p class="muted">暂无机器人。点「+ 添加 Bot」新增；不需要飞书桥可以留空。</p>';
    return;
  }
  box.innerHTML = _bots.map((b, i) => `
    <div class="bot-card" data-i="${i}">
      <div class="bot-head" data-toggle="${i}">
        <span class="bot-title">
          <span class="bot-caret">&#9656;</span>
          ${escapeHtml(b.name || '（未命名 Bot）')}
        </span>
        <span class="bot-actions">
          <button class="btn small danger" type="button" data-del="${i}">删除</button>
        </span>
      </div>
      <div class="bot-body hidden">
        ${field('Bot 名称', 'bot-name-' + i, b.name || '', '同时是中继通道名，<b>必须唯一</b>。通道地址由它自动拼（ws://本机IP:中继端口/名称），不用手填。', true)}
        ${field('App ID', 'bot-appid-' + i, b.app_id || '', '该机器人应用的 App ID（cli_ 开头）。', true)}
        ${field('App Secret', 'bot-secret-' + i, b.app_secret || '', '该机器人应用的 App Secret。掩码=保留原值，新增 bot 必须真填。', true, 'password')}
      </div>
    </div>`).join('');

  // 折叠/展开：点标题栏切换；默认折叠
  Array.prototype.forEach.call(box.querySelectorAll('[data-toggle]'), (el) => {
    el.onclick = (ev) => {
      if (ev.target.closest('[data-del]')) return;   // 点删除不触发折叠
      const card = el.closest('.bot-card');
      if (!card) return;
      const body = card.querySelector('.bot-body');
      const opened = card.classList.toggle('open');
      if (body) body.classList.toggle('hidden', !opened);
    };
  });

  Array.prototype.forEach.call(box.querySelectorAll('[data-del]'), (el) => {
    el.onclick = () => {
      _bots.splice(parseInt(el.dataset.del, 10), 1);
      renderBots(_bots);
    };
  });
  // Bot 名称 → 卡片标题实时同步
  _bots.forEach((b, i) => {
    const nameEl = $('bot-name-' + i);
    if (nameEl) {
      nameEl.addEventListener('input', () => {
        nameEl.dataset.touched = '1';
        const card = nameEl.closest('.bot-card');
        const t = card && card.querySelector('.bot-title');
        if (t) {
          const caret = t.querySelector('.bot-caret');
          t.innerHTML = '';
          if (caret) t.appendChild(caret);
          t.appendChild(document.createTextNode(
            ' ' + (nameEl.value.trim() || '（未命名 Bot）')));
        }
      });
    }
  });
}

function cleanupFields(prefix, c, note) {
  c = c || {};
  // 四个字段一行，描述统一提到行上方 —— 各列 label/input 天然对齐，
  // 不会因为某个描述换行成两行而把输入框挤歪。
  return fieldGrid([
    {label: '启用', id: prefix + '-cl-enabled',
     value: c.enabled === true ? 'true' : (c.enabled === false ? 'false' : '')},
    {label: '保留天数', id: prefix + '-cl-age',
     value: c.max_age_days != null ? c.max_age_days : '', type: 'number'},
    {label: '保留数量', id: prefix + '-cl-files',
     value: c.max_files != null ? c.max_files : '', type: 'number'},
    {label: '扫描间隔(秒)', id: prefix + '-cl-interval',
     value: c.interval_s != null ? c.interval_s : '', type: 'number'},
  ], (note || '') + ' 启用填 true / false。三个数值都可留空 = 继承上一级；'
     + '保留天数按文件时间删，保留数量超出时删最旧，扫描间隔是多久扫一次。');
}

function collectCleanup(prefix) {
  const out = {};
  const enEl = $(prefix + '-cl-enabled');
  const en = enEl ? enEl.value.trim().toLowerCase() : '';
  if (en === 'true') out.enabled = true;
  else if (en === 'false') out.enabled = false;
  [['age', 'max_age_days'], ['files', 'max_files'], ['interval', 'interval_s']].forEach((pair) => {
    const el = $(prefix + '-cl-' + pair[0]);
    if (!el || !el.value.trim()) return;
    const n = parseInt(el.value, 10);
    if (!isNaN(n)) out[pair[1]] = n;
  });
  return out;
}

// ══════════ 设置页：部署管理器自身配置 ══════════

function renderSettings() {
  const w = _wiz || {};
  const repo = w.repo || {};
  const web = w.web || {};
  const fn = w.feishu_notify || {};
  const box = $('set-body');
  if (!box) return;

  box.innerHTML = `
  <div class="wiz-group">
    <h3>更新源（Gitee 仓库）</h3>
    ${field('仓库地址', 'repo-url', repo.url || '', '部署管理器从这里拉取源码并编译。填 Gitee 镜像地址。', true)}
    ${field('分支', 'repo-branch', repo.branch || 'main', '主分支名，一般为 main。')}
    ${field('检查间隔(秒)', 'repo-poll', repo.poll_interval_s || 60, '后台多久查一次远端版本。只做提示，不会自动升级。', false, 'number')}
  </div>

  <div class="wiz-group">
    <h3>管理页面</h3>
    ${field('监听地址', 'web-bind', web.bind || '0.0.0.0', '0.0.0.0 表示局域网内都可访问；改成 127.0.0.1 则只能本机访问。')}
    ${field('端口', 'web-port', web.port || 9100, '管理网页端口，注意避开 58080 / 9001 / 8081。', false, 'number')}
    ${field('访问用户名', 'web-user', (web.auth || {}).user || 'admin', '登录管理页面的用户名。')}
    ${field('访问密码', 'web-pass', '', '留空则不修改当前密码。首次配置建议设置。', false, 'password')}
  </div>

  <div class="wiz-group">
    <h3>飞书通知（部署管理器自己用）</h3>
    ${field('App ID', 'nt-appid', fn.app_id || '', '部署管理器发通知用的飞书应用 ID。')}
    ${field('App Secret', 'nt-secret', fn.app_secret || '', '已保存的密钥显示为掩码，不改就保留原值。', false, 'password')}
    ${field('接收人 ID', 'nt-recv', fn.receive_id || '', '接收通知的 open_id 或群 ID。')}
    ${field('ID 类型', 'nt-type', fn.receive_id_type || 'open_id', 'open_id / chat_id / user_id，一般用 open_id。')}
  </div>

  <p class="muted">改完点下方「保存设置」。改监听地址/端口或用户名密码后需要重启管理器才生效，可用「保存并重启管理器」。</p>`;
}

async function saveSettings() {
  const body = {
    repo: {
      url: ($('repo-url').value || '').trim(),
      branch: ($('repo-branch').value || '').trim() || 'main',
      poll_interval_s: intVal('repo-poll', 60),
      use_tag: true,
    },
    web: {
      bind: ($('web-bind').value || '').trim() || '0.0.0.0',
      port: intVal('web-port', 9100),
      auth: { enabled: true, user: ($('web-user').value || '').trim() || 'admin' },
      password: $('web-pass').value,
    },
    feishu_notify: {
      enabled: true,
      app_id: ($('nt-appid').value || '').trim(),
      app_secret: $('nt-secret').value.trim(),
      receive_id: ($('nt-recv').value || '').trim(),
      receive_id_type: ($('nt-type').value || '').trim() || 'open_id',
    },
  };
  const r = await call('POST', '/api/wizard', body);
  const hint = $('set-hint');
  if (!r.ok) {
    if (hint) hint.textContent = r.error || '保存失败';
    return toast(r.error || '保存失败', 'err');
  }
  if (hint) hint.textContent = '已保存到 deployer_config.json';
  toast('设置已保存', 'ok');
  await loadWizard();
}

async function saveWizard() {
  const body = {
    comp_params: {
      relay: { port: intVal('relay-port', 58080) },
      http: {
        listen_host: ($('http-host').value || '').trim() || '0.0.0.0',
        listen_port: intVal('http-port', 9001),

        result_threshold_entries: intVal('http-ent', 50),
        result_threshold_bytes: intVal('http-bytes', 4096),
      },
      feishu: {
        http_host: $('fs-host').value.trim() || '0.0.0.0',
        http_port: intVal('fs-port', 8081),
        cleanup: collectCleanup('gl'),
        bots: collectBots(),
      },
    },
    users: $('wiz-users').value.split('\n').map((s) => s.trim()).filter(Boolean),
  };
  const r = await call('POST', '/api/wizard', body);
  if (!r.ok) return toast(r.error || '保存失败', 'err');
  $('wiz-hint').textContent = '已保存，配置文件已生成到 conf/';
  toast('配置已保存并生成组件配置文件', 'ok');
  loadConfig();
}

function collectBots() {
  // 页面只收 3 项：名称 / App ID / App Secret
  // 通道地址由名称 + 本机 IP + 中继端口自动拼（手填极易写错 → 中继分通道不一致 →
  // 飞书报「没有可用的 Chat Worker」）
  const ip = primaryIp();
  const relayPort = intVal('relay-port', 58080);
  return _bots.map((b, i) => {
    const g = (id) => {
      const el = $(id);
      return el ? el.value.trim() : '';
    };
    const name = g('bot-name-' + i);
    return {
      name: name,
      app_id: g('bot-appid-' + i),
      app_secret: $('bot-secret-' + i) ? $('bot-secret-' + i).value : '',
      relay_url: name ? `ws://${ip}:${relayPort}/${name}` : '',
    };
  });
}

function intVal(id, dflt) {
  const v = parseInt($(id).value, 10);
  return isNaN(v) ? dflt : v;
}

// ══════════ 设置（等同向导的 OTA 自身部分） ══════════

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

// 弹窗事件绑定
(function bindModal() {
  const mask = $('modal-mask');
  if (!mask) return;
  $('modal-ok').onclick = () => {
    const fn = _modalOnOk;
    closeModal();
    if (typeof fn === 'function') fn();
  };
  $('modal-cancel').onclick = closeModal;
  mask.onclick = (e) => { if (e.target === mask) closeModal(); };
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !mask.classList.contains('hidden')) closeModal();
  });
})();
