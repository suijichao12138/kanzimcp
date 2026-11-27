# -*- coding: utf-8 -*-
"""HTML 报告生成：单文件自包含，双击即看。

产出两份报告：
  report.html     问题查看器（按工具/级别/文件/规则筛选 + 源码上下文）
  coverage.html   规范覆盖对照表（可选，需提供规范条目）
"""
from __future__ import annotations

import html
import json
import os
import time
from pathlib import Path


def _esc(s):
    return html.escape("" if s is None else str(s))


def _read_sources(src: Path, max_mb: float = 30.0) -> dict:
    """读取源码，供报告里展示上下文。

    max_mb：内嵌源码总大小上限。超过则返回空字典，报告仍能正常显示问题列表，
    只是详情区会提示"源码未内嵌，请在 IDE 打开 xxx:行号"。
    这样避免大工程生成几百 MB 的 HTML（在常驻服务里尤其危险）。
    """
    out = {}
    exts = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")
    budget = int(max_mb * 1024 * 1024)
    used = 0
    for p in sorted(Path(src).rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if used + size > budget:
            return {}                      # 超限就整体不内嵌，避免半截数据
        try:
            out[p.relative_to(src).as_posix()] = \
                p.read_text(encoding="utf-8", errors="replace").splitlines()
            used += size
        except OSError:
            pass
    return out


def _json_for_script(obj) -> str:
    """把对象序列化成可安全嵌入 <script> 的 JSON。

    必须把 "</" 转成 "<\\/"：否则源码里出现 "</script>"（比如注释中写了
    HTML 示例）会提前闭合 script 标签，导致报告白屏。
    这是 JSON 标准允许的转义，解析后语义不变。
    """
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


SEV_ORDER = {
    "error": 0, "A": 0,
    "warning": 1, "L1": 1,
    "L2": 2, "high": 2,
    "performance": 3, "L4": 3,
    "style": 4,
    "portability": 5,
    "note": 6,
}

TOOL_COLORS = {
    "cppcheck": "#0ea5e9",
    "flawfinder": "#ef4444",
    "lizard": "#8b5cf6",
    "clang-tidy": "#10b981",
    "clang-format": "#f59e0b",
    "自定义规则": "#6366f1",
}


def build_report(src: Path, items: list, out_html: Path,
                 title="静态扫描报告", subtitle="", stats=None,
                 embed_sources=True, max_embed_mb=30.0) -> Path:
    """生成问题查看器 HTML。

    embed_sources=False 或源码总量超过 max_embed_mb 时不内嵌源码，
    报告体积会小很多，详情区改为提示到 IDE 查看。
    """
    sources = _read_sources(src, max_embed_mb) if embed_sources else {}

    # 统一字段，补默认值
    norm = []
    for x in items:
        norm.append({
            "file": x.get("file", ""),
            "line": int(x.get("line") or 0),
            "col": int(x.get("col") or 0),
            "sev": x.get("sev", "warning"),
            "tool": x.get("tool", ""),
            "check": x.get("check", ""),
            "msg": x.get("msg", ""),
            "cwe": x.get("cwe", ""),
            "spec": x.get("spec", ""),
        })

    payload = {
        "items": norm,
        "sources": sources,
        "title": title,
        "subtitle": subtitle,
        "stats": stats or {},
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "toolColors": TOOL_COLORS,
    }
    html_text = (_REPORT_TPL
                 .replace("__TITLE__", _esc(title))
                 .replace("__DATA__", _json_for_script(payload)))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_text, encoding="utf-8", newline="\n")
    return out_html


def build_coverage(items_spec: list, out_html: Path,
                   spec_total=0, title="规范覆盖对照表") -> Path:
    """生成规范覆盖对照表。items_spec 为 [{no, cat, level, text, grade,
    tool, note, hit}] 结构。"""
    payload = {
        "rules": items_spec,
        "total": spec_total or len(items_spec),
        "title": title,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    html_text = (_COVERAGE_TPL
                 .replace("__TITLE__", _esc(title))
                 .replace("__DATA__", _json_for_script(payload)))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_text, encoding="utf-8", newline="\n")
    return out_html


# ============================================================ 模板

_REPORT_TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
       background:#f5f6f8;color:#1f2328;font-size:13px}
  header{background:#fff;border-bottom:1px solid #d8dce3;padding:14px 20px;
         position:sticky;top:0;z-index:50;box-shadow:0 1px 3px rgba(0,0,0,.04)}
  h1{margin:0 0 3px;font-size:17px;font-weight:600}
  .sub{color:#6b7280;font-size:12px;margin-bottom:10px}
  .stats{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}
  .stat{background:#f8f9fb;border:1px solid #e3e6eb;border-radius:6px;
        padding:5px 11px;cursor:pointer;display:flex;align-items:center;gap:6px;
        user-select:none;transition:.12s}
  .stat:hover{border-color:#b9c0cc}
  .stat.active{border-color:#2563eb;background:#eff4ff}
  .stat b{font-size:15px;font-variant-numeric:tabular-nums}
  .stat span{color:#6b7280;font-size:12px}
  .bar{display:flex;gap:7px;flex-wrap:wrap;align-items:center}
  input,select{border:1px solid #d0d5dd;border-radius:5px;padding:5px 9px;
    font-size:13px;font-family:inherit;background:#fff;color:inherit;outline:none}
  input:focus,select:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1)}
  input{min-width:230px}
  .btn{border:1px solid #d0d5dd;background:#fff;border-radius:5px;padding:5px 11px;
       cursor:pointer;font-size:13px;font-family:inherit;color:inherit}
  .btn:hover{background:#f3f4f6}
  .sp{flex:1}
  main{display:flex;height:calc(100vh - 158px)}
  .list{flex:1;overflow:auto;background:#fff;border-right:1px solid #d8dce3}
  table{border-collapse:collapse;width:100%}
  thead th{background:#f8f9fb;position:sticky;top:0;z-index:10;text-align:left;
    padding:8px 9px;font-size:12px;font-weight:600;border-bottom:1px solid #d8dce3;
    white-space:nowrap;cursor:pointer;user-select:none;color:#374151}
  thead th:hover{background:#eef1f5}
  tbody tr{border-bottom:1px solid #f0f2f5;cursor:pointer}
  tbody tr:hover{background:#f7f9fc}
  tbody tr.sel{background:#e8f0fe!important}
  td{padding:6px 9px;vertical-align:top}
  .loc{font-family:Consolas,monospace;font-size:12px;white-space:nowrap}
  .loc b{color:#2563eb}
  .msg{color:#374151;max-width:560px}
  .ck{font-family:Consolas,monospace;font-size:11.5px;color:#6b7280;white-space:nowrap}
  .tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap}
  .t-error{background:#fee2e2;color:#b91c1c}
  .t-warning{background:#ffedd5;color:#c2410c}
  .t-style{background:#e0e7ff;color:#3730a3}
  .t-performance{background:#dbeafe;color:#1d4ed8}
  .t-portability{background:#f3e8ff;color:#7e22ce}
  .t-note{background:#f1f5f9;color:#64748b}
  .t-L1{background:#fee2e2;color:#b91c1c}
  .t-L2{background:#ffedd5;color:#c2410c}
  .t-L4{background:#fef9c3;color:#a16207}
  .t-A{background:#fee2e2;color:#b91c1c}
  .tt{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10.5px;
      color:#fff;white-space:nowrap}
  .detail{width:620px;min-width:360px;overflow:auto;background:#fbfcfd;padding:15px 17px}
  .detail h2{font-size:14px;margin:0 0 3px}
  .detail .s2{color:#6b7280;font-size:12px;margin-bottom:13px}
  .kv{display:grid;grid-template-columns:80px 1fr;gap:5px 10px;margin-bottom:14px}
  .kv dt{color:#6b7280;font-size:12px}
  .kv dd{margin:0;font-size:12.5px;word-break:break-word}
  code.i{background:#eef1f5;padding:1px 5px;border-radius:3px;
         font-family:Consolas,monospace;font-size:12px}
  .cb{background:#fff;border:1px solid #e3e6eb;border-radius:6px;overflow:auto;max-height:430px}
  .cb table{width:auto;min-width:100%}
  .cb td{padding:0 9px;border:none;vertical-align:top}
  .cb tr{border:none}
  .cb .ln{color:#9ca3af;text-align:right;user-select:none;width:1%;
          font-family:Consolas,monospace;font-size:12px;border-right:1px solid #f0f2f5}
  .cb .cd{font-family:Consolas,monospace;font-size:12px;white-space:pre}
  .cb tr.hit{background:#fff7d6}
  .cb tr.hit .ln{color:#b45309;font-weight:700;background:#fef3c7}
  .empty{color:#9ca3af;text-align:center;padding:50px 20px}
  .box{background:#fffbeb;border:1px solid #fde68a;border-radius:6px;
       padding:9px 11px;font-size:12px;color:#92400e;margin-bottom:12px;line-height:1.6}
  .hint{color:#9ca3af;font-size:12px;margin-top:7px}
</style>
</head>
<body>
<header>
  <h1 id="t"></h1>
  <div class="sub" id="st"></div>
  <div class="stats" id="stats"></div>
  <div class="bar">
    <input type="text" id="q" placeholder="搜索 文件 / 规则 / 描述 / CWE…">
    <select id="fTool"><option value="">全部工具</option></select>
    <select id="fSev"><option value="">全部级别</option></select>
    <select id="fFile"><option value="">全部文件</option></select>
    <select id="fSpec"><option value="">全部规范条目</option></select>
    <div class="sp"></div>
    <button class="btn" id="reset">重置</button>
    <button class="btn" id="csv">导出CSV</button>
  </div>
</header>
<main>
  <div class="list">
    <table><thead><tr>
      <th data-k="tool">工具</th><th data-k="sev">级别</th>
      <th data-k="file">位置</th><th data-k="check">规则</th>
      <th data-k="msg">描述</th><th data-k="spec">规范</th>
    </tr></thead><tbody id="tb"></tbody></table>
    <div id="none" class="empty" style="display:none">没有匹配的条目</div>
  </div>
  <div class="detail" id="detail">
    <div class="empty">← 点击左侧任一条查看详情与源码</div>
  </div>
</main>
<script>
const D = __DATA__;
const ITEMS = D.items, SRC = D.sources;
document.getElementById('t').textContent = D.title;
document.getElementById('st').textContent =
  (D.subtitle ? D.subtitle + ' · ' : '') + '生成于 ' + D.generated +
  ' · 共 ' + ITEMS.length + ' 条';

const SEVORD = {error:0,A:0,warning:1,L1:1,L2:2,high:2,performance:3,L4:3,style:4,portability:5,note:6};
const TOOLS = [...new Set(ITEMS.map(x=>x.tool).filter(Boolean))].sort();
let stat='', tool='', sev='', file='', spec='', q='';

/* 顶部统计 */
const byTool = {};
TOOLS.forEach(t=>byTool[t]=ITEMS.filter(x=>x.tool===t).length);
const defs = [{k:'',n:'全部',f:()=>true},
  {k:'err',n:'错误',f:x=>x.sev==='error'||x.sev==='A'},
  {k:'warn',n:'警告',f:x=>x.sev==='warning'||x.sev==='L1'},
  ...TOOLS.map(t=>({k:'t:'+t,n:t,f:x=>x.tool===t}))];
function renderStats(){
  const b=document.getElementById('stats'); b.innerHTML='';
  defs.forEach(d=>{
    const n=ITEMS.filter(d.f).length;
    const e=document.createElement('div');
    e.className='stat'+(stat===d.k?' active':'');
    e.innerHTML='<b>'+n+'</b><span>'+d.n+'</span>';
    e.onclick=()=>{stat=d.k;renderStats();render();};
    b.appendChild(e);
  });
}

/* 下拉初始化 */
(function(){
  const sevs=[...new Set(ITEMS.map(x=>x.sev))].sort((a,b)=>(SEVORD[a]??9)-(SEVORD[b]??9));
  const files=[...new Set(ITEMS.map(x=>x.file))].sort();
  const specs=[...new Set(ITEMS.map(x=>x.spec).filter(Boolean))].sort();
  const add=(id,arr,lab)=>{
    const s=document.getElementById(id);
    arr.forEach(v=>{const o=document.createElement('option');o.value=v;
      o.textContent=lab?lab(v):v;s.appendChild(o);});
  };
  add('fTool',TOOLS);
  add('fSev',sevs);
  add('fFile',files,v=>v.split('/').pop()+'  ('+v.split('/')[0]+')');
  if(specs.length) add('fSpec',specs); else document.getElementById('fSpec').style.display='none';
})();

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

let list=[], sortK='sev', asc=true;
function apply(){
  list = ITEMS.filter(x=>{
    if(stat==='err' && !(x.sev==='error'||x.sev==='A')) return false;
    if(stat==='warn' && !(x.sev==='warning'||x.sev==='L1')) return false;
    if(stat.startsWith('t:') && x.tool!==stat.slice(2)) return false;
    if(tool && x.tool!==tool) return false;
    if(sev && x.sev!==sev) return false;
    if(file && x.file!==file) return false;
    if(spec && x.spec!==spec) return false;
    if(q){const h=(x.file+' '+x.check+' '+x.msg+' '+x.cwe+' '+x.spec).toLowerCase();
          if(!h.includes(q)) return false;}
    return true;
  });
  list.sort((a,b)=>{
    let va,vb;
    if(sortK==='sev'){va=SEVORD[a.sev]??9;vb=SEVORD[b.sev]??9;}
    else if(sortK==='line'){va=a.line;vb=b.line;}
    else {va=String(a[sortK]||'');vb=String(b[sortK]||'');}
    if(va<vb) return asc?-1:1;
    if(va>vb) return asc?1:-1;
    return a.file===b.file?a.line-b.line:a.file.localeCompare(b.file);
  });
}
function render(){
  apply();
  const tb=document.getElementById('tb'); tb.innerHTML='';
  const f=document.createDocumentFragment();
  list.forEach(x=>{
    const tr=document.createElement('tr');
    const color = D.toolColors[x.tool] || '#94a3b8';
    tr.innerHTML =
      '<td><span class="tt" style="background:'+color+'">'+esc(x.tool)+'</span></td>'+
      '<td><span class="tag t-'+esc(x.sev)+'">'+esc(x.sev)+'</span></td>'+
      '<td class="loc">'+esc(x.file)+' : <b>'+x.line+'</b></td>'+
      '<td class="ck">'+esc(x.check)+'</td>'+
      '<td class="msg">'+esc(x.msg)+'</td>'+
      '<td class="ck">'+esc(x.spec||'—')+'</td>';
    tr.onclick=()=>{
      tb.querySelectorAll('tr.sel').forEach(e=>e.classList.remove('sel'));
      tr.classList.add('sel'); detail(x);
    };
    f.appendChild(tr);
  });
  tb.appendChild(f);
  document.getElementById('none').style.display = list.length?'none':'block';
  const first=tb.querySelector('tr');
  if(first) first.click();
  else document.getElementById('detail').innerHTML='<div class="empty">没有匹配的条目</div>';
}

function detail(x){
  const L=SRC[x.file];
  let h='<h2>'+esc(x.check)+'</h2>'+
        '<div class="s2">'+esc(x.tool)+' · '+esc(x.file)+' 第 '+x.line+' 行</div>';
  if(x.sev==='error'||x.sev==='A')
    h+='<div class="box"><b>该条为确定性缺陷</b>，建议优先修复。</div>';
  h+='<dl class="kv">';
  h+='<dt>级别</dt><dd><span class="tag t-'+esc(x.sev)+'">'+esc(x.sev)+'</span></dd>';
  h+='<dt>位置</dt><dd><code class="i">'+esc(x.file)+':'+x.line+
     (x.col?':'+x.col:'')+'</code></dd>';
  h+='<dt>规则</dt><dd><code class="i">'+esc(x.check)+'</code></dd>';
  if(x.cwe) h+='<dt>CWE</dt><dd>'+esc(x.cwe)+'</dd>';
  if(x.spec) h+='<dt>规范条款</dt><dd><code class="i">'+esc(x.spec)+'</code></dd>';
  h+='<dt>描述</dt><dd>'+esc(x.msg)+'</dd></dl>';
  if(L&&L.length){
    const a=Math.max(1,x.line-6), b=Math.min(L.length,x.line+6);
    h+='<div style="font-size:12px;color:#6b7280;margin-bottom:5px">源码上下文</div><div class="cb"><table>';
    for(let i=a;i<=b;i++)
      h+='<tr class="'+(i===x.line?'hit':'')+'"><td class="ln">'+i+
         '</td><td class="cd">'+esc(L[i-1])+'</td></tr>';
    h+='</table></div><div class="hint">共 '+L.length+' 行 · 显示 '+a+'–'+b+'</div>';
  }else{
    h+='<div class="box">该文件源码未内嵌，请直接在 IDE 打开 <code class="i">'+
       esc(x.file)+':'+x.line+'</code></div>';
  }
  const d=document.getElementById('detail');
  d.innerHTML=h; d.scrollTop=0;
}

document.getElementById('q').oninput=e=>{q=e.target.value.trim().toLowerCase();render();};
['fTool','fSev','fFile','fSpec'].forEach((id,i)=>{
  const key=['tool','sev','file','spec'][i];
  document.getElementById(id).onchange=e=>{
    if(key==='tool')tool=e.target.value;
    if(key==='sev')sev=e.target.value;
    if(key==='file')file=e.target.value;
    if(key==='spec')spec=e.target.value;
    render();
  };
});
document.getElementById('reset').onclick=()=>{
  stat='';tool='';sev='';file='';spec='';q='';
  document.getElementById('q').value='';
  ['fTool','fSev','fFile','fSpec'].forEach(id=>document.getElementById(id).value='');
  renderStats();render();
};
document.querySelectorAll('thead th').forEach(th=>{
  th.onclick=()=>{const k=th.dataset.k;
    if(k==='line')return;
    if(sortK===k)asc=!asc;else{sortK=k;asc=true;}
    render();};
});
document.getElementById('csv').onclick=()=>{
  const head=['工具','级别','文件','行号','规则','描述','CWE','规范'];
  const rows=list.map(x=>[x.tool,x.sev,x.file,x.line,x.check,x.msg,x.cwe,x.spec]);
  const csv=[head,...rows].map(r=>r.map(v=>{
    const s=String(v==null?'':v);
    return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
  }).join(',')).join('\r\n');
  const b=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(b);a.download='scan_result.csv';a.click();
};
renderStats();render();
</script>
</body>
</html>
"""

_COVERAGE_TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
       background:#f5f6f8;color:#1f2328;font-size:13px}
  header{background:#fff;border-bottom:1px solid #d8dce3;padding:14px 20px;
         position:sticky;top:0;z-index:50}
  h1{margin:0 0 8px;font-size:17px}
  .lead{background:#fffbeb;border:1px solid #fde68a;border-radius:6px;
        padding:10px 12px;font-size:12.5px;line-height:1.75;margin-bottom:11px}
  .stats{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:11px}
  .stat{background:#f8f9fb;border:1px solid #e3e6eb;border-radius:6px;
        padding:5px 11px;cursor:pointer;display:flex;gap:6px;align-items:center;
        user-select:none}
  .stat:hover{border-color:#b9c0cc}
  .stat.active{border-color:#2563eb;background:#eff4ff}
  .stat b{font-size:15px}
  .stat span{color:#6b7280;font-size:12px}
  .bar{display:flex;gap:7px;flex-wrap:wrap;align-items:center}
  input,select{border:1px solid #d0d5dd;border-radius:5px;padding:5px 9px;
    font-size:13px;font-family:inherit;background:#fff;color:inherit;outline:none}
  input{min-width:240px}
  .btn{border:1px solid #d0d5dd;background:#fff;border-radius:5px;padding:5px 11px;
       cursor:pointer;font-size:13px;font-family:inherit;color:inherit}
  .btn:hover{background:#f3f4f6}
  .sp{flex:1}
  table{border-collapse:collapse;width:100%;background:#fff}
  thead th{background:#f8f9fb;position:sticky;top:148px;z-index:10;text-align:left;
    padding:8px 9px;font-size:12px;border-bottom:1px solid #d8dce3;white-space:nowrap}
  tbody tr{border-bottom:1px solid #f0f2f5}
  tbody tr:hover{background:#f7f9fc}
  td{padding:6px 9px;vertical-align:top;font-size:12.5px}
  .no{font-family:Consolas,monospace;font-weight:600;white-space:nowrap}
  .g{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap}
  .gA{background:#dcfce7;color:#15803d}
  .gB{background:#fef9c3;color:#a16207}
  .gC{background:#fee2e2;color:#b91c1c}
  .gD{background:#e0e7ff;color:#3730a3}
  .lv{font-size:11px;color:#6b7280;white-space:nowrap}
  .lv.must{color:#b91c1c;font-weight:600}
  .txt{color:#374151;max-width:440px}
  .tk{font-family:Consolas,monospace;font-size:11.5px;color:#6b7280;white-space:nowrap}
  .hit{font-weight:600;color:#b45309;font-variant-numeric:tabular-nums}
  .hit0{color:#cbd5e1}
</style>
</head>
<body>
<header>
  <h1 id="t"></h1>
  <div class="lead" id="lead"></div>
  <div class="stats" id="stats"></div>
  <div class="bar">
    <input type="text" id="q" placeholder="搜索 编号 / 分类 / 条款原文 / 说明…">
    <select id="fTool"><option value="">全部工具</option></select>
    <select id="fLv"><option value="">全部级别</option>
      <option value="必须">必须</option><option value="建议">建议</option>
    </select>
    <div class="sp"></div>
    <button class="btn" id="reset">重置</button>
    <button class="btn" id="csv">导出CSV</button>
  </div>
</header>
<table><thead><tr>
  <th>编号</th><th>分类</th><th>级别</th><th>条款原文</th>
  <th>覆盖</th><th>检测工具</th><th>说明</th><th>命中</th>
</tr></thead><tbody id="tb"></tbody></table>
<script>
const D = __DATA__, R = D.rules;
const GN = {A:'可直接定位',B:'可检出待对条款',C:'需人工判断'};
document.getElementById('t').textContent = D.title + '（' + D.total + ' 条）';
let g='',tool='',lv='',q='';

const count = k => R.filter(r=>r.grade===k).length;
const pct = k => (R.length ? Math.round(100*count(k)/R.length) : 0);
document.getElementById('lead').innerHTML =
  '规范共 <b>'+D.total+'</b> 条。按本工具当前的实际能力：'+
  '<b>'+count('A')+'</b> 条（'+pct('A')+'%）报告里可直接命中并标出条款号；'+
  '<b>'+count('B')+'</b> 条（'+pct('B')+'%）工具能检出问题，但没有逐条映射到条款号，需人工对照；'+
  '<b>'+count('C')+'</b> 条（'+pct('C')+'%）属于语义、设计意图或主观判断，'+
  '<b>原理上无法自动化</b>，只能靠代码评审把关。'+
  '<br><span style="color:#6b7280">说明：A 级条款由 cppcheck / clang-tidy 规则映射表、'+
  '自研规则检查器、clang-format 共同覆盖；B 级指 clang-format 与 clang-tidy 已配置相应检查项，'+
  '但报告未标注条款号。</span>';

const defs=[{k:'',n:'全部',f:()=>true},
  {k:'A',n:'A 可直接定位',f:r=>r.grade==='A'},
  {k:'B',n:'B 可检出待对',f:r=>r.grade==='B'},
  {k:'C',n:'C 需人工判断',f:r=>r.grade==='C'},
  {k:'hit',n:'本次有命中',f:r=>r.hit>0}];
function rs(){
  const b=document.getElementById('stats');b.innerHTML='';
  defs.forEach(d=>{
    const e=document.createElement('div');
    e.className='stat'+(g===d.k?' active':'');
    e.innerHTML='<b>'+R.filter(d.f).length+'</b><span>'+d.n+'</span>';
    e.onclick=()=>{g=d.k;rs();rr();};
    b.appendChild(e);
  });
}
(function(){
  const ts=[...new Set(R.map(r=>r.tool).filter(Boolean))].sort();
  const s=document.getElementById('fTool');
  ts.forEach(t=>{const o=document.createElement('option');o.value=t;
    o.textContent=t;s.appendChild(o);});
})();
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function filt(){
  return R.filter(r=>{
    if(g==='hit'&&!(r.hit>0))return false;
    if(g&&g!=='hit'&&r.grade!==g)return false;
    if(tool&&r.tool!==tool)return false;
    if(lv&&r.level!==lv)return false;
    if(q){const h=(r.no+' '+r.cat+' '+r.text+' '+r.note+' '+r.tool).toLowerCase();
          if(!h.includes(q))return false;}
    return true;
  });
}
function rr(){
  const tb=document.getElementById('tb');tb.innerHTML='';
  const f=document.createDocumentFragment();
  filt().forEach(r=>{
    const tr=document.createElement('tr');
    tr.innerHTML='<td class="no">'+esc(r.no)+'</td>'+
      '<td class="lv">'+esc(r.cat)+'</td>'+
      '<td class="lv'+(r.level==='必须'?' must':'')+'">'+esc(r.level)+'</td>'+
      '<td class="txt">'+esc(r.text)+'</td>'+
      '<td><span class="g g'+r.grade+'">'+GN[r.grade]+'</span></td>'+
      '<td class="tk">'+esc(r.tool||'—')+'</td>'+
      '<td class="txt">'+esc(r.note)+'</td>'+
      '<td class="'+(r.hit>0?'hit':'hit0')+'">'+(r.hit>0?r.hit:'—')+'</td>';
    f.appendChild(tr);
  });
  tb.appendChild(f);
}
document.getElementById('q').oninput=e=>{q=e.target.value.trim().toLowerCase();rr();};
document.getElementById('fTool').onchange=e=>{tool=e.target.value;rr();};
document.getElementById('fLv').onchange=e=>{lv=e.target.value;rr();};
document.getElementById('reset').onclick=()=>{
  g='';tool='';lv='';q='';
  document.getElementById('q').value='';
  document.getElementById('fTool').value='';
  document.getElementById('fLv').value='';
  rs();rr();
};
document.getElementById('csv').onclick=()=>{
  const head=['编号','分类','级别','条款原文','覆盖','工具','说明','命中'];
  const rows=filt().map(r=>[r.no,r.cat,r.level,r.text,GN[r.grade],r.tool,r.note,r.hit]);
  const csv=[head,...rows].map(x=>x.map(v=>{
    const s=String(v==null?'':v);
    return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
  }).join(',')).join('\r\n');
  const b=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(b);a.download='coverage.csv';a.click();
};
rs();rr();
</script>
</body>
</html>
"""
