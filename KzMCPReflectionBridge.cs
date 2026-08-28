using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using Rightware.Kanzi.Studio.PluginInterface;

namespace KzMCPChatPlugin
{
    /// <summary>
    /// Reflection 桥接层，通过 Kanzi Studio API 操作工程中的节点和属性。
    /// 全部使用 C# Reflection 动态调用，不依赖任何 Kanzi Studio 内部类型。
    /// </summary>
    public class KzMCPReflectionBridge
    {
        private readonly KanziStudio _studio;
        private object _project;
        private Type _projectType;
        private object _projectItem;
        private Type _projectItemType;
        private string _lastDefaultHow;   // 最近一次 set_DefaultText 的尝试结果（诊断用）

        // ====== V12 多工程支持：工程池 ======
        // 每个已打开工程按名字缓存其 Project/ProjectItem/类型，供 @proj:<name> 与 SelectProject 使用。
        // KanziStudio 本身只有 get_Project(当前Project)/get_Solution/get_PrimaryProject/get_ActiveProject；
        // 所有已打开工程的枚举在 Solution.get_Projects()（返回 IEnumerable<Project>），反编译确认（非脑补）。
        private class ProjectSlot
        {
            public object Project;
            public object ProjectItem;
            public Type ProjectType;
            public Type ProjectItemType;
            public string Name;
            public bool IsActive;
            public bool IsPrimary;
        }
        private readonly Dictionary<string, ProjectSlot> _projectPool = new Dictionary<string, ProjectSlot>(StringComparer.OrdinalIgnoreCase);
        private object _solutionCached;
        private string _selectedProjectName;   // SelectProject 选中的工程名；null=默认 ActiveProject

        // ====== 对象引用缓存 ======
        private readonly Dictionary<string, object> _objectStore = new Dictionary<string, object>();
        private readonly Dictionary<object, string> _objectToRefId = new Dictionary<object, string>();
        private long _nextRefId = 1;

        // 内部反射时置元：为 true 时所有 WrapResult 直接返回裸对象（不给 MCP 网络用，供插件内部直接拿真实对象）
        private bool _suppressWrap;

        /// <summary>根据 _suppressWrap 决定 wrap 还是返回裸对象；给 InvokeCore 内部所有 return WrapResult 用。</summary>
        private object MaybeWrap(object rawResult)
        {
            return _suppressWrap ? rawResult : WrapResult(rawResult);
        }

        /// <summary>内部用反射入口：返回【真实对象】（不 WrapResult），供插件内部直接拿对象用（如 LocalizationTable / LocaleLibrary）。
        /// 线程策略同 Invoke（默认切 UI 线程），只是不 wrap，避免 ref_id 绕路。</summary>
        public object InvokeRaw(string target, string method, object[] args)
        {
            bool old = _suppressWrap;
            _suppressWrap = true;
            try
            {
                return Invoke(target, method, args);
            }
            finally
            {
                _suppressWrap = old;
            }
        }

        /// <summary>调用方法并返回裸结果的【确切 CLR 类型全名】（不 WrapResult、不展开 IEnumerable）。
        /// 用于查明 Get("...") 等返回值的确切类型（如集合是具体 List<T>/Kanzi 集合还是数组），
        /// 从而知道 Set 该传什么类型的值。</summary>
        public string GetRawReturnType(string target, string method, object[] args)
        {
            object raw;
            bool old = _suppressWrap;
            _suppressWrap = true;
            try
            {
                raw = Invoke(target, method, args);
            }
            finally
            {
                _suppressWrap = old;
            }
            if (raw == null) return "<null>";
            var t = raw.GetType();
            return t.FullName + " (isEnumerable=" + (raw is System.Collections.IEnumerable) + ", isArray=" + t.IsArray + ", isList=" + (t.IsGenericType && t.GetGenericTypeDefinition() == typeof(List<>)) + ")";
        }

        /// <summary>调用方法并返回裸结果对象（不 WrapResult、不展开 IEnumerable），若为对象则 RegisterObject 拿到 @obj ref；
        /// 基础类型/字符串则原样返回。用于拿 DynamicClass 等被展开机制的【集合对象实例】ref，之后可 Set 或调其方法。
        /// 注意：不能切到非 UI 线程时由调用方决定；此处同 Invoke 默认 UI 线程策略不在本方法内处理。</summary>
        public object GetRawRef(string target, string method, object[] args)
        {
            object raw;
            bool old = _suppressWrap;
            _suppressWrap = true;
            try
            {
                raw = Invoke(target, method, args);
            }
            finally
            {
                _suppressWrap = old;
            }
            if (raw == null) return null;
            var t = raw.GetType();
            if (raw is string || raw is int || raw is long || raw is float
                || raw is double || raw is decimal || raw is bool)
                return raw;
            if (t.IsEnum)
                return raw.ToString();
            // 对象（含 IEnumerable 集合对象本身）→ 注册拿 ref
            return RegisterObject(raw);
        }

        // ====== 构造函数 ======
        public KzMCPReflectionBridge(KanziStudio studio)
        {
            _studio = studio ?? throw new ArgumentNullException(nameof(studio));
            _project = _studio.ActiveProject;
            _projectType = _project?.GetType();
            if (_project != null)
                CacheReflectionTypes();
            RefreshProjects();
        }

        // ====== 属性 ======
        public bool HasActiveProject => _studio.ActiveProject != null;

        public string GetProjectName()
        {
            try
            {
                var nameProp = _projectType?.GetProperty("Name");
                return nameProp?.GetValue(_project)?.ToString() ?? "(无工程)";
            }
            catch { return "(无工程)"; }
        }

        public bool HasProjectObject => _project != null;

        // ====== 生命周期管理 ======
        public void Refresh()
        {
            _project = _studio.ActiveProject;
            _projectType = _project?.GetType();
            if (_project != null)
                CacheReflectionTypes();
            // V12：刷新工程池；若之前 SelectProject 选中的工程仍存在，则维持该选中工程为当前上下文
            RefreshProjects();
            var prev = _selectedProjectName;
            _selectedProjectName = null;
            if (!string.IsNullOrEmpty(prev))
            {
                try { SelectProject(prev); } catch { /* SelectProject 内部已回退 ActiveProject */ }
            }
        }

        // ====== V12 多工程支持 ======

        /// <summary>V12 内部：拿 <c>KanziStudio</c> 的 <c>Solution</c> 对象（@studio.get_Solution）。
        /// 通过它才能枚举所有已打开工程（Solution.get_Projects）。</summary>
        private object GetSolution()
        {
            if (_solutionCached != null) return _solutionCached;
            object sol = null;
            try
            {
                var m = FindMethod(_studio.GetType(), "get_Solution", Type.EmptyTypes);
                if (m != null) sol = m.Invoke(_studio, null);
            }
            catch { }
            _solutionCached = sol;
            return sol;
        }

        /// <summary>V12：枚举所有已打开工程（Solution.get_Projects → IEnumerable&lt;Project&gt;），
        /// 填充 <c>_projectPool</c> 并把每个工程对象注册为 <c>@proj:&lt;工程名&gt;</c> 别名。
        /// 不切换当前上下文（不碰 ActiveProject）。</summary>
        public void RefreshProjects()
        {
            _projectPool.Clear();
            object sol = GetSolution();
            if (sol == null) return;

            object projects;
            try
            {
                var m = FindMethod(sol.GetType(), "get_Projects", Type.EmptyTypes);
                if (m == null) return;
                projects = m.Invoke(sol, null);
            }
            catch { return; }
            if (projects == null) return;

            // 确定当前 ActiveProject 对象（用于标记 isActive）
            object activeProj = null;
            try { activeProj = _studio.ActiveProject; } catch { }
            object primaryProj = null;
            try
            {
                var pm = FindMethod(sol.GetType(), "get_PrimaryProject", Type.EmptyTypes);
                if (pm != null) primaryProj = pm.Invoke(sol, null);
            }
            catch { }

            var items = projects as System.Collections.IEnumerable;
            if (items == null) return;

            int idx = 0;
            foreach (var projObj in items)
            {
                if (projObj == null) continue;
                idx++;
                var slot = new ProjectSlot();
                slot.Project = projObj;
                slot.ProjectType = projObj.GetType();
                // 名称：优先 Name 属性，退而求其次用默认别名
                string name = null;
                try
                {
                    var nameProp = slot.ProjectType.GetProperty("Name");
                    name = nameProp?.GetValue(projObj)?.ToString();
                }
                catch { }
                if (string.IsNullOrEmpty(name))
                    name = "project" + idx;
                // 确保名字唯一
                string key = name;
                int n = 2;
                while (_projectPool.ContainsKey(key))
                    key = name + "_" + (n++);
                slot.Name = key;
                slot.IsActive = ReferenceEquals(projObj, activeProj);
                slot.IsPrimary = ReferenceEquals(projObj, primaryProj);
                // 缓存 ProjectItem/WrappedItem
                try
                {
                    var wm = slot.ProjectType.GetMethod("get_WrappedItem",
                        BindingFlags.Public | BindingFlags.Instance | BindingFlags.FlattenHierarchy,
                        null, Type.EmptyTypes, null);
                    if (wm != null)
                    {
                        var wi = wm.Invoke(projObj, null);
                        if (wi != null)
                        {
                            slot.ProjectItem = wi;
                            slot.ProjectItemType = wi.GetType();
                        }
                    }
                }
                catch { }

                _projectPool[key] = slot;
                // 注册 @proj:<name> 别名；但若该对象已是 @project/@projectItem（当前活跃工程），
                // 不覆盖其别名（避免破坏 @project 语义），路径解析走 _projectPool 即可。
                if (!ReferenceEquals(projObj, _project) && !ReferenceEquals(projObj, _projectItem))
                {
                    try { RegisterWithId(projObj, "@proj:" + key); } catch { }
                }
            }
        }

        /// <summary>V12：列出所有已打开工程。返回数组，每项 { name, isActive, isPrimary }。</summary>
        public Dictionary<string, object>[] ListProjects()
        {
            var result = new List<Dictionary<string, object>>();
            foreach (var kv in _projectPool)
            {
                var s = kv.Value;
                result.Add(new Dictionary<string, object>
                {
                    ["name"] = s.Name,
                    ["isActive"] = s.IsActive,
                    ["isPrimary"] = s.IsPrimary,
                    ["ref"] = "@proj:" + s.Name
                });
            }
            return result.ToArray();
        }

        /// <summary>V12：选择指定工程为「当前操作上下文」。之后所有基于 @project 的调用（路径解析/CreateProjectItem 等）
        /// 自动作用于该工程，且**不切换 Kanzi Studio 的 ActiveProject**（不打扰老隋正在编辑的工程）。
        /// name 为空/null/等于 ActiveProject 名 → 切回 ActiveProject。</summary>
        public string SelectProject(string name)
        {
            if (string.IsNullOrWhiteSpace(name))
            {
                // 切回 ActiveProject
                _selectedProjectName = null;
                object ap;
                try { ap = _studio.ActiveProject; } catch { ap = null; }
                if (ap != null)
                {
                    _project = ap;
                    _projectType = ap.GetType();
                    _projectItem = null;
                    _projectItemType = null;
                    CacheReflectionTypes();
                }
                return $"已切回 ActiveProject: {GetProjectName()}";
            }

            name = name.Trim();
            ProjectSlot slot;
            if (!_projectPool.TryGetValue(name, out slot))
            {
                // 工程池里没有：尝试刷新一次再找
                RefreshProjects();
                if (!_projectPool.TryGetValue(name, out slot))
                    throw new KeyNotFoundException($"找不到工程 '{name}'。用 kz_list_projects 查看所有已打开工程。");
            }

            _selectedProjectName = slot.Name;
            _project = slot.Project;
            _projectType = slot.ProjectType;
            _projectItem = slot.ProjectItem;
            _projectItemType = slot.ProjectItemType;
            if (_projectItem == null)
                CacheReflectionTypes(); // 兜底：若未缓存 WrappedItem，走通用路径

            return $"已切换到工程: {slot.Name}" + (slot.IsActive ? " (ActiveProject)" : "") +
                   (slot.IsPrimary ? " (Primary)" : "");
        }

        /// <summary>V12：当前操作的工程名（SelectProject 选中的，未选中则为 ActiveProject 名）。</summary>
        public string GetSelectedProjectName()
        {
            return _selectedProjectName ?? GetProjectName();
        }

        /// <summary>V12：解析 `@proj:&lt;name&gt;` 或 `@proj:&lt;name&gt;/&lt;path&gt;`。
        /// 纯工程名→工程对象；带路径→临时切到该工程解析节点/项目项后切回（不动 ActiveProject）。</summary>
        private object ResolveProjPath(string body)
        {
            body = body.TrimStart('/');
            int slash = body.IndexOf('/');
            string projName;
            string path;
            if (slash >= 0)
            {
                projName = body.Substring(0, slash);
                path = body.Substring(slash + 1);
            }
            else
            {
                projName = body;
                path = null;
            }
            if (string.IsNullOrEmpty(projName))
                throw new KeyNotFoundException($"@proj: 缺少工程名");

            ProjectSlot slot;
            if (!_projectPool.TryGetValue(projName, out slot))
            {
                RefreshProjects();
                if (!_projectPool.TryGetValue(projName, out slot))
                    throw new KeyNotFoundException($"找不到工程 '{projName}'。用 kz_list_projects 查看所有已打开工程。");
            }

            // 纯工程名 → 返回工程对象
            if (string.IsNullOrEmpty(path))
                return slot.Project;

            // 带路径 → 临时切换当前上下文解析，再切回
            object oldProject = _project;
            object oldProjectItem = _projectItem;
            Type oldProjectType = _projectType;
            Type oldProjectItemType = _projectItemType;
            try
            {
                _project = slot.Project;
                _projectType = slot.ProjectType;
                _projectItem = slot.ProjectItem;
                _projectItemType = slot.ProjectItemType;
                if (_projectItem == null) CacheReflectionTypes();

                var node = GetNodeByPath(path);
                if (node != null) return node;
                var pi = GetProjectItem(path);
                if (pi != null) return pi;
                throw new KeyNotFoundException($"在工程 '{projName}' 中找不到节点/项目项: '{path}'");
            }
            finally
            {
                _project = oldProject;
                _projectType = oldProjectType;
                _projectItem = oldProjectItem;
                _projectItemType = oldProjectItemType;
            }
        }



        // ====== 调试/诊断方法 ======
        public string[] DebugListProjectMethods()
        {
            if (_projectType == null) return new[] { "(no project type)" };
            return _projectType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Select(m => $"{m.Name}({string.Join(",", m.GetParameters().Select(p => p.ParameterType.Name))})")
                .OrderBy(n => n)
                .ToArray();
        }

        public string[] DebugListProjectItemMethods()
        {
            if (_projectItemType == null) return new[] { "(no project item type)" };
            return _projectItemType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Select(m => $"{m.Name}({string.Join(",", m.GetParameters().Select(p => p.ParameterType.Name))})")
                .OrderBy(n => n)
                .ToArray();
        }

        public string[] DebugListProjectItemProperties()
        {
            if (_projectItemType == null) return new[] { "(no project item type)" };
            return _projectItemType.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Select(p => $"{p.Name}: {p.PropertyType.Name}")
                .OrderBy(n => n)
                .ToArray();
        }

        public string[] DebugListWrappedItemMethods()
        {
            if (_projectItemType == null) return new[] { "(no wrapped item type)" };
            return _projectItemType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.FlattenHierarchy)
                .Select(m => $"{m.Name}({string.Join(",", m.GetParameters().Select(p => p.ParameterType.Name))})")
                .OrderBy(n => n)
                .ToArray();
        }

        public string[] DebugListWrappedItemProperties()
        {
            if (_projectItemType == null) return new[] { "(no wrapped item type)" };
            return _projectItemType.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.FlattenHierarchy)
                .Select(p => $"{p.Name}: {p.PropertyType.Name}")
                .OrderBy(n => n)
                .ToArray();
        }

        public string DebugGetWrappedItemTypeFullName()
        {
            return _projectItemType?.FullName ?? "(null)";
        }

        public string DebugGetProjectTypeFullName()
        {
            return _projectType?.FullName ?? "(null)";
        }

        public string[] DebugGetNodeInfo(string path)
        {
            var node = GetNodeByPath(path);
            if (node == null) return new[] { "(node not found)" };
            var t = node.GetType();
            var result = new List<string>();
            result.Add($"Type: {t.FullName}");
            result.Add($"BaseType: {t.BaseType?.FullName}");
            foreach (var iface in t.GetInterfaces())
                result.Add($"Interface: {iface.FullName}");
            result.Add("--- Methods ---");
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Where(m => !m.Name.StartsWith("add_") && !m.Name.StartsWith("remove_")
                    && !m.Name.StartsWith("get_") && !m.Name.StartsWith("set_"))
                .Select(m => $"{m.Name}({string.Join(",", m.GetParameters().Select(p => p.ParameterType.Name))})")
                .OrderBy(n => n))
                result.Add(m);
            result.Add("--- Properties ---");
            foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Select(p => $"{p.Name}: {p.PropertyType.Name}")
                .OrderBy(n => n))
                result.Add(p);
            return result.ToArray();
        }

        #region 对象引用管理

        private string RegisterObject(object obj)
        {
            if (obj == null) return null;
            if (_objectToRefId.TryGetValue(obj, out var existingId))
                return existingId;
            if (obj == _studio)
                return RegisterWithId(obj, "@studio");
            if (obj == _project)
                return RegisterWithId(obj, "@project");
            if (obj == _projectItem)
                return RegisterWithId(obj, "@projectItem");
            var refId = "@obj" + System.Threading.Interlocked.Increment(ref _nextRefId);
            return RegisterWithId(obj, refId);
        }

        private string RegisterWithId(object obj, string refId)
        {
            _objectStore[refId] = obj;
            _objectToRefId[obj] = refId;
            return refId;
        }

        public void ClearObjectStore()
        {
            _objectStore.Clear();
            _objectToRefId.Clear();
            _nextRefId = 0;
        }

        public Dictionary<string, object> ListRefs()
        {
            var result = new Dictionary<string, object>();
            foreach (var kv in _objectStore)
            {
                var obj = kv.Value;
                string name;
                try
                {
                    var nameProp = obj.GetType().GetProperty("Name");
                    name = nameProp?.GetValue(obj)?.ToString() ?? obj.GetType().Name;
                }
                catch { name = obj.GetType().Name; }
                result[kv.Key] = new Dictionary<string, object>
                {
                    ["type"] = obj.GetType().Name,
                    ["name"] = name
                };
            }
            return result;
        }

        public object ResolveObject(string refOrPath)
        {
            if (string.IsNullOrEmpty(refOrPath))
                return null;
            if (refOrPath.StartsWith("@"))
            {
                // V12: @proj:<工程名>[/路径] → 指定工程（及其中节点/项目项）
                if (refOrPath.StartsWith("@proj:", StringComparison.OrdinalIgnoreCase))
                {
                    return ResolveProjPath(refOrPath.Substring("@proj:".Length));
                }
                // v4: @node:/path → 按节点路径解析（target 场景）
                if (refOrPath.StartsWith("@node:"))
                {
                    var nodeObj = GetNodeByPath(refOrPath.Substring("@node:".Length));
                    if (nodeObj != null) return nodeObj;
                    throw new KeyNotFoundException($"无法解析节点路径: '{refOrPath}'");
                }
                // v4: 新格式 @obj:23 → 归一化为 @obj23（缓存 key 无冒号）
                var key = refOrPath;
                if (refOrPath.StartsWith("@obj:"))
                    key = "@obj" + refOrPath.Substring("@obj:".Length);
                if (_objectStore.TryGetValue(key, out var obj))
                    return obj;
                throw new KeyNotFoundException($"对象引用 '{refOrPath}' 不存在或已失效。使用 kz_list_refs 查看可用引用。");
            }
            var node = GetNodeByPath(refOrPath);
            if (node != null)
                return node;
            try
            {
                var pi = GetProjectItem(refOrPath);
                if (pi != null) return pi;
            }
            catch { }
            throw new KeyNotFoundException($"无法解析对象路径或引用: '{refOrPath}'");
        }

        public string GetRefName(string refId)
        {
            if (!_objectStore.TryGetValue(refId, out var obj))
                return $"引用 '{refId}' 不存在";
            try
            {
                var nameProp = obj.GetType().GetProperty("Name");
                return nameProp?.GetValue(obj)?.ToString() ?? "(unnamed)";
            }
            catch { return obj.GetType().Name; }
        }

        public object GetRefMethods(string refId)
        {
            if (!_objectStore.TryGetValue(refId, out var obj))
                return new Dictionary<string, object> { ["error"] = $"引用 '{refId}' 不存在" };
            var t = obj.GetType();
            var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Select(m => $"{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name))})")
                .OrderBy(n => n)
                .ToArray();
            var ifaceMethods = t.GetInterfaces()
                .SelectMany(iface => iface.GetMethods(BindingFlags.Public | BindingFlags.Instance))
                .Select(m => $"{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name))})")
                .Distinct()
                .OrderBy(n => n)
                .ToArray();
            return new Dictionary<string, object>
            {
                ["type"] = t.FullName,
                ["methods"] = methods,
                ["interfaceMethods"] = ifaceMethods
            };
        }

        public object GetRefProperties(string refId)
        {
            if (!_objectStore.TryGetValue(refId, out var obj))
                return new Dictionary<string, object> { ["error"] = $"引用 '{refId}' 不存在" };
            var t = obj.GetType();
            var props = t.GetProperties(BindingFlags.Public | BindingFlags.Instance)
                .Select(p =>
                {
                    var val = "(unreadable)";
                    try
                    {
                        var v = p.GetValue(obj);
                        val = v?.ToString() ?? "(null)";
                    }
                    catch { }
                    return new Dictionary<string, object>
                    {
                        ["name"] = p.Name,
                        ["type"] = p.PropertyType.Name,
                        ["value"] = val
                    };
                })
                .ToList();
            return new Dictionary<string, object>
            {
                ["type"] = t.FullName,
                ["properties"] = props
            };
        }

        /// <summary>只读探测一个类型的构造函数 + 方法（不执行任何逻辑，不污染工程）。用于验证如 CreateLocaleCommandRecord 等命令记录是否可加载/可反射。</summary>
        public object ProbeType(string fullTypeName)
        {
            var res = new Dictionary<string, object>();
            res["fullType"] = fullTypeName;
            Type t = LoadTypeByFullName(fullTypeName) ?? ResolveTypeByName(fullTypeName);
            if (t == null)
            {
                res["loaded"] = false;
                res["error"] = "类型未加载到 Studio 进程（LoadTypeByFullName/ResolveTypeByName 均失败）";
                return res;
            }
            res["loaded"] = true;
            res["type"] = t.FullName;
            res["assembly"] = t.Assembly?.GetName()?.Name;
            var ctors = new List<object>();
            foreach (var c in t.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                ctors.Add("(" + string.Join(", ", c.GetParameters().Select(p => (p.ParameterType.FullName ?? p.ParameterType.Name) + " " + p.Name)) + ")");
            }
            res["ctors"] = ctors;
            var methods = new List<object>();
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                       .Where(m => !m.IsSpecialName || m.Name.StartsWith("get_") || m.Name.StartsWith("set_") || m.Name == "Execute" || m.Name == "CreateProjectItem"))
            {
                methods.Add(m.Name + "(" + string.Join(", ", m.GetParameters().Select(p => (p.ParameterType.FullName ?? p.ParameterType.Name) + " " + p.Name)) + ")");
            }
            res["methods"] = methods.Distinct().ToList();
            return res;
        }

        /// <summary>
        /// [v13+]: 给本地化表新增一个语言（语言列）。
        /// 走 CreateLocaleCommandRecord.CreateProjectItem（等价 GUI 菜单"新建语言"）。
        /// target = 本地化表路径或 @obj 引用；lang = 新语言码（缩写，如 "de"）。
        /// return：{ success, lang, recordRef, message }。
        /// </summary>
        public object AddLanguage(string target, string lang)
        {
            // ★ Kanzi 对象操作必须在 UI 线程，否则报"调用线程无法访问此对象"
            if (!IsUiThread())
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                {
                    return app.Dispatcher.Invoke(new Func<object>(() =>
                        AddLanguageCore(target, lang)));
                }
            }
            return AddLanguageCore(target, lang);
        }

        private object AddLanguageCore(string target, string lang)
        {
            var res = new Dictionary<string, object>
            {
                ["lang"] = lang,
                ["target"] = target
            };
            if (string.IsNullOrEmpty(lang))
            {
                res["success"] = false;
                res["message"] = "lang 不能为空（传新语言码，如 de）";
                return res;
            }

            // ---- 1. 解析目标表 & 拿内部 LocalizationTable 对象 ----
            object wrapperObj = null;
            if (target == "project" || target == "@project") wrapperObj = _project;
            else wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
            {
                res["success"] = false;
                res["message"] = $"无法解析目标表: '{target}'";
                return res;
            }
            // CreateLocaleCommandRecord 构造需要的是【内部】LocalizationTable
            // （Rightware.Kanzi.Tool.Logic.Project.ResourceLocalizationItems.LocalizationTable），
            // 即 wrapper 的 get_WrappedItem() 返回的对象，不是 PluginInterface 包装器。
            object internalTable = GetWrappedItemRaw(wrapperObj) ?? wrapperObj;

            // ---- 2. 解析 CreateLocaleCommandRecord 类型（全反射）----
            var recordType = ResolveTypeByName("Rightware.Kanzi.Tool.Logic.Project.ResourceLocalizationItems.CreateLocaleCommandRecord");
            if (recordType == null)
            {
                res["success"] = false;
                res["message"] = "解析 CreateLocaleCommandRecord 失败（LogicProject 未加载？）";
                return res;
            }

            // ---- 3. 构造 CreateLocaleCommandRecord(parent, name) ----
            ConstructorInfo ctor = null;
            try
            {
                // 按参数兼容匹配：(LocalizationTable, String)
                ctor = recordType.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .FirstOrDefault(c =>
                    {
                        var p = c.GetParameters();
                        return p.Length == 2 && p[1].ParameterType == typeof(string) &&
                               (p[0].ParameterType.IsAssignableFrom(internalTable.GetType()) ||
                                internalTable.GetType().IsAssignableFrom(p[0].ParameterType));
                    });
                if (ctor == null)
                    ctor = recordType.GetConstructors().FirstOrDefault(c =>
                    {
                        var p = c.GetParameters();
                        return p.Length == 2 && p[1].ParameterType == typeof(string);
                    });
            }
            catch { }
            if (ctor == null)
            {
                res["success"] = false;
                res["message"] = "CreateLocaleCommandRecord 上找不到 (LocalizationTable, String) 构造器";
                return res;
            }

            object record;
            try
            {
                record = ctor.Invoke(new object[] { internalTable, lang });
            }
            catch (System.Reflection.TargetInvocationException tie)
            {
                res["success"] = false;
                res["message"] = $"创建 CreateLocaleCommandRecord 失败: {tie.InnerException?.Message ?? tie.Message}";
                return res;
            }
            string recordRef = RegisterObject(record);
            res["recordRef"] = recordRef;

            // ---- 4. 调 CreateProjectItem(lang) 真正新建语言 ----
            var createMethod = FindMethodByParamCount(recordType, "CreateProjectItem", 1)
                              ?? recordType.GetMethod("CreateProjectItem", new[] { typeof(string) });
            if (createMethod == null)
            {
                res["success"] = false;
                res["message"] = "CreateLocaleCommandRecord 上找不到 CreateProjectItem(String)";
                return res;
            }
            try
            {
                createMethod.Invoke(record, new object[] { lang });
                res["success"] = true;
                res["message"] = $"已创建语言: {lang}（记录 ref={recordRef}）";
            }
            catch (System.Reflection.TargetInvocationException tie)
            {
                res["success"] = false;
                res["message"] = $"CreateLocaleCommandRecord.CreateProjectItem 失败: {tie.InnerException?.Message ?? tie.Message}";
            }
            return res;
        }

        /// <summary>
        /// [v13+]: 删除本地化表的一个语言（语言列）。
        /// 等价 GUI 菜单"删除" → Delete ProjectItem ".../Localization Table/<lang>"：
        /// 对 get_Locales 里匹配 lang 的 Locale 项目项调 Delete()（标准项目项删除）。
        /// target = 本地化表路径或 @obj 引用；lang = 语言码（缩写，如 "de"）。
        /// 安全：只删完全匹配的那一个语言；找不到 lang 不删任何东西，返回 found=false。
        /// return：{ success, lang, found, message }。
        /// </summary>
        public object DeleteLanguage(string target, string lang)
        {
            // ★ Kanzi 对象操作必须在 UI 线程，否则报"调用线程无法访问此对象"
            if (!IsUiThread())
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                {
                    return app.Dispatcher.Invoke(new Func<object>(() =>
                        DeleteLanguageCore(target, lang)));
                }
            }
            return DeleteLanguageCore(target, lang);
        }

        private object DeleteLanguageCore(string target, string lang)
        {
            var res = new Dictionary<string, object>
            {
                ["lang"] = lang,
                ["target"] = target
            };
            if (string.IsNullOrEmpty(lang))
            {
                res["success"] = false;
                res["found"] = false;
                res["message"] = "lang 不能为空（传要删除的语言码，如 de）";
                return res;
            }

            // ---- 1. 解析目标表 & 拿内部 LocalizationTable 对象 ----
            object wrapperObj = null;
            if (target == "project" || target == "@project") wrapperObj = _project;
            else wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
            {
                res["success"] = false;
                res["found"] = false;
                res["message"] = $"无法解析目标表: '{target}'";
                return res;
            }
            object internalTable = GetWrappedItemRaw(wrapperObj) ?? wrapperObj;

            // ---- 2. 枚举 get_Locales，找匹配 lang 的 Locale（精确匹配语言码）----
            object targetLocale = null;
            string foundName = null;
            foreach (var lo in GetLocalesList(internalTable))
            {
                var ln = GetStringPropValue(lo, "LocaleName")
                         ?? GetStringPropValue(lo, "Name");
                if (ln != null && string.Equals(ln.Trim(), lang.Trim(), StringComparison.OrdinalIgnoreCase))
                {
                    targetLocale = lo;
                    foundName = ln;
                    break;
                }
            }
            if (targetLocale == null)
            {
                res["success"] = false;
                res["found"] = false;
                res["message"] = $"表中不存在语言 '{lang}'，未删除任何内容（当前语言列见 get_Locales）";
                return res;
            }
            res["found"] = true;
            res["foundName"] = foundName;

            // ---- 3. 对该 Locale 项目项调 Delete()（等价 GUI Delete ProjectItem）----
            MethodInfo deleteMethod = null;
            try
            {
                deleteMethod = FindMethod(targetLocale.GetType(), "Delete", Type.EmptyTypes);
                if (deleteMethod == null)
                {
                    deleteMethod = targetLocale.GetType().GetMethod("Delete", Type.EmptyTypes);
                }
            }
            catch { }
            if (deleteMethod == null)
            {
                res["success"] = false;
                res["message"] = $"Locale 类型 {targetLocale.GetType().Name} 上找不到 Delete() 方法";
                return res;
            }
            try
            {
                object delRes = deleteMethod.Invoke(targetLocale, null);
                bool deleted = delRes == null || (delRes is bool b && b);
                if (!deleted)
                {
                    res["success"] = false;
                    res["message"] = $"Delete() 返回了假值（结果 {delRes?.ToString() ?? "null"}），语言 '{foundName}' 可能未删除";
                    return res;
                }
                res["success"] = true;
                res["message"] = $"已删除语言: {foundName}";
            }
            catch (System.Reflection.TargetInvocationException tie)
            {
                res["success"] = false;
                res["message"] = $"删除语言 '{foundName}' 失败: {tie.InnerException?.Message ?? tie.Message}";
            }
            catch (Exception ex)
            {
                res["success"] = false;
                res["message"] = $"删除语言 '{foundName}' 失败: {ex.Message}";
            }
            return res;
        }

        #endregion 对象引用管理

        #region 通用反射调用

        /// <summary>
        /// 通用反射调用：在任意目标上调用任意方法。
        /// target 支持: "@refId", "@studio", "@project", "@projectItem", "/path/to/node"
        /// 默认走 UI 线程（保持旧行为），兼容旧调用方。
        /// </summary>
        public object Invoke(string target, string method, object[] args)
        {
            return Invoke(target, method, args, false);
        }

        /// <summary>
        /// 通用反射调用（带线程策略）。
        /// runOffUiThread=false：保持默认行为，统一切到 UI 线程执行（Kanzi Studio 是 WPF 应用,
        ///   大量对象(尤其 BindingHost/DSO) 只能在创建它的 UI(Dispatcher)线程访问）。
        /// runOffUiThread=true：**直接在当前线程（已是线程池线程）上同步执行 InvokeCore**，
        ///   不做任何新线程/Dispatcher 调度，与旧版"不强制UI线程"的行为一致。
        /// </summary>
        public object Invoke(string target, string method, object[] args, bool runOffUiThread)
        {
            if (runOffUiThread)
            {
                // ★★ 关键：KzMCPServerClient 已在 Task.Run(async ...) 里调用到这里，
                // 当前线程就已经是 .NET 线程池的托管线程（和旧版 HTTP 不强制UI线程时一致）。
                // 所以直接在当前线程上同步执行 InvokeCore 即可，绝不 new Thread / StartNew
                //（那两种都会绕开线程池托管上下文 → 原生层访问违例崩溃）。
                return InvokeCore(target, method, args);
            }

            // ★ 统一调度到 UI 线程: Kanzi Studio 是 WPF 应用, 大量对象(尤其 BindingHost/DSO)
            //   只能在创建它的 UI(Dispatcher)线程访问。为避免各类"调用线程无法访问此对象",
            //   **所有**反射调用统一切到 UI 线程执行。
            if (!IsUiThread())
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                {
                    return app.Dispatcher.Invoke(
                        new Func<object>(() => InvokeCore(target, method, args)));
                }
            }
            // 已在 UI 线程(含 Dispatcher.Invoke 进去之后内部再调用) → 直接执行
            return InvokeCore(target, method, args);
        }

        /// <summary>
        /// 判断某次 kz_invoke 是否应跑在非UI线程（线程策略）。
        /// 规则：状态机相关的创建/设置类调用走非UI线程提速；其余反射仍走UI线程。
        /// 会实际解析 target 指向的运行时对象类型，从而把 State/StateObject 上的
        /// set_Item/get_Item 等调用也判为可离线。由 KzMCPServerClient 分派 kz_invoke 时调用。
        /// </summary>
        public bool ShouldRunOffUiThread(string target, string method, object[] args)
        {
            if (string.IsNullOrEmpty(method)) return false;

            // 批量事务包裹：状态机创建通常包在 Begin/Commit 批里
            if (method == "BeginBatchModification" || method == "CommitBatchModification")
                return true;

            // 创建状态机/状态组/状态/状态对象
            if (method == "CreateProjectItem")
            {
                if (args != null && args.Length >= 1 && args[0] is string typeStr)
                {
                    var t = typeStr.Replace("@type:", "").Trim();
                    if (t == "StateManager" || t == "StateGroup" ||
                        t == "State" || t == "StateObject" ||
                        t.EndsWith("StateManager") || t.EndsWith("StateGroup") ||
                        t.EndsWith("State") || t.EndsWith("StateObject"))
                        return true;
                }
                return false;
            }

            // 状态/状态对象的属性与控制值设置
            if (method == "set_TargetObjectPath" || method == "get_TargetObjectPath")
                return true;

            if (method == "set_Item" || method == "get_Item")
            {
                // 解析目标对象的运行时类型：若是 State/StateObject 包装器则判为可离线(提速)；
                // 其余 set_Item/get_Item（如普通节点属性）保守保持 UI 线程。
                if (IsStateTarget(target))
                    return true;
                return false;
            }

            return false;
        }

        /// <summary>
        /// 判断 target 指向的运行时对象是否为状态机相关包装器
        /// （StateManager/StateGroup/State/StateObject）。
        /// </summary>
        private bool IsStateTarget(string target)
        {
            try
            {
                object obj = ResolveObject(target);
                if (obj == null) return false;
                var name = obj.GetType().Name;
                if (string.IsNullOrEmpty(name)) return false;
                return name.IndexOf("StateManager", StringComparison.OrdinalIgnoreCase) >= 0 ||
                       name.IndexOf("StateGroup", StringComparison.OrdinalIgnoreCase) >= 0 ||
                       name.IndexOf("StateObject", StringComparison.OrdinalIgnoreCase) >= 0 ||
                       // 注意：State 是 StateObject 的子串，需排除误判；这里单独精确判断
                       name.Equals("StatePluginWrapper", StringComparison.OrdinalIgnoreCase) ||
                       name.Equals("State", StringComparison.OrdinalIgnoreCase);
            }
            catch
            {
                return false;
            }
        }

        private static bool IsUiThread()
        {
            try
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                    return app.Dispatcher.CheckAccess();
            }
            catch { }
            return true; // 无法判断时默认允许直调(不阻塞)
        }

        private object InvokeCore(string target, string method, object[] args)
        {
            // [V9 静态调用扩展] target 形如 "@static:Full.Type.Name" → 调 CLR 类型的静态方法
            // 例: @static:System.Diagnostics.Process + GetProcesses()  → 枚举进程拿 Preview PID
            // @static:System.Diagnostics.Process + GetProcessById(@int:1234) → 按 PID 拿进程对象
            if (target != null && target.StartsWith("@static:"))
            {
                var typeName = target.Substring("@static:".Length).Trim();
                // Process/窗口截图等系统类无 UI 线程约束，但静态方法可能返回 UI 对象
                return InvokeStatic(typeName, method, args);
            }

            object targetObj;
            if (target == "studio" || target == "@studio")
                targetObj = _studio;
            else if (target == "project" || target == "@project")
                targetObj = _project;
            else if (target == "projectItem" || target == "@projectItem")
                targetObj = _projectItem;
            else
                targetObj = ResolveObject(target);  // V12: 内含 @proj:<名称>[/路径] 解析

            if (targetObj == null)
                throw new InvalidOperationException($"target '{target}' 解析为 null");

            var resolvedArgs = ResolveArgs(args, method);

            // 针对枚举参数的自动转换：如果某个方法的参数是枚举类型而传入的是 int，自动 Enum.ToObject
            var targetType = targetObj.GetType();
            MethodInfo enumMethod;
            object[] enumArgs;
            if (FindEnumMethod(targetType, method, resolvedArgs, out enumMethod, out enumArgs))
            {
                try
                {
                    var rawResult = enumMethod.Invoke(targetObj, enumArgs);
                    return MaybeWrap(rawResult);
                }
                catch (TargetInvocationException tie)
                {
                    throw new InvalidOperationException($"调用 {method} 失败: {tie.InnerException?.Message ?? tie.Message}");
                }
            }

            // null 参数的类型用 typeof(object) 占位，但所有匹配都应允许 null 匹配任意引用类型
            var paramTypes = resolvedArgs.Select(a => a?.GetType() ?? typeof(object)).ToArray();
            // 判断 null 参数位置，用于宽松匹配
            var argIsNull = resolvedArgs.Select(a => a == null).ToArray();

            var mi = FindMethod(targetType, method, paramTypes);

            // 放宽匹配
            if (mi == null)
            {
                var allMethods = targetType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                    .Where(m => m.Name == method)
                    .ToList();
                foreach (var iface in targetType.GetInterfaces())
                {
                    allMethods.AddRange(iface.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                        .Where(m => m.Name == method));
                }
                allMethods = allMethods.GroupBy(m => m.ToString()).Select(g => g.First()).ToList();

                if (allMethods.Count == 0)
                {
                    throw new MissingMethodException($"在 {targetType.Name} 上找不到方法 '{method}'");
                }

                if (allMethods.Count == 1)
                {
                    mi = allMethods[0];
                }
                else
                {
                    // 类型兼容匹配
                    foreach (var candidate in allMethods)
                    {
                        var pars = candidate.GetParameters();
                        if (pars.Length != paramTypes.Length) continue;
                        bool match = true;
                        for (int i = 0; i < pars.Length; i++)
                        {
                            if (resolvedArgs[i] == null) continue;
                            var argType = resolvedArgs[i].GetType();
                            var paramType = pars[i].ParameterType;
                            if (paramType.IsAssignableFrom(argType)) continue;
                            if (IsNumericConversion(argType, paramType)) continue;
                            match = false;
                            break;
                        }
                        if (match) { mi = candidate; break; }
                    }
                }
            }

            // 最终尝试：参数数量相同的强试
            if (mi == null)
            {
                var allMethods2 = targetType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                    .Where(m => m.Name == method && m.GetParameters().Length == paramTypes.Length && !m.IsGenericMethodDefinition)
                    .ToList();
                foreach (var iface in targetType.GetInterfaces())
                {
                    allMethods2.AddRange(iface.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                        .Where(m => m.Name == method && m.GetParameters().Length == paramTypes.Length && !m.IsGenericMethodDefinition));
                }
                foreach (var iface in targetType.GetInterfaces())
                {
                    try
                    {
                        var map = targetType.GetInterfaceMap(iface);
                        for (int i = 0; i < map.InterfaceMethods.Length; i++)
                        {
                            var ifaceMethod = map.InterfaceMethods[i];
                            if (ifaceMethod.Name == method && ifaceMethod.GetParameters().Length == paramTypes.Length && !ifaceMethod.IsGenericMethodDefinition)
                                allMethods2.Add(ifaceMethod);
                        }
                    }
                    catch { }
                }
                allMethods2 = allMethods2.GroupBy(m => m.ToString()).Select(g => g.First()).ToList();
                foreach (var candidate in allMethods2)
                {
                    try
                    {
                        var rawResult = candidate.Invoke(targetObj, resolvedArgs);
                        mi = candidate;
                        break;
                    }
                    catch
                    {
                        continue;
                    }
                }
            }

            // 泛型方法处理
            if (mi == null)
            {
                var genericMethods = targetType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                    .Where(m => m.Name == method && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 1)
                    .ToList();
                foreach (var iface in targetType.GetInterfaces())
                {
                    genericMethods.AddRange(iface.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                        .Where(m => m.Name == method && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 1));
                }

                if (genericMethods.Count > 0)
                {
                    foreach (var genMi in genericMethods)
                    {
                        var pars = genMi.GetParameters();
                        int genericParamCount = pars.Length;
                        int totalArgCount = resolvedArgs.Length;

                        // 解析第一参的短类型名
                        string typeName = null;
                        Type directTypeArg = null;
                        if (resolvedArgs.Length >= 1)
                        {
                            if (resolvedArgs[0] is Type t0)
                            {
                                // ★ @type: 前缀传进来的直接是 Type 对象 → 直接用
                                directTypeArg = t0;
                            }
                            else if (resolvedArgs[0] is string s0)
                            {
                                if (s0.StartsWith("@") && _objectStore.TryGetValue(s0, out var obj) && obj is Type rt)
                                {
                                    // @obj 引用指向 RuntimeType → 提取短类型名（如 StateManagerLibrary → StateManager）
                                    typeName = rt.Name;
                                    if (typeName.EndsWith("Library") && typeName.Length > 7)
                                        typeName = typeName.Substring(0, typeName.Length - 7);
                                }
                                else
                                {
                                    typeName = s0;
                                }
                            }
                        }

                        if (directTypeArg != null && genericParamCount == totalArgCount - 1)
                        {
                            try
                            {
                                var constructed = genMi.MakeGenericMethod(directTypeArg);
                                // 去掉 args[0]（Type 实参），只传实际方法参数
                                var actualArgs = new object[genericParamCount];
                                Array.Copy(resolvedArgs, 1, actualArgs, 0, genericParamCount);
                                var rawResult = constructed.Invoke(targetObj, actualArgs);
                                return MaybeWrap(rawResult);
                            }
                            catch { }
                        }

                        if (!string.IsNullOrEmpty(typeName) && genericParamCount == totalArgCount - 1)
                        {
                            var typeArg = FindProjectItemType(targetObj, typeName);
                            if (typeArg != null)
                            {
                                try
                                {
                                    var constructed = genMi.MakeGenericMethod(typeArg);
                                    // 去掉 args[0]（类型名），只传实际方法参数
                                    var actualArgs = new object[genericParamCount];
                                    Array.Copy(resolvedArgs, 1, actualArgs, 0, genericParamCount);
                                    var rawResult = constructed.Invoke(targetObj, actualArgs);
                                    return MaybeWrap(rawResult);
                                }
                                catch { }
                            }
                        }
                    }
                }

                // InterfaceMapping 查找
                foreach (var iface in targetType.GetInterfaces())
                {
                    try
                    {
                        var map = targetType.GetInterfaceMap(iface);
                        for (int i = 0; i < map.InterfaceMethods.Length; i++)
                        {
                            var ifaceMethod = map.InterfaceMethods[i];
                            if (ifaceMethod.Name != method) continue;
                            var pars = ifaceMethod.GetParameters();

                            if (ifaceMethod.IsGenericMethodDefinition && resolvedArgs.Length > 0)
                            {
                                // 解析第一参为短类型名
                                string typeName = null;
                                Type directTypeArg = null;
                                if (resolvedArgs[0] is Type t0)
                                {
                                    // ★ @type: 前缀传进来的直接是 Type 对象
                                    directTypeArg = t0;
                                }
                                else if (resolvedArgs[0] is string s0)
                                {
                                    if (s0.StartsWith("@") && _objectStore.TryGetValue(s0, out var obj) && obj is Type rt)
                                    {
                                        // @obj 引用指向 RuntimeType → 提取短类型名
                                        typeName = rt.Name;
                                        if (typeName.EndsWith("Library") && typeName.Length > 7)
                                            typeName = typeName.Substring(0, typeName.Length - 7);
                                    }
                                    else
                                    {
                                        typeName = s0;
                                    }
                                }

                                int genericParamCount = pars.Length;
                                int totalArgCount = resolvedArgs.Length;
                                if (directTypeArg != null && genericParamCount == totalArgCount - 1)
                                {
                                    try
                                    {
                                        var constructed = ifaceMethod.MakeGenericMethod(directTypeArg);
                                        var actualArgs = new object[genericParamCount];
                                        Array.Copy(resolvedArgs, 1, actualArgs, 0, genericParamCount);
                                        var rawResult = constructed.Invoke(targetObj, actualArgs);
                                        return MaybeWrap(rawResult);
                                    }
                                    catch { }
                                }

                                if (!string.IsNullOrEmpty(typeName))
                                {
                                    int genericParamCount2 = pars.Length;
                                    int totalArgCount2 = resolvedArgs.Length;
                                    if (genericParamCount2 == totalArgCount2 - 1)
                                    {
                                        var typeArg = FindProjectItemType(targetObj, typeName);
                                        if (typeArg != null)
                                        {
                                            try
                                            {
                                                var constructed = ifaceMethod.MakeGenericMethod(typeArg);
                                                var actualArgs = new object[genericParamCount];
                                                Array.Copy(resolvedArgs, 1, actualArgs, 0, genericParamCount);
                                                var rawResult = constructed.Invoke(targetObj, actualArgs);
                                                return MaybeWrap(rawResult);
                                            }
                                            catch { }
                                        }
                                    }
                                }
                            }

                            if (!ifaceMethod.IsGenericMethodDefinition)
                            {
                                // 1. 精确匹配
                                if (pars.Length == paramTypes.Length)
                                {
                                    bool match = true;
                                    for (int j = 0; j < pars.Length; j++)
                                    {
                                        if (resolvedArgs[j] == null) continue;
                                        var argType = resolvedArgs[j].GetType();
                                        var paramType = pars[j].ParameterType;
                                        if (paramType.IsAssignableFrom(argType)) continue;
                                        if (IsNumericConversion(argType, paramType)) continue;
                                        match = false;
                                        break;
                                    }
                                    if (match)
                                    {
                                        try
                                        {
                                            var rawResult = ifaceMethod.Invoke(targetObj, resolvedArgs);
                                            return MaybeWrap(rawResult);
                                        }
                                        catch { }
                                    }
                                }

                                // 2. 宽松匹配：参数数量相同就直接尝试调用
                                if (pars.Length == paramTypes.Length)
                                {
                                    try
                                    {
                                        var rawResult = ifaceMethod.Invoke(targetObj, resolvedArgs);
                                        return MaybeWrap(rawResult);
                                    }
                                    catch
                                    {
                                        // 参数类型不匹配，继续尝试
                                    }
                                }
                            }
                        }
                    }
                    catch { }
                }
            }

            if (mi == null)
                throw new MissingMethodException($"在 {targetType.Name} 上找不到与参数 ({string.Join(", ", paramTypes.Select(t => t.Name))}) 匹配的 '{method}'");

            try
            {
                var rawResult = mi.Invoke(targetObj, resolvedArgs);
                return MaybeWrap(rawResult);
            }
            catch (TargetInvocationException tie)
            {
                throw new InvalidOperationException($"调用 {method} 失败: {tie.InnerException?.Message ?? tie.Message}");
            }
        }

        /// <summary>
        /// [V9 静态调用扩展] 调用 CLR 类型的静态方法。
        /// 通过反射按完整类型名解析 Type，然后以 BindingFlags.Static 绑定并调用。
        /// target 形如 "@static:System.Diagnostics.Process"，method 形如 "GetProcesses" / "GetProcessById"。
        /// </summary>
        public object InvokeStatic(string fullTypeName, string method, object[] args)
        {
            if (string.IsNullOrEmpty(fullTypeName))
                throw new ArgumentException("静态类型名不能为空，target 形如 @static:System.Diagnostics.Process");

            // 优先复用 v8 现成的 ResolveTypeByName（内置类型映射 + Kanzi 映射 + Type.GetType +
            // AppDomain 已加载程序集遍历，最全），解析不到再走 ResolveStaticType 兜底。
            var t = ResolveTypeByName(fullTypeName) ?? ResolveStaticType(fullTypeName);
            if (t == null)
                throw new TypeLoadException($"无法解析类型 '{fullTypeName}'。可用 ListStaticMethods 查看");

            // 特例：method="ListStaticMethods" → 返回该类型的全部静态方法清单（便于探索，无需知道具体方法名）
            if (method == "ListStaticMethods")
            {
                var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Static)
                    .Select(m => $"{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name))}) -> {m.ReturnType.Name}")
                    .OrderBy(n => n)
                    .ToArray();
                return new Dictionary<string, object>
                {
                    ["type"] = t.FullName,
                    ["staticMethods"] = methods
                };
            }

            var resolvedArgs = ResolveArgs(args, method);
            var paramTypes = resolvedArgs.Select(a => a?.GetType() ?? typeof(object)).ToArray();

            // 优先精确参数匹配
            var mi = t.GetMethod(method, BindingFlags.Public | BindingFlags.Static, null, paramTypes, null);

            // 放宽：同名静态方法里按参数个数+类型兼容匹配
            if (mi == null)
            {
                var cands = t.GetMethods(BindingFlags.Public | BindingFlags.Static)
                    .Where(m => m.Name == method)
                    .ToList();
                if (cands.Count == 0)
                    throw new MissingMethodException($"在静态类型 {t.FullName} 上找不到方法 '{method}'");
                if (cands.Count == 1)
                {
                    mi = cands[0];
                }
                else
                {
                    mi = cands.FirstOrDefault(c =>
                    {
                        var pars = c.GetParameters();
                        if (pars.Length != paramTypes.Length) return false;
                        for (int i = 0; i < pars.Length; i++)
                        {
                            var pt = pars[i].ParameterType;
                            var av = resolvedArgs[i];
                            if (av == null)
                            {
                                if (pt.IsValueType) return false;
                                continue;
                            }
                            if (!pt.IsAssignableFrom(av.GetType()) && !(pt.IsEnum && av is int)) return false;
                        }
                        return true;
                    });
                    if (mi == null)
                        throw new MissingMethodException($"静态方法 '{method}' 参数不匹配（共 {cands.Count} 个重载）");
                }
            }

            try
            {
                var raw = mi.Invoke(null, resolvedArgs);   // 静态方法：targetObj 为 null
                return MaybeWrap(raw);
            }
            catch (TargetInvocationException tie)
            {
                throw new InvalidOperationException($"静态调用 {t.FullName}.{method} 失败: {tie.InnerException?.Message ?? tie.Message}");
            }
        }

        /// <summary>
        /// [V9 静态调用扩展] 解析一个 CLR 类型。支持完整类型名、带程序集限定名（逗号+程序集）。
        /// 解析失败时自动追加常见程序集再试（Process 等方法大多在 System / System.Core / mscorlib）。
        /// </summary>
        private static Type ResolveStaticType(string fullTypeName)
        {
            var t = Type.GetType(fullTypeName, false);
            if (t != null) return t;

            var candidates = new[]
            {
                fullTypeName + ", System",
                fullTypeName + ", System.Core",
                fullTypeName + ", mscorlib",
                fullTypeName + ", System.Drawing",
                fullTypeName + ", System.Windows.Forms",
                fullTypeName + ", PresentationCore",
            };
            foreach (var c in candidates)
            {
                t = Type.GetType(c, false);
                if (t != null) return t;
            }

            // 兜底：遍历当前 AppDomain 已加载的全部程序集，按完整类型名逐个查找。
            // Type.GetType 只认特定程序集/已加载位置，系统类型（如
            // System.Diagnostics.Process 在 System 程序集）有时解析不到，
            // 遍历已加载程序集最稳妥。
            try
            {
                foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    try
                    {
                        var x = asm.GetType(fullTypeName, false);
                        if (x != null && x.IsPublic) return x;
                    }
                    catch { }
                }
            }
            catch { }
            return null;
        }

        /// <summary>
        /// [V9 静态调用扩展] 列出某个 CLR 类型的全部静态方法（便于发现有哪些可调）。
        /// 例: kz_invoke target=@static:System.Diagnostics.Process method=ListStaticMethods
        /// </summary>
        public object ListStaticMethods(string fullTypeName)
        {
            var t = ResolveStaticType(fullTypeName);
            if (t == null) return new Dictionary<string, object> { ["error"] = $"无法解析类型 '{fullTypeName}'" };
            var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Static)
                .Select(m => $"{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name))}) -> {m.ReturnType.Name}")
                .OrderBy(n => n)
                .ToArray();
            return new Dictionary<string, object>
            {
                ["type"] = t.FullName,
                ["staticMethods"] = methods
            };
        }

        /// <summary>
        /// 在节点上通过反射调用方法（便捷方法内部用）
        /// </summary>
        private object CallNodeMethod(object node, string methodName, object[] args)
        {
            if (args == null)
                throw new ArgumentNullException(nameof(args));
            var types = args.Select(a => a?.GetType() ?? typeof(object)).ToArray();
            var method = FindMethod(node.GetType(), methodName, types);
            if (method == null)
                throw new InvalidOperationException(
                    $"节点类型 {node.GetType().Name} 及其接口上没有方法 {methodName}");

            try
            {
                return method.Invoke(node, args);
            }
            catch (TargetInvocationException tie)
            {
                throw new InvalidOperationException(
                    $"调用 {methodName} 失败: {tie.InnerException?.Message ?? tie.Message}");
            }
        }

        private object[] ResolveArgs(object[] args, string callerMethod = null)
        {
            if (args == null) return Array.Empty<object>();
            if (args.Length == 0) return Array.Empty<object>();
            return args.Select(a => ResolveSingleArg(a)).ToArray();
        }

        /// <summary>
        /// 找到包含枚举参数的方法，自动将 int 参数转换为枚举类型。
        /// 返回 true 表示找到匹配方法并已转换参数。
        /// </summary>
        private bool FindEnumMethod(Type targetType, string method, object[] resolvedArgs, out MethodInfo foundMethod, out object[] convertedArgs)
        {
            foundMethod = null;
            convertedArgs = null;

            if (resolvedArgs == null || resolvedArgs.Length == 0) return false;

            // 收集所有同名方法
            var allMethods = targetType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Where(m => m.Name == method)
                .ToList();
            foreach (var iface in targetType.GetInterfaces())
            {
                allMethods.AddRange(iface.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                    .Where(m => m.Name == method));
            }
            allMethods = allMethods.GroupBy(m => m.ToString()).Select(g => g.First()).ToList();

            foreach (var mi in allMethods)
            {
                var pars = mi.GetParameters();
                if (pars.Length != resolvedArgs.Length) continue;

                bool needsEnumConversion = false;
                var converted = new object[resolvedArgs.Length];
                bool validMethod = true;

                for (int i = 0; i < pars.Length; i++)
                {
                    var argVal = resolvedArgs[i];
                    var paramType = pars[i].ParameterType;

                    if (argVal == null)
                    {
                        if (paramType.IsValueType && !paramType.IsGenericType)
                        {
                            validMethod = false; break;
                        }
                        converted[i] = null; continue;
                    }

                    if (paramType.IsAssignableFrom(argVal.GetType()))
                    {
                        converted[i] = argVal; continue;
                    }

                    // int → enum 转换
                    if (paramType.IsEnum && argVal is int intVal)
                    {
                        converted[i] = Enum.ToObject(paramType, intVal);
                        needsEnumConversion = true; continue;
                    }

                    // v4: @enum:NAME 精准转换（EnumTag 标记）
                    if (paramType.IsEnum && argVal is EnumTag tag)
                    {
                        try
                        {
                            converted[i] = Enum.Parse(paramType, tag.Name, true);
                            needsEnumConversion = true; continue;
                        }
                        catch { validMethod = false; break; }
                    }

                    // string → enum 转换（枚举名称转值）
                    if (paramType.IsEnum && argVal is string strVal)
                    {
                        try
                        {
                            converted[i] = Enum.Parse(paramType, strVal);
                            needsEnumConversion = true; continue;
                        }
                        catch { validMethod = false; break; }
                    }

                    // @obj 引用：尝试解析为对象，用对象类型匹配参数
                    if (argVal is string argStr && argStr.StartsWith("@") && _objectStore.ContainsKey(argStr))
                    {
                        var resolved = _objectStore[argStr];
                        if (resolved != null && paramType.IsAssignableFrom(resolved.GetType()))
                        {
                            converted[i] = resolved;
                            continue;
                        }
                        // 解析后类型不匹配时，不要放弃此方法——保持字符串原值，跳过枚举需求继续尝试
                        // 让后面更宽松的匹配逻辑（强试或泛型处理）来处理
                        converted[i] = argStr;
                        continue;
                    }
                    // 其他类型不匹配，放弃此方法
                    validMethod = false; break;
                }

                if (validMethod && needsEnumConversion)
                {
                    foundMethod = mi;
                    convertedArgs = converted;
                    return true;
                }
            }

            return false;
        }

        private object ResolveSingleArg(object a)
        {
            if (a is string s)
            {
                // ============================================================
                // v4: 显式类型标识前缀（有标识 → 必须走标识，精准无歧义）
                // 无标识 → 落到底部自动猜测兜底（兼容老调用）
                // ============================================================

                // ---------- 数值/基础类型 ----------
                if (s.StartsWith("@int:"))   { return ParseOr(s, "@int:", int.TryParse, (int v) => v); }
                if (s.StartsWith("@long:"))  { return ParseOr(s, "@long:", long.TryParse, (long v) => v); }
                if (s.StartsWith("@float:")) { return ParseOr(s, "@float:", float.TryParse, (float v) => v); }
                if (s.StartsWith("@double:")) { return ParseOr(s, "@double:", double.TryParse, (double v) => v); }
                if (s.StartsWith("@decimal:")) { return ParseOr(s, "@decimal:", decimal.TryParse, (decimal v) => v); }
                if (s.StartsWith("@bool:"))  { return ParseOr(s, "@bool:", bool.TryParse, (bool v) => v); }
                if (s.StartsWith("@byte:"))  { return ParseOr(s, "@byte:", byte.TryParse, (byte v) => v); }
                if (s.StartsWith("@char:"))  { var cs = s.Substring("@char:".Length); return cs.Length > 0 ? (object)cs[0] : s; }
                if (s.StartsWith("@string:")) { return s.Substring("@string:".Length); } // 强制 string（解决 "123" 被转 int 的歧义）

                // ---------- null（用于可空参数，如 CreateFloatProperty 的 lowerBound/upperBound/step）----------
                if (s == "@null") return null;

                // ---------- 数学类型（System.Windows / System.Windows.Media.Media3D）----------
                if (s.StartsWith("@vector:"))    { return ParseVector(s.Substring("@vector:".Length)); }
                if (s.StartsWith("@vector3d:"))  { return ParseVector3D(s.Substring("@vector3d:".Length)); }
                if (s.StartsWith("@quaternion:")) { return ParseQuaternion(s.Substring("@quaternion:".Length)); }
                // ---------- Transformation2D（Rightware.Kanzi.Studio.PluginInterface.Transformation2D）----------
                // 格式 @transformation2d:scaleX,scaleY,rotation,tx,ty（逗号分隔，5 个 double）
                // 对应构造函数 (System.Windows.Vector scale, double rotation, System.Windows.Vector translation)
                // 用于 Node2D.RenderTransformation 等只接受 Transformation2D 值的属性（如 1;1;0;0;115 → @transformation2d:1,1,0,0,115）
                if (s.StartsWith("@transformation2d:")) { return ParseTransformation2D(s.Substring("@transformation2d:".Length)); }

                // ---------- 颜色（System.Windows.Media.Color，#AARRGGBB / #RRGGBB）----------
                // 构造 WPF Color 对象（ColorBrush.Color 等只接受 Color 值，不接受字符串）。用于 Set("ColorBrush.Color", "@color:#FF9BA014")。
                if (s.StartsWith("@color:")) { return ParseColor(s.Substring("@color:".Length)); }

                // ---------- 枚举：标记交给 FindEnumMethod 按目标方法签名精准转换 ----------
                if (s.StartsWith("@enum:"))
                {
                    var enumName = s.Substring("@enum:".Length).Trim();
                    if (enumName.Length > 0)
                        return new EnumTag(enumName);
                }

                // ---------- 类型 ----------
                // ★ @type: 前缀 → 解析为 .NET Type 对象（如 @type:string / @type:System.Int32）
                //   用于 CreateProperty<T> 等带 Type 参数/泛型类型实参的方法，通用支持。
                if (s.StartsWith("@type:"))
                {
                    var typeName = s.Substring("@type:".Length).Trim();
                    if (!string.IsNullOrEmpty(typeName))
                    {
                        var t = ResolveTypeByName(typeName);
                        if (t != null) return t; // 返回真正的 Type 对象
                    }
                    // 解析失败：保持原字符串，避免误吞
                    return s;
                }

                // ---------- 对象 / 节点引用 ----------
                // @project / @studio / @projectItem 特殊 target 作为 args 时也解析成对象（如 SaveProject("@project")）
                if (s == "@project" || s == "project") return _project;
                if (s == "@studio" || s == "studio") return _studio;
                if (s == "@projectItem" || s == "projectItem") return _projectItem;

                if (s.StartsWith("@obj:"))
                {
                    // 新格式 @obj:10 → @obj10
                    var refKey = "@obj" + s.Substring("@obj:".Length);
                    if (_objectStore.ContainsKey(refKey))
                    {
                        var resolvedObj = _objectStore[refKey];
                        if (resolvedObj is Type)
                            return refKey; // RuntimeType 保持字符串引用，供泛型匹配
                        return resolvedObj;
                    }
                    return s; // 未命中缓存：保持原样
                }
                if (s.StartsWith("@node:"))
                {
                    try { return GetNodeByPath(s.Substring("@node:".Length)); }
                    catch { return s; }
                }

                // ---------- 列表/集合 ----------
                // @list:类型名@obj1,@obj2  → List<T>（元素为已解析对象，用于 FontFiles 等 List 集合属性）
                // @list:@obj1,@obj2          → List<object>
                if (s.StartsWith("@list:"))
                {
                    var listObj = TryParseListArg(s.Substring("@list:".Length).Trim());
                    if (listObj != null)
                        return listObj;
                    return s; // 解析失败保持原样
                }

                // ---------- 空集合（LINQ Enumerable.Empty<T>()）---------
                // @empty:类型全名 → Enumerable.Empty<类型>()（返回 IEnumerable<类型> 空序列）
                //   用于验证 MaterialType.Set("MaterialTypePropertyTypes", IEnumerable<T>) 等只接受枚举、
                //   不接受 List<>/数组 的属性。空枚举先确认 T，再配合 Add 元素。
                if (s.StartsWith("@empty:"))
                {
                    var emptyObj = TryParseEmptyArg(s.Substring("@empty:".Length).Trim());
                    if (emptyObj != null)
                        return emptyObj;
                    return s; // 解析失败保持原样
                }

                // ---------- 数组（T[]）---------
                // @array:类型全名@obj1,@obj2  → T[] 数组（元素为已解析对象，可含多个）
                // 用于 Set 到只接受数组、不接受 List<>/IEnumerable 的属性。
                if (s.StartsWith("@array:"))
                {
                    var arrObj = TryParseArrayArg(s.Substring("@array:".Length).Trim());
                    if (arrObj != null)
                        return arrObj;
                    return s; // 解析失败保持原样
                }

                // ---------- 字典 ----------
                if (s.StartsWith("@dict:"))
                {
                    var jsonPart = s.Substring("@dict:".Length);
                    if (TryParseDict(jsonPart, out var dictResult))
                        return dictResult;
                    return s; // 解析失败保持原样
                }

                // @ 前缀且命中缓存（老格式 @obj10 / @obj225）
                if (s.StartsWith("@") && _objectStore.ContainsKey(s))
                {
                    var resolved = _objectStore[s];
                    // 对 RuntimeType 对象，保持为字符串引用而不是提前解析
                    // 这样泛型方法匹配时能识别第一参为类型名字符串
                    if (resolved is Type)
                        return s;
                    return resolved;
                }

                // ===== 无标识 → 自动猜测兜底（兼容老调用）=====
                if (int.TryParse(s, out int i)) return i;
                if (bool.TryParse(s, out bool b)) return b;
                if (float.TryParse(s, out float f)) return f;
                // 尝试将节点路径解析为节点对象
                // ★ 修复: { 开头的绑定表达式(如 {#Info/warning.value} 或 {A = #Info/warning.value\nA})
                //   含 "/" 但不 s 是节点路径, 若拿去 GetNodeByPath 会被吞成 null,
                //   导致 CreateBinding 的 code 参数丢失。{ 开头一律按字符串处理。
                if (!s.StartsWith("@") && !s.StartsWith("{") && s.Contains("/"))
                {
                    try { return GetNodeByPath(s); }
                    catch { }
                }
                return s;
            }

            // Dictionary<string, object> → Dictionary<string, int> 转换（用于 CreateCustomEnumProperty 的 options 参数）
            if (a is System.Collections.IDictionary dict)
            {
                var result = new Dictionary<string, int>();
                foreach (var key in dict.Keys)
                {
                    if (key is string skey)
                    {
                        object val = dict[skey];
                        if (val is int ival)
                            result[skey] = ival;
                        else if (val is string sval && int.TryParse(sval, out ival))
                            result[skey] = ival;
                        else
                            result[skey] = 0;
                    }
                }
                return result;
            }

            return a;
        }

        // ================ v4 参数标识辅助方法 ================

        /// <summary>解析带前缀的标量，解析失败返回原字符串（避免误吞）。</summary>
        private static object ParseOr<T>(string s, string prefix, TryParse<T> tryParse, Func<T, object> build)
        {
            if (tryParse(s.Substring(prefix.Length), out var v))
                return build(v);
            return s;
        }
        private delegate bool TryParse<T>(string s, out T value);

        /// <summary>解析 @vector:0,0 → System.Windows.Vector。格式："," 分隔的 x,y。</summary>
        private static object ParseVector(string body)
        {
            var parts = body.Split(',');
            if (parts.Length < 2) return null;
            if (double.TryParse(parts[0].Trim(), out double x) && double.TryParse(parts[1].Trim(), out double y))
            {
                var vecType = ResolveTypeByName("System.Windows.Vector");
                if (vecType != null)
                {
                    try
                    {
                        return Activator.CreateInstance(vecType, new object[] { x, y });
                    }
                    catch { }
                }
                // 兜底：返回 null 字符串，交给后续库查询/调用方处理
            }
            return null;
        }

        /// <summary>解析 @vector3d:0,0,0 → System.Windows.Media.Media3D.Vector3D。格式："," 分隔。</summary>
        /// <summary>解析 @transformation2d:1,1,0,0,115 → Rightware.Kanzi.Studio.PluginInterface.Transformation2D（\",\" 分隔，5 个 double）。</summary>
        /// <remarks>
        /// 格式：scaleX,scaleY,rotation,tx,ty。对应构造函数 (System.Windows.Vector scale, double rotation, System.Windows.Vector translation)。
        /// 即 scale=(scaleX,scaleY)、rotation、translation=(tx,ty)。
        /// 用于 Node2D.RenderTransformation 等只接受 Transformation2D 类型值的属性。
        /// 构造函数签名已由 PluginInterface.dll 反编译确认（非猜测）。
        /// </remarks>
        private static object ParseTransformation2D(string body)
        {
            var parts = body.Split(',');
            if (parts.Length < 5) return null;
            if (double.TryParse(parts[0].Trim(), out double scaleX)
                && double.TryParse(parts[1].Trim(), out double scaleY)
                && double.TryParse(parts[2].Trim(), out double rotation)
                && double.TryParse(parts[3].Trim(), out double tx)
                && double.TryParse(parts[4].Trim(), out double ty))
            {
                var t2dType = ResolveTypeByName("Rightware.Kanzi.Studio.PluginInterface.Transformation2D");
                var vecType = ResolveTypeByName("System.Windows.Vector");
                if (t2dType != null && vecType != null)
                {
                    try
                    {
                        var scale = Activator.CreateInstance(vecType, new object[] { scaleX, scaleY });
                        var translation = Activator.CreateInstance(vecType, new object[] { tx, ty });
                        return Activator.CreateInstance(t2dType, new object[] { scale, rotation, translation });
                    }
                    catch { }
                }
            }
            return null;
        }

        private static object ParseVector3D(string body)
        {
            var parts = body.Split(',');
            if (parts.Length < 3) return null;
            if (double.TryParse(parts[0].Trim(), out double x)
                && double.TryParse(parts[1].Trim(), out double y)
                && double.TryParse(parts[2].Trim(), out double z))
            {
                var vecType = ResolveTypeByName("System.Windows.Media.Media3D.Vector3D");
                if (vecType != null)
                {
                    try
                    {
                        return Activator.CreateInstance(vecType, new object[] { x, y, z });
                    }
                    catch { }
                }
            }
            return null;
        }

        /// <summary>解析 @quaternion:x,y,z,w → System.Windows.Media.Media3D.Quaternion。</summary>
        private static object ParseQuaternion(string body)
        {
            var parts = body.Split(',');
            if (parts.Length < 4) return null;
            if (double.TryParse(parts[0].Trim(), out double x)
                && double.TryParse(parts[1].Trim(), out double y)
                && double.TryParse(parts[2].Trim(), out double z)
                && double.TryParse(parts[3].Trim(), out double w))
            {
                var qType = ResolveTypeByName("System.Windows.Media.Media3D.Quaternion");
                if (qType != null)
                {
                    try
                    {
                        return Activator.CreateInstance(qType, new object[] { x, y, z, w });
                    }
                    catch { }
                }
            }
            return null;
        }

        /// <summary>
        /// 解析 @color:AARRGGBB / @color:RRGGBB → System.Windows.Media.Color。
        /// WPF Color 是 struct（无公开构造器），用静态工厂 Color.FromArgb(a,r,g,b) 构造。
        /// 支持 8 位 AARRGGBB 或 6 位 RRGGBB（A 默认 255）。16进制前缀 # 可有可无。
        /// 用于 Set("ColorBrush.Color", "@color:#FF9BA014") 等只接受 Color 值的属性。
        /// </summary>
        private static object ParseColor(string body)
        {
            var hex = (body ?? "").Trim();
            if (hex.StartsWith("#")) hex = hex.Substring(1);
            if (hex.Length != 6 && hex.Length != 8) return null;
            try
            {
                byte a = 255, r, g, b;
                if (hex.Length == 8)
                {
                    a = byte.Parse(hex.Substring(0, 2), System.Globalization.NumberStyles.HexNumber);
                    r = byte.Parse(hex.Substring(2, 2), System.Globalization.NumberStyles.HexNumber);
                    g = byte.Parse(hex.Substring(4, 2), System.Globalization.NumberStyles.HexNumber);
                    b = byte.Parse(hex.Substring(6, 2), System.Globalization.NumberStyles.HexNumber);
                }
                else
                {
                    r = byte.Parse(hex.Substring(0, 2), System.Globalization.NumberStyles.HexNumber);
                    g = byte.Parse(hex.Substring(2, 2), System.Globalization.NumberStyles.HexNumber);
                    b = byte.Parse(hex.Substring(4, 2), System.Globalization.NumberStyles.HexNumber);
                }
                // 调 System.Windows.Media.Color.FromArgb(byte a, byte r, byte g, byte b) 静态方法构造
                var colorType = ResolveTypeByName("System.Windows.Media.Color");
                if (colorType != null)
                {
                    var m = colorType.GetMethod("FromArgb", new[] { typeof(byte), typeof(byte), typeof(byte), typeof(byte) });
                    if (m != null && m.IsStatic)
                        return m.Invoke(null, new object[] { a, r, g, b });
                }
            }
            catch { }
            return null;
        }

        /// <summary>
        /// 解析 @dict: 前缀后的内容 → Dictionary&lt;string,int&gt;。
        /// 支持逗号分隔的 k=v 格式：@dict:Level0=0,Level1=1,Level2=2
        ///（MCP args 里真正的 JSON 对象 {…} 会先被反序列化成 IDictionary，由上部已有分支处理）
        /// 解析失败返回 false（调用方保留原字符串）。
        /// </summary>
        private bool TryParseDict(string body, out Dictionary<string, int> dict)
        {
            dict = null;
            if (string.IsNullOrWhiteSpace(body)) return false;
            try
            {
                var result = new Dictionary<string, int>();
                foreach (var pair in body.Split(','))
                {
                    var idx = pair.IndexOf('=');
                    if (idx < 0) return false;
                    var key = pair.Substring(0, idx).Trim();
                    var valStr = pair.Substring(idx + 1).Trim();
                    if (key.Length == 0) return false;
                    if (int.TryParse(valStr, out int ival))
                        result[key] = ival;
                    else
                        return false;
                }
                if (result.Count == 0) return false;
                dict = result;
                return true;
            }
            catch { return false; }
        }

        /// <summary>
        /// 解析 @list: 前缀后的内容 → List&lt;T&gt;。<br/>
        /// 格式：<c>@list:类型名@obj1,@obj2</c>（元素为对象引用）或
        /// <c>@list:@obj1,@obj2</c>（无类型名 → List&lt;object&gt;）。<br/>
        /// 类型名是“第一个 @ 之前”的部分（可为空），元素以逗号分隔。
        /// 用于给 FontFiles 这类 List 集合属性赋值（文档：Set(FontFiles, List&lt;FontFile&gt;)）。
        /// 解析失败返回 null（调用方保留原字符串）。
        /// </summary>
        private object TryParseListArg(string body)
        {
            if (string.IsNullOrWhiteSpace(body)) return null;
            try
            {
                // 分离“类型名”与“元素列表”：类型名 = 第一个 @ 之前的部分（可为空）
                int atIdx = body.IndexOf('@');
                string typeName = atIdx < 0 ? "" : body.Substring(0, atIdx).Trim();
                string elemsPart = atIdx < 0 ? body : body.Substring(atIdx);
                var elems = elemsPart.Split(',');

                var items = new List<object>();
                foreach (var e in elems)
                {
                    var raw = e.Trim();
                    if (raw.Length == 0) continue;
                    object el = ResolveListElement(raw);
                    if (el != null) items.Add(el);
                }
                if (items.Count == 0 && elems.Length == 1) return null; // 无任何有效元素

                Type elemType = null;
                if (!string.IsNullOrEmpty(typeName))
                    elemType = ResolveTypeByName(typeName);
                if (elemType == null) elemType = typeof(object);

                var listType = typeof(List<>).MakeGenericType(elemType);
                var list = Activator.CreateInstance(listType);
                var addM = listType.GetMethod("Add");
                foreach (var it in items)
                {
                    object converted = it;
                    if (elemType != typeof(object) && it != null && !elemType.IsInstanceOfType(it))
                    {
                        try
                        {
                            // 元素引用是已登记对象（非原始类型）时，尝试按接口/实现类型转换
                            if (elemType.IsInterface || elemType.IsAssignableFrom(it.GetType()))
                                converted = it; // 实现类型可直接赋给接口
                            else
                                converted = Convert.ChangeType(it, elemType);
                        }
                        catch { converted = it; }
                    }
                    try { addM.Invoke(list, new[] { converted }); } catch { }
                }
                return list;
            }
            catch { return null; }
        }

        /// <summary>
        /// 解析 @empty:类型全名 → Enumerable.Empty<类型>()（可枚举空序列）。
        ///   返回 IEnumerable<类型>，用于 Set 到只接受枚举、不接受 List<>/数组的属性（如 MaterialType 的 MaterialTypePropertyTypes）。
        ///   类型解析失败则返回 null，由调用方保持原字符串。
        /// </summary>
        private object TryParseEmptyArg(string typeName)
        {
            if (string.IsNullOrWhiteSpace(typeName)) return null;
            try
            {
                var type = ResolveTypeByName(typeName);
                if (type == null) return null;
                var emptyMethod = typeof(Enumerable).GetMethod("Empty").MakeGenericMethod(type);
                return emptyMethod.Invoke(null, null);
            }
            catch { return null; }
        }

        /// <summary>
        /// 解析 @array:类型全名@obj1,@obj2 → T[] 数组。
        ///   元素用 ResolveListElement 解析（@obj 引用还原为实际对象）。返回 T[]；解析失败返回 null。
        /// </summary>
        private object TryParseArrayArg(string body)
        {
            if (string.IsNullOrWhiteSpace(body)) return null;
            try
            {
                int atIdx = body.IndexOf('@');
                string typeName = atIdx < 0 ? "" : body.Substring(0, atIdx).Trim();
                string elemsPart = atIdx < 0 ? body : body.Substring(atIdx);
                var elems = elemsPart.Split(',');
                var items = new List<object>();
                foreach (var e in elems)
                {
                    var raw = e.Trim();
                    if (raw.Length == 0) continue;
                    object el = ResolveListElement(raw);
                    if (el != null) items.Add(el);
                }
                if (items.Count == 0) return null;

                Type elemType = null;
                if (!string.IsNullOrEmpty(typeName))
                    elemType = ResolveTypeByName(typeName);
                if (elemType == null) elemType = typeof(object);

                var arr = Array.CreateInstance(elemType, items.Count);
                for (int i = 0; i < items.Count; i++)
                {
                    object it = items[i];
                    object converted = it;
                    if (elemType != typeof(object) && it != null && !elemType.IsInstanceOfType(it))
                    {
                        try
                        {
                            if (elemType.IsInterface || elemType.IsAssignableFrom(it.GetType()))
                                converted = it;
                            else
                                converted = Convert.ChangeType(it, elemType);
                        }
                        catch { converted = it; }
                    }
                    try { arr.SetValue(converted, i); } catch { }
                }
                return arr;
            }
            catch { return null; }
        }

        /// <summary>
        /// 解析 @list: 里的单个元素。支持：
        ///   - @objNNN（已登记对象引用）→ 还原为实际对象
        ///   - @string:xxx → 字符串
        ///   - 数值/布尔 → 基础类型
        ///   其余按字符串原样返回。
        /// </summary>
        private object ResolveListElement(string raw)
        {
            if (raw.StartsWith("@obj") && _objectStore.ContainsKey(raw))
            {
                var r = _objectStore[raw];
                // 对 Type 对象保持字符串引用（与 ResolveSingleArg 一致）
                return (r is Type) ? raw : r;
            }
            if (raw.StartsWith("@string:")) return raw.Substring("@string:".Length);
            if (int.TryParse(raw, out int ii)) return ii;
            if (bool.TryParse(raw, out bool bb)) return bb;
            if (float.TryParse(raw, out float ff)) return ff;
            return raw;
        }

        /// <summary>
        /// @enum:NAME 的标记对象。
        /// ResolveSingleArg 把 @enum: 前缀解析成 EnumTag，
        /// FindEnumMethod 根据目标方法参数类型对该枚举名做精准 Enum.Parse。
        /// </summary>
        private sealed class EnumTag
        {
            public string Name { get; }
            public EnumTag(string name) { Name = name; }
        }

        /// <summary>
        /// 把类型名字符串解析为 .NET Type 对象。支持：
        ///   - 内置类型短名：string/int/long/float/double/decimal/bool/byte/char/object/void
        ///   - 全名/程序集名：System.String、System.Int32、System.Collections.Generic.List`1[System.String]
        ///   - 已加载程序集命名空间搜索（含 Kanzi 相关程序集）
        /// 解析失败返回 null（调用方保留原字符串）。
        /// </summary>
        /// <summary>
        /// 统一的类型名 → .NET Type 解析器。
        /// 不区分“内置 / Kanzi / 数学”类型，一套规则搞定所有：
        ///   1. 内置 CLR 短名（string/int/float/bool/Vector 等别名）
        ///   2. Kanzi Studio PluginInterface 类型（StateManager/State/Binding...）
        ///   3. 程序集限定名 / 全限定名（Type.GetType）
        ///   4. 在所有已加载程序集里按类型名（短名/全名）搜索（含 Kanzi 数学类型如 Vector2/Vector3/Vector3D）
        /// 解析失败返回 null。
        /// </summary>
        private static Type ResolveTypeByName(string typeName)
        {
            if (string.IsNullOrEmpty(typeName)) return null;

            var trimmed = typeName.Trim();
            var lower = trimmed.ToLowerInvariant();

            // ---- 1. 内置 CLR 类型短名映射 ----
            var builtin = new Dictionary<string, Type>(StringComparer.OrdinalIgnoreCase)
            {
                ["string"] = typeof(string),
                ["int"] = typeof(int),
                ["integer"] = typeof(int),
                ["int32"] = typeof(int),
                ["long"] = typeof(long),
                ["int64"] = typeof(long),
                ["short"] = typeof(short),
                ["int16"] = typeof(short),
                ["byte"] = typeof(byte),
                ["sbyte"] = typeof(sbyte),
                ["float"] = typeof(float),
                ["single"] = typeof(float),
                ["double"] = typeof(double),
                ["decimal"] = typeof(decimal),
                ["bool"] = typeof(bool),
                ["boolean"] = typeof(bool),
                ["char"] = typeof(char),
                ["object"] = typeof(object),
                ["void"] = typeof(void),
                ["system.string"] = typeof(string),
                ["system.int32"] = typeof(int),
                ["system.int64"] = typeof(long),
                ["system.single"] = typeof(float),
                ["system.double"] = typeof(double),
                ["system.boolean"] = typeof(bool),
                ["system.object"] = typeof(object),
            };
            if (builtin.TryGetValue(lower, out var bt)) return bt;

            // ---- 2. Kanzi Studio PluginInterface 类型----
            var kanziMap = new Dictionary<string, Type>(StringComparer.OrdinalIgnoreCase)
            {
                ["statemanager"] = typeof(Rightware.Kanzi.Studio.PluginInterface.StateManager),
                ["stategroup"] = typeof(Rightware.Kanzi.Studio.PluginInterface.StateGroup),
                ["state"] = typeof(Rightware.Kanzi.Studio.PluginInterface.State),
                ["stateobject"] = typeof(Rightware.Kanzi.Studio.PluginInterface.StateObject),
                ["statetransition"] = typeof(Rightware.Kanzi.Studio.PluginInterface.StateTransition),
                ["binding"] = typeof(Rightware.Kanzi.Studio.PluginInterface.Binding),
                ["bindinghost"] = typeof(Rightware.Kanzi.Studio.PluginInterface.BindingHost),
            };
            if (kanziMap.TryGetValue(lower, out var kt)) return kt;

            // ---- 3. 程序集限定名 / 全限定名 ----
            try
            {
                var t = Type.GetType(trimmed);
                if (t != null) return t;
            }
            catch { }

            // ---- 4. 已加载程序集里按全名 / 短名搜索（含 Kanzi 数学类型 Vector2/Vector3/Vector3D 等）----
            try
            {
                foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    try
                    {
                        // 全限定名在指定程序集中查一次
                        var t = asm.GetType(trimmed, false, true);
                        if (t != null) return t;

                        // 短名：遍历该程序集所有公开类型，匹配 短名 或 全名(忽略大小写)
                        if (!trimmed.Contains('.'))
                        {
                            Type matched = null;
                            foreach (var cand in asm.GetExportedTypes())
                            {
                                if (string.Equals(cand.Name, trimmed, StringComparison.OrdinalIgnoreCase)
                                    || string.Equals(cand.FullName, trimmed, StringComparison.OrdinalIgnoreCase))
                                {
                                    matched = cand;
                                    break;
                                }
                            }
                            if (matched != null) return matched;
                        }
                    }
                    catch { }
                }
            }
            catch { }

            return null;
        }

        private static bool IsNumericConversion(Type from, Type to)
        {
            var numericTypes = new[] { typeof(int), typeof(long), typeof(float), typeof(double), typeof(decimal) };
            return numericTypes.Contains(from) && numericTypes.Contains(to);
        }

        private object WrapResult(object result)
        {
            if (result == null) return null;
            var t = result.GetType();
            if (result is string || result is int || result is long || result is float
                || result is double || result is decimal || result is bool)
                return result;
            if (t.IsEnum)
                return result.ToString();
            // 资源字典（ResourceDictionary）本身是可枚举集合（IEnumerable<KeyValuePair<...>>），
            // 但它是需要作为对象引用的单个实体（用户要拿到它来调用 CreateResourceEntry 等）。
            // 若不特判，空字典会被当成空集合展开 → 丢失对象 ref（表现为返回空 text）。
            if (t.Name.Contains("ResourceDictionary"))
            {
                var rdRefId = RegisterObject(result);
                string rdName;
                try
                {
                    var rdNameProp = t.GetProperty("Name", BindingFlags.Public | BindingFlags.Instance);
                    rdName = rdNameProp?.GetValue(result)?.ToString() ?? result.ToString();
                }
                catch { rdName = result.ToString(); }
                return new Dictionary<string, object>
                {
                    ["ref_id"] = rdRefId,
                    ["type"] = t.Name,
                    ["fullType"] = t.FullName,
                    ["name"] = rdName
                };
            }
            if (result is IEnumerable enumerable && !(result is string))
            {
                var list = new List<object>();
                foreach (var item in enumerable)
                    list.Add(WrapResult(item));
                return list;
            }
            // KeyValuePair 的 ToString() 会把 key 中的中文转成 \uXXXX，用反射取 Key/Value 值
            string name;
            if (t.IsGenericType && t.GetGenericTypeDefinition() == typeof(KeyValuePair<,>))
            {
                var keyProp = t.GetProperty("Key");
                var valProp = t.GetProperty("Value");
                var keyVal = keyProp?.GetValue(result)?.ToString() ?? "";
                var valVal = valProp?.GetValue(result)?.ToString() ?? "";
                name = "[" + keyVal + ", " + valVal + "]";
                var kvRefId = RegisterObject(result);
                return new Dictionary<string, object>
                {
                    ["ref_id"] = kvRefId,
                    ["type"] = t.Name,
                    ["fullType"] = t.FullName,
                    ["name"] = name
                };
            }

            var refId = RegisterObject(result);
            try
            {
                var nameProp = t.GetProperty("Name", BindingFlags.Public | BindingFlags.Instance);
                name = nameProp?.GetValue(result)?.ToString() ?? result.ToString();
            }
            catch
            {
                name = result.ToString();
            }
            return new Dictionary<string, object>
            {
                ["ref_id"] = refId,
                ["type"] = t.Name,
                ["fullType"] = t.FullName,
                ["name"] = name
            };
        }

        #endregion 通用反射调用

        #region 便捷操作（纯反射实现）


        private static string GetDictStr(Dictionary<string, object> d, string key)
        {
            return d.TryGetValue(key, out var v) ? v?.ToString() : null;
        }

        /// <summary>无参构造 LocalizationTableRow 后，通过属性填充（兜底：仅 ResourceName；Translations 若可写则填）</summary>
        private static void PopulateRowByReflection(object rowObj, string resourceName, Dictionary<string, string> translations)
        {
            var t = rowObj.GetType();
            var resNameSetter = t.GetProperty("ResourceName")?.GetSetMethod() ?? t.GetMethod("set_ResourceName");
            if (resNameSetter != null) resNameSetter.Invoke(rowObj, new object[] { resourceName ?? "" });

            var transSetter = t.GetProperty("Translations")?.GetSetMethod() ?? t.GetMethod("set_Translations");
            var translationsField = t.GetField("Translations");
            if (transSetter != null)
                transSetter.Invoke(rowObj, new object[] { translations });
            else if (translationsField != null && translationsField.FieldType.IsAssignableFrom(translations.GetType()))
                translationsField.SetValue(rowObj, translations);
        }

        /// <summary>反射加载指定全名类型（不缓存，遵守全反射规则）</summary>

        /// <summary>反射加载指定全名类型（不缓存，遵守全反射规则）</summary>
        private static Type LoadTypeByFullName(string fullName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(fullName);
                if (t != null) return t;
            }
            return Type.GetType(fullName);
        }

        private static bool IsDictionaryCompatible(Type t)
        {
            if (t == typeof(IDictionary<string, string>)) return true;
            return t.IsGenericType && typeof(IDictionary<,>).IsAssignableFrom(t.GetGenericTypeDefinition());
        }

        private static bool IsEnumerableCompatible(Type t)
        {
            return t == typeof(IEnumerable) || (t.IsGenericType && (t.GetGenericTypeDefinition() == typeof(IEnumerable<>)
                || typeof(IEnumerable<>).IsAssignableFrom(t)));
        }

        /// <summary>构造指定类型的 Dictionary<string,string>（兼容非泛型/具体实现）</summary>
        private static object CreateDictionaryOfStringString(Dictionary<string, string> src, Type dictType)
        {
            if (dictType == typeof(Dictionary<string, string>))
                return new Dictionary<string, string>(src);
            // 尝试 Activator 创建并逐个 Add
            if (dictType.IsGenericType && dictType.GetGenericArguments().Length == 2)
            {
                try
                {
                    var inst = Activator.CreateInstance(dictType);
                    var add = dictType.GetMethod("Add", new[] { typeof(string), typeof(string) });
                    if (add != null)
                    {
                        foreach (var kv in src) add.Invoke(inst, new object[] { kv.Key, kv.Value });
                        return inst;
                    }
                }
                catch { }
            }
            return src;
        }

        private static object ConvertListToEnumerable(IList list, Type targetType)
        {
            if (targetType.IsGenericType)
            {
                var elem = targetType.GetGenericArguments()[0];
                try
                {
                    var arr = Array.CreateInstance(elem, list.Count);
                    for (int i = 0; i < list.Count; i++) arr.SetValue(list[i], i);
                    if (targetType.IsAssignableFrom(arr.GetType())) return arr;
                    var listT = typeof(List<>).MakeGenericType(elem);
                    var lst = Activator.CreateInstance(listT) as IList;
                    foreach (var it in list) lst.Add(it);
                    return lst;
                }
                catch { }
            }
            return list;
        }

        /// <summary>
        /// 创建节点 — 纯反射
        /// </summary>
        public string CreateNode(string parentPath, string nodeType, string name)
        {
            if (_project == null)
                throw new InvalidOperationException("没有打开的工程");

            var parent = GetNodeByPath(parentPath);
            if (parent == null)
                throw new InvalidOperationException($"父节点 '{parentPath}' 不存在");

            // 策略1: 先尝试 CreateComponentNode（适用于 ComponentTypeLibrary 中的类型）
            var compType = FindComponentType(nodeType);
            if (compType != null)
            {
                try
                {
                    var result = Invoke("@project", "CreateComponentNode",
                        new object[] { name, parent, compType });
                    if (result != null)
                    {
                        if (result is string msgStr)
                            return msgStr;
                        if (result is IDictionary dict && dict.Contains("ref_id"))
                            return dict["ref_id"].ToString();
                        try { return GetNodePath(result); } catch { }
                        return result.ToString();
                    }
                }
                catch { }
            }

            // 策略2: CreateProjectItem<T>(name, parent) — 视觉节点 / 状态机类型
            // 通过 @project 的泛型方法创建，args: [typeName, name, parent]
            object projectItemResult = null;
            try
            {
                projectItemResult = Invoke("@project", "CreateProjectItem",
                    new object[] { nodeType, name, parent });
            }
            catch { }

            // 策略2b: 如果泛型 Invoke 失败，手动构造泛型方法并调用
            if (projectItemResult == null)
            {
                projectItemResult = TryCreateByManualGeneric(nodeType, name, parent);
            }

            // 策略3: 对于 StateManager 等库级类型，通过 StateManagerLibrary 创建
            if (projectItemResult == null && string.Equals(nodeType, "StateManager", StringComparison.OrdinalIgnoreCase))
            {
                try
                {
                    projectItemResult = CreateStateManagerViaLibrary(name, parent);
                }
                catch { }
            }

            if (projectItemResult != null)
            {
                if (projectItemResult is string msgStr)
                    return msgStr;
                if (projectItemResult is IDictionary dict && dict.Contains("ref_id"))
                    return dict["ref_id"].ToString();
                try { return GetNodePath(projectItemResult); } catch { }
                return projectItemResult.ToString();
            }

            throw new InvalidOperationException("创建节点失败: 不支持的节点类型或方法");
        }

        /// <summary>
        /// 设置节点属性值 — 纯反射
        /// </summary>
        public void SetProperty(string nodePath, string propertyName, object value)
        {
            var node = GetNodeByPath(nodePath);
            if (node == null)
                throw new InvalidOperationException($"节点 '{nodePath}' 不存在");

            object finalValue = ConvertValue(value);
            CallNodeMethod(node, "Set", new object[] { propertyName, finalValue });
        }

        /// <summary>
        /// 获取节点属性值 — 纯反射
        /// </summary>
        public object GetProperty(string nodePath, string propertyName)
        {
            var node = GetNodeByPath(nodePath);
            if (node == null)
                throw new InvalidOperationException($"节点 '{nodePath}' 不存在");
            var val = CallNodeMethod(node, "Get", new object[] { propertyName });
            return val?.ToString();
        }

        /// <summary>
        /// 删除节点 — 纯反射
        /// </summary>
        public void DeleteNode(string nodePath)
        {
            var node = GetNodeByPath(nodePath);
            if (node == null)
                throw new InvalidOperationException($"节点 '{nodePath}' 不存在");

            var deleteMethod = FindMethod(node.GetType(), "Delete", Type.EmptyTypes);
            if (deleteMethod == null)
                throw new InvalidOperationException($"节点类型 {node.GetType().Name} 上没有 Delete 方法");
            try
            {
                deleteMethod.Invoke(node, null);
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException($"删除节点失败: {ex.Message}");
            }
        }

        /// <summary>
        /// 获取节点树 — 纯反射
        /// </summary>
        public object GetNodeTree(string rootPath = null)
        {
            object root;
            if (string.IsNullOrEmpty(rootPath) || rootPath == "/")
                root = GetRootNode();
            else
            {
                root = GetNodeByPath(rootPath);
                if (root == null)
                    throw new InvalidOperationException($"根节点 '{rootPath}' 不存在");
            }
            return SerializeNodeTree(root);
        }

        /// <summary>
        /// 获取节点类型列表 — 纯反射
        /// </summary>
        public string[] GetNodeTypes()
        {
            try
            {
                var typeLibProp = _projectType?.GetProperty("PropertyTypeLibrary");
                if (typeLibProp != null)
                {
                    var typeLib = typeLibProp.GetValue(_project);
                    if (typeLib != null)
                    {
                        var propTypesProp = typeLib.GetType().GetProperty("ProjectPropertyTypes");
                        if (propTypesProp != null)
                        {
                            var propTypes = propTypesProp.GetValue(typeLib) as IEnumerable;
                            if (propTypes != null)
                            {
                                var names = new List<string>();
                                foreach (var pt in propTypes)
                                {
                                    var nameProp = pt.GetType().GetProperty("Name");
                                    if (nameProp != null)
                                    {
                                        var name = nameProp.GetValue(pt)?.ToString();
                                        if (!string.IsNullOrEmpty(name) && name.EndsWith("2D"))
                                            names.Add(name);
                                    }
                                }
                                if (names.Count > 0)
                                    return names.OrderBy(n => n).ToArray();
                            }
                        }
                    }
                }
            }
            catch { }
            return new[] {
                "Button2D", "TextBlock2D", "Image2D", "Rectangle2D",
                "EmptyNode2D", "ScrollView2D", "ListView2D", "Slider2D",
                "ToggleButton2D", "TextBox2D", "ComboBox2D", "StackLayout2D",
                "GridLayout2D", "Canvas2D", "Video2D", "Mesh2D"
            };
        }

        /// <summary>
        /// 执行 Kanzi Studio 命令 — 纯反射
        /// </summary>
        public void ExecuteCommand(string commandName, object parameter = null)
        {
            try
            {
                var target = _projectItem ?? _project;
                if (target == null)
                    throw new InvalidOperationException("没有打开的工程");

                var targetType = target.GetType();

                // 查找 ExecutePluginCommand 方法 — 不限参数类型，用 GetMethods 全扫描
                MethodInfo execMethod = null;
                foreach (var m in targetType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.FlattenHierarchy))
                {
                    if (m.Name == "ExecutePluginCommand")
                    {
                        execMethod = m;
                        break;
                    }
                }

                // 如果目标类型上没有，查接口
                if (execMethod == null)
                {
                    foreach (var iface in targetType.GetInterfaces())
                    {
                        foreach (var m in iface.GetMethods(BindingFlags.Public | BindingFlags.Instance))
                        {
                            if (m.Name == "ExecutePluginCommand")
                            {
                                execMethod = m;
                                break;
                            }
                        }
                        if (execMethod != null) break;
                    }
                }

                if (execMethod != null)
                {
                    var ps = execMethod.GetParameters();
                    if (parameter != null && ps.Length >= 2)
                    {
                        var paramNode = GetNodeByPath(parameter.ToString());
                        var secondParamType = ps[1].ParameterType;
                        // 构建第二个参数，兼容 IEnumerable / object[] / IList 等
                        object secondArg;
                        if (secondParamType.IsArray)
                            secondArg = new object[] { paramNode };
                        else if (secondParamType.IsGenericType &&
                                 secondParamType.GetGenericTypeDefinition() == typeof(IEnumerable<>))
                            secondArg = new object[] { paramNode };
                        else
                            secondArg = new object[] { paramNode };

                        execMethod.Invoke(target, new object[] { commandName, secondArg });
                    }
                    else
                    {
                        execMethod.Invoke(target, new object[] { commandName });
                    }
                    return;
                }

                // Fallback: 找其他 Save 相关方法
                var saveMethod = FindMethod(targetType, "Save", Type.EmptyTypes);
                if (saveMethod != null)
                {
                    saveMethod.Invoke(target, null);
                    return;
                }

                throw new MissingMethodException($"在 {targetType.FullName} 上找不到 ExecutePluginCommand");
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException($"执行命令失败: {ex.Message}");
            }
        }

        /// <summary>
        /// 写日志到 Kanzi Studio 日志窗口
        /// </summary>
        public void Log(string message)
        {
            try
            {
                var method = typeof(KanziStudio).GetMethod("Log", new[] { typeof(string) });
                method?.Invoke(_studio, new[] { message });
            }
            catch { }
        }

        /// <summary>
        /// 显示消息框
        /// </summary>
        public void ShowMessage(string message, string title = "MCP Server")
        {
            try
            {
                var method = typeof(KanziStudio).GetMethod("ShowMessageBox",
                    new[] { typeof(string), typeof(string), typeof(bool) });
                method?.Invoke(_studio, new object[] { message, title, false });
            }
            catch { }
        }

        /// <summary>
        /// 保存工程 — 纯反射
        /// </summary>
        public void SaveProject()
        {
            if (_project == null)
                throw new InvalidOperationException("没有打开的工程");
            try
            {
                // 方法1: 在 _projectItem（WrappedItem，实际是 Project 类型）上找 Save 方法
                var target = _projectItem ?? _project;
                var targetType = target?.GetType();
                if (targetType != null)
                {
                    var saveMethod = FindMethod(targetType, "Save", Type.EmptyTypes);
                    if (saveMethod != null)
                    {
                        saveMethod.Invoke(target, null);
                        return;
                    }
                }

                // 方法2: 通过 KanziStudio 接口上的命令
                if (_projectItemType != null)
                {
                    var saveMethod2 = FindMethod(_projectItemType, "Save", Type.EmptyTypes);
                    if (saveMethod2 != null)
                    {
                        saveMethod2.Invoke(_projectItem, null);
                        return;
                    }
                }

                // 方法3: 尝试在 _projectType（ProjectPluginWrapper）上找 Save
                if (_projectType != null)
                {
                    var saveMethod3 = FindMethod(_projectType, "Save", Type.EmptyTypes);
                    if (saveMethod3 != null)
                    {
                        saveMethod3.Invoke(_project, null);
                        return;
                    }
                }

                // 方法4: ExecuteCommand fallback
                ExecuteCommand("Save");
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException($"保存工程失败: {ex.Message}");
            }
        }

        /// <summary>
        /// [V9 截图扩展] 抓取屏幕区域并返回 PNG 的 base64 字符串（不走文件共享，直接回传）。
        /// 纯反射实现（不直接引用 System.Drawing 具体类型），符合全反射铁律。
        /// 用于 Preview/Studio 截图验证。参数: x,y 左上角；w,h 宽高；默认截整屏。
        /// 为避免 base64 过大拖慢回传，默认缩放到最大边 maxSide（默认 800）；maxSide<=0 则保持原始尺寸。
        /// </summary>
        public object CaptureScreenBase64(int x, int y, int width, int height, int maxSide = 800)
        {
            // 解析需要用到的 System.Drawing 类型
            var bmpType = ResolveTypeByName("System.Drawing.Bitmap");
            var gfxType = ResolveTypeByName("System.Drawing.Graphics");
            var imgType = ResolveTypeByName("System.Drawing.Image");
            var sizeType = ResolveTypeByName("System.Drawing.Size");
            var imageFormatType = ResolveTypeByName("System.Drawing.Imaging.ImageFormat");
            if (bmpType == null || gfxType == null || sizeType == null || imgType == null)
                throw new TypeLoadException("System.Drawing 相关类型解析失败，截图不可用");

            // 全屏尺寸：若 width/height <=0 用屏幕大小
            // ⚠️ 必须用 Screen.PrimaryScreen.Bounds 的【物理像素】尺寸（4K 屏 3840x2160），
            //    不能用 SystemInformation.VirtualScreenWidth（DPI 缩放后返回逻辑尺寸 1920x1080，会截一半）。
            int w = width, h = height;
            if (w <= 0 || h <= 0)
            {
                try
                {
                    var screenType = ResolveTypeByName("System.Windows.Forms.Screen");
                    if (screenType != null)
                    {
                        var primaryProp = screenType.GetProperty("PrimaryScreen");
                        var primary = primaryProp?.GetValue(null, null);
                        if (primary != null)
                        {
                            var boundsProp = primary.GetType().GetProperty("Bounds");
                            var bounds = boundsProp?.GetValue(primary, null);
                            if (bounds != null)
                            {
                                var bw = bounds.GetType().GetProperty("Width");
                                var bh = bounds.GetType().GetProperty("Height");
                                if (bw != null && bh != null)
                                {
                                    w = (int)bw.GetValue(bounds, null);
                                    h = (int)bh.GetValue(bounds, null);
                                }
                            }
                        }
                    }
                    if (w <= 0 || h <= 0) { w = 1920; h = 1080; }
                }
                catch { if (w <= 0 || h <= 0) { w = 1920; h = 1080; } }
            }

            // new Bitmap(w, h)
            var bmp = Activator.CreateInstance(bmpType, new object[] { w, h });
            using (var ms = new System.IO.MemoryStream())
            {
                try
                {
                    // Graphics.FromImage(bitmap)
                    var gfx = gfxType.GetMethod("FromImage", new Type[] { bmpType }).Invoke(null, new object[] { bmp });

                    // gfx.CopyFromScreen(x, y, 0, 0, new Size(w, h))
                    var size = Activator.CreateInstance(sizeType, new object[] { w, h });
                    var cfm = gfxType.GetMethod("CopyFromScreen",
                        new Type[] { typeof(int), typeof(int), typeof(int), typeof(int), sizeType });
                    cfm.Invoke(gfx, new object[] { x, y, 0, 0, size });

                    // 释放 graphics（Flush + Dispose），确保像素写入
                    gfxType.GetMethod("Flush", Type.EmptyTypes)?.Invoke(gfx, null);
                    gfxType.GetMethod("Dispose", Type.EmptyTypes)?.Invoke(gfx, null);

                    // 需要保存/缩放的源图片对象
                    object saveImage = bmp;
                    int outW = w, outH = h;

                    // 可选：缩放到最大边 maxSide，控制 base64 体积
                    if (maxSide > 0 && (w > maxSide || h > maxSide))
                    {
                        double ratio = (double)maxSide / Math.Max(w, h);
                        outW = Math.Max(1, (int)(w * ratio));
                        outH = Math.Max(1, (int)(h * ratio));
                        var thumbType = ResolveTypeByName("System.Drawing.Bitmap");
                        var thumb = Activator.CreateInstance(thumbType, new object[] { outW, outH });
                        try
                        {
                            var tgfx = gfxType.GetMethod("FromImage", new Type[] { thumbType }).Invoke(null, new object[] { thumb });
                            // tgfx.InterpolationMode = HighQualityBicubic (可选，简化略)
                            var dr = gfxType.GetMethod("DrawImage", new Type[] { imgType,
                                typeof(int), typeof(int), typeof(int), typeof(int) });
                            dr.Invoke(tgfx, new object[] { bmp, 0, 0, outW, outH });
                            gfxType.GetMethod("Flush", Type.EmptyTypes)?.Invoke(tgfx, null);
                            gfxType.GetMethod("Dispose", Type.EmptyTypes)?.Invoke(tgfx, null);
                            saveImage = thumb;
                        }
                        catch { saveImage = bmp; }
                    }

                    // (saveImage).Save(ms, ImageFormat.Png)
                    var saveM = bmpType.GetMethod("Save", new Type[] { typeof(System.IO.Stream), imageFormatType });
                    var pngProp = imageFormatType.GetProperty("Png");
                    var png = pngProp?.GetValue(null, null);
                    saveM.Invoke(saveImage, new object[] { ms, png });

                    var bytes = ms.ToArray();
                    return new Dictionary<string, object>
                    {
                        ["width"] = outW,
                        ["height"] = outH,
                        ["srcW"] = w,
                        ["srcH"] = h,
                        ["mime"] = "image/png",
                        ["bytes"] = bytes.Length,
                        ["base64"] = System.Convert.ToBase64String(bytes)
                    };
                }
                finally
                {
                    bmpType.GetMethod("Dispose", Type.EmptyTypes)?.Invoke(bmp, null);
                }
            }
        }

        /// <summary>
        /// [V9 窗口枚举] 用 user32.EnumWindows + GetWindowThreadProcessId 找出指定 PID 的所有顶层窗口。
        /// 返回每个窗口的 HWND、类名、可见性、矩形(物理像素)。用于定位 Preview/Studio 的窗口（
        /// Process.MainWindowHandle 在远程/服务会话里常为 0，EnumWindows 才可靠）。
        /// 纯 P/Invoke，不依赖 Kanzi 类型。
        /// </summary>
        public object EnumProcessWindows(int pid)
        {
            var result = new List<object>();
            try
            {
                EnumWindows((hwnd, lParam) =>
                {
                    uint wpid;
                    GetWindowThreadProcessId(hwnd, out wpid);
                    if (wpid == (uint)pid)
                    {
                        var sb = new System.Text.StringBuilder(256);
                        GetClassName(hwnd, sb, sb.Capacity);
                        var cls = sb.ToString();
                        var visible = IsWindowVisible(hwnd);
                        RECT rc;
                        GetWindowRect(hwnd, out rc);
                        var tsb = new System.Text.StringBuilder(512);
                        GetWindowText(hwnd, tsb, tsb.Capacity);
                        var title = tsb.ToString();
                        result.Add(new Dictionary<string, object>
                        {
                            ["hwnd"] = (long)hwnd,
                            ["className"] = cls,
                            ["title"] = title,
                            ["visible"] = visible,
                            ["x"] = rc.Left,
                            ["y"] = rc.Top,
                            ["w"] = rc.Right - rc.Left,
                            ["h"] = rc.Bottom - rc.Top
                        });
                    }
                    return true;
                }, IntPtr.Zero);
            }
            catch (Exception ex)
            {
                return new Dictionary<string, object> { ["error"] = ex.Message };
            }
            return new Dictionary<string, object>
            {
                ["pid"] = pid,
                ["windows"] = result
            };
        }

        /// <summary>
        /// [V9 全窗口枚举] 不依赖 pid，枚举系统中所有顶层窗口并带 PID + 标题。
        /// 用于直接定位 Preview 拽出后的窗口（无需先拿 GetProcesses）。
        /// </summary>
        public object EnumAllWindowsWithTitle()
        {
            var result = new List<object>();
            try
            {
                EnumWindows((hwnd, lParam) =>
                {
                    uint wpid;
                    GetWindowThreadProcessId(hwnd, out wpid);
                    var sb = new System.Text.StringBuilder(256);
                    GetClassName(hwnd, sb, sb.Capacity);
                    var cls = sb.ToString();
                    var visible = IsWindowVisible(hwnd);
                    RECT rc;
                    GetWindowRect(hwnd, out rc);
                    var tsb = new System.Text.StringBuilder(512);
                    GetWindowText(hwnd, tsb, tsb.Capacity);
                    var title = tsb.ToString();
                    result.Add(new Dictionary<string, object>
                    {
                        ["pid"] = (int)wpid,
                        ["hwnd"] = (long)hwnd,
                        ["className"] = cls,
                        ["title"] = title,
                        ["visible"] = visible,
                        ["x"] = rc.Left,
                        ["y"] = rc.Top,
                        ["w"] = rc.Right - rc.Left,
                        ["h"] = rc.Bottom - rc.Top
                    });
                    return true;
                }, IntPtr.Zero);
            }
            catch (Exception ex)
            {
                return new Dictionary<string, object> { ["error"] = ex.Message };
            }
            return new Dictionary<string, object>
            {
                ["windows"] = result
            };
        }

        // ---- user32 P/Invoke ----
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder lpClassName, int nMaxCount);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);
        [StructLayout(LayoutKind.Sequential)]
        private struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
        [DllImport("user32.dll")]
        private static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        /// <summary>
        /// [V9 离屏窗口截图] 用 user32.PrintWindow 把指定 HWND 的窗口内容离屏渲染成图片（PNG base64）。
        /// 即使窗口被遮挡/不在前台也能截到（PrintWindow 走 WM_PRINT，非屏幕像素抓取）。
        /// 用于截被 MCP 面板遮挡的 Preview。配合 EnumProcessWindows 拿 HWND。
        /// 注意：对 OpenGL/DirectX 渲染(如 NVOpenGLPbuffer)可能抓不到 GPU 内容，需实测。
        /// </summary>
        public object PrintWindowBase64(long hwndInt, int maxSide = 0)
        {
            // 用后台线程执行 Core，避免 PrintWindow 在 UI 线程死锁/卡死插件；6s 超时强制返回
            object result = null;
            var task = System.Threading.Tasks.Task.Run(() => {
                result = PrintWindowCore(hwndInt, maxSide);
            });
            try
            {
                if (!task.Wait(TimeSpan.FromSeconds(6)))
                    return "❌ PrintWindow 超时(6s)，窗口可能无响应(OpenGL/离屏内容)";
                return result ?? "❌ PrintWindow 未返回结果";
            }
            catch (Exception ex)
            {
                return $"❌ PrintWindow 异常: {ex.Message}";
            }
        }

        private object PrintWindowCore(long hwndInt, int maxSide)
        {
            try
            {
                IntPtr hwnd = new IntPtr(hwndInt);
                RECT rc;
                if (!GetWindowRect(hwnd, out rc)) return "❌ GetWindowRect 失败，窗口无效";
                int w = rc.Right - rc.Left, h = rc.Bottom - rc.Top;
                if (w <= 0 || h <= 0) return $"❌ 窗口尺寸无效({w}x{h})";

                var bmpType = ResolveTypeByName("System.Drawing.Bitmap");
                var gfxType = ResolveTypeByName("System.Drawing.Graphics");
                var imgType = ResolveTypeByName("System.Drawing.Image");
                var sizeType = ResolveTypeByName("System.Drawing.Size");
                var imageFormatType = ResolveTypeByName("System.Drawing.Imaging.ImageFormat");
                var pngFormatProp = imageFormatType.GetProperty("Png");
                if (bmpType == null || gfxType == null || imgType == null || sizeType == null) throw new TypeLoadException("System.Drawing 类型解析失败");

                // new Bitmap(w, h)
                var bmp = Activator.CreateInstance(bmpType, new object[] { w, h });
                using (var ms = new System.IO.MemoryStream())
                {
                    // Graphics.FromImage(bmp)
                    var gfx = gfxType.GetMethod("FromImage", new Type[] { bmpType }).Invoke(null, new object[] { bmp });
                    // 用窗口 DC：GetWindowDC + BitBlt 或 PrintWindow
                    // 方式A：PrintWindow(hwnd, gdc, PW_RENDERFULLCONTENT=2)
                    var gdc = gfxType.GetMethod("GetHdc", Type.EmptyTypes).Invoke(gfx, null);
                    bool ok = PrintWindow(hwnd, (IntPtr)gdc, 2); // PW_RENDERFULLCONTENT
                    gfxType.GetMethod("ReleaseHdc", new Type[] { gdc.GetType() }).Invoke(gfx, new object[] { gdc });
                    if (!ok)
                    {
                        // 方式B：BitBlt 兜底（抓窗口 DC，需先 GetWindowDC）
                        var wdc = GetWindowDC(hwnd);
                        if (wdc == IntPtr.Zero) return "❌ PrintWindow 失败且 GetWindowDC 拿不到";
                        // 用 gfx 画位图拷贝（简化：把窗口DC内容 BitBlt 到 bmp）
                        // (此路径在 System.Drawing 反射下复杂，先报错让上层决定)
                        ReleaseDC(hwnd, wdc);
                        return "❌ PrintWindow 返回 false（OpenGL/离屏窗口可能不支持）";
                    }

                    gfxType.GetMethod("Flush", Type.EmptyTypes)?.Invoke(gfx, null);
                    gfxType.GetMethod("Dispose", Type.EmptyTypes)?.Invoke(gfx, null);

                    // 保存为 PNG base64
                    object saveImage = bmp;
                    if (maxSide > 0 && (w > maxSide || h > maxSide))
                    {
                        double ratio = (double)maxSide / Math.Max(w, h);
                        int outW = Math.Max(1, (int)(w * ratio)), outH = Math.Max(1, (int)(h * ratio));
                        var thumb = Activator.CreateInstance(bmpType, new object[] { outW, outH });
                        try {
                            var tgfx = gfxType.GetMethod("FromImage", new Type[] { bmpType }).Invoke(null, new object[] { thumb });
                            var dr = gfxType.GetMethod("DrawImage", new Type[] { imgType, typeof(int), typeof(int), typeof(int), typeof(int) });
                            dr.Invoke(tgfx, new object[] { bmp, 0, 0, outW, outH });
                            gfxType.GetMethod("Flush", Type.EmptyTypes)?.Invoke(tgfx, null);
                            gfxType.GetMethod("Dispose", Type.EmptyTypes)?.Invoke(tgfx, null);
                            saveImage = thumb;
                        } catch { saveImage = bmp; }
                    }

                    var saveMethod = bmpType.GetMethod("Save", new Type[] { typeof(System.IO.Stream), imageFormatType });
                    saveMethod.Invoke(saveImage, new object[] { ms, pngFormatProp.GetValue(null, null) });
                    var bytes = ms.ToArray();
                    var b64 = Convert.ToBase64String(bytes);
                    return new Dictionary<string, object>
                    {
                        ["hwnd"] = hwndInt, ["srcW"] = w, ["srcH"] = h,
                        ["printWindowOk"] = ok, ["mime"] = "image/png",
                        ["bytes"] = bytes.Length, ["base64"] = b64
                    };
                }
            }
            catch (Exception ex)
            {
                return $"❌ {ex.Message}";
            }
        }
        [DllImport("user32.dll")]
        private static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
        [DllImport("user32.dll")]
        private static extern IntPtr GetWindowDC(IntPtr hWnd);
        [DllImport("user32.dll")]
        private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

        /// <summary>
        /// [V9 智能截图] 一键截取 Preview；获取不到 Preview 则截 Studio 主窗。不截主屏幕。
        /// 判据：Preview 是 Studio 进程里可见、且 PrintWindow 截出内容最大的窗口（渲染画面信息量远大于普通 UI 窗口）。
        /// 若能从窗口 Title/className 直接命中 "Preview"，优先用它。
        /// </summary>
        public object SmartShotBase64(int studioPid, int maxSide = 1200)
        {
            try
            {
                // 1. 用全枚举（pid 准确）拿系统所有顶层窗口，再按 pid 过滤出 Studio 进程的窗口
                //    避免 EnumProcessWindows 的 pid 过滤 bug（会把别的进程窗口混进来）
                var enumObj = EnumAllWindowsWithTitle();
                var allWindows = new List<Dictionary<string, object>>();
                if (enumObj is Dictionary<string, object> ed && ed.ContainsKey("windows") && ed["windows"] is System.Collections.IList wl)
                {
                    foreach (var w in wl)
                        if (w is Dictionary<string, object> wd) allWindows.Add(wd);
                }
                var windows = new List<Dictionary<string, object>>();
                foreach (var w in allWindows)
                {
                    int pid = w.ContainsKey("pid") ? Convert.ToInt32(w["pid"]) : 0;
                    if (pid == studioPid) windows.Add(w);
                }
                if (windows.Count == 0)
                    return "❌ 未枚举到 Studio 窗口(pid=" + studioPid + ")";

                // 2. 有 Preview 就截 Preview：visible 且 title 含 preview （不区分大小写）
                Dictionary<string, object> previewWin = null;
                foreach (var w in windows)
                {
                    if (!(w.ContainsKey("visible") && (bool)w["visible"])) continue;
                    string title = (w.ContainsKey("title") ? w["title"] : "").ToString();
                    if (title.IndexOf("preview", StringComparison.OrdinalIgnoreCase) >= 0)
                    { previewWin = w; break; }
                }

                // 3. 没有 Preview 截 Studio 主窗：visible 且 title 含 kanzi studio
                Dictionary<string, object> studioWin = null;
                if (previewWin == null)
                {
                    foreach (var w in windows)
                    {
                        if (!(w.ContainsKey("visible") && (bool)w["visible"])) continue;
                        string title = (w.ContainsKey("title") ? w["title"] : "").ToString();
                        if (title.IndexOf("kanzi studio", StringComparison.OrdinalIgnoreCase) >= 0)
                        { studioWin = w; break; }
                    }
                }

                Dictionary<string, object> shotWin = previewWin != null ? previewWin : studioWin;
                if (shotWin == null)
                    return "❌ 未找到 Preview/Studio 窗口";

                // 4. 只对目标窗口 PrintWindow 一次（离屏，不截主屏幕）
                long shotHwnd = (long)shotWin["hwnd"];
                var rr = PrintWindowCore(shotHwnd, maxSide);
                if (!(rr is Dictionary<string, object> rd) || !rd.ContainsKey("base64"))
                    return "❌ 截图失败: " + (rr is string s ? s : "PrintWindow 未返回");

                bool isPreview = previewWin != null;
                return new Dictionary<string, object>
                {
                    ["target"] = isPreview ? "preview" : "studio",
                    ["hwnd"] = shotHwnd,
                    ["bytes"] = rd["bytes"],
                    ["srcW"] = rd["srcW"], ["srcH"] = rd["srcH"],
                    ["printWindowOk"] = rd.ContainsKey("printWindowOk") && (bool)rd["printWindowOk"],
                    ["mime"] = "image/png",
                    ["base64"] = rd["base64"]
                };
            }
            catch (Exception ex)
            {
                return $"❌ SmartShot: {ex.Message}";
            }
        }

        #endregion 便捷操作

        #region ModifyAnimation 关键帧编辑（纯反射实现，v10 新增）

        /// <summary>
        /// [v10] 给 Animation Data 加/改/删关键帧（驱动 Kanzi 命令总线的 ModifyAnimationCommand）。
        /// 方案乙：原子式——一条命令查动画→建参数→加/改/删帧→建命令记录→Execute 全做完。
        /// 但内部仍把中间对象（Parameter/ModifiedAnimationData/CommandRecord）注册进对象库并返回 @obj，
        /// 供后续 kz_invoke 继续操作（返回的 @obj 是真实对象引用，可直接用于后续调用）。
        ///
        /// action: add(加帧) | modify(改帧，按 time 定位) | remove(删帧，按 time 定位)
        /// keyframes: List&lt;object&gt;，每项是 Dictionary：{ time(float), value(必填), type(LINEAR/STEP/BEZIER/HERMITE，默认LINEAR) }
        /// animation: 目标 Animation Data 的路径 或 @obj 引用（AnimationPluginWrapper）
        /// </summary>
        public object ModifyAnimation(string animation, string action, object keyframes = null)
        {
            // ★ 全部 Kanzi 对象操作必须在 UI(Dispatcher) 线程，否则报“调用线程无法访问此对象”
            if (!IsUiThread())
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                {
                    return app.Dispatcher.Invoke(new Func<object>(() =>
                        ModifyAnimationCore(animation, action, keyframes)));
                }
            }
            return ModifyAnimationCore(animation, action, keyframes);
        }

        private object ModifyAnimationCore(string animation, string action, object keyframes)
        {
            action = (action ?? "").Trim().ToLowerInvariant();
            if (action != "add" && action != "modify" && action != "remove")
                throw new ArgumentException($"action 只能为 add/modify/remove，收到 '{action}'");

            // ---- 1. 解析目标动画 & 拿内部 Animation 对象（关键）----
            // 目标可能是路径或 @obj 引用（AnimationPluginWrapper）。ResolveObject 拿 wrapper。
            // 但 AddAnimation 需要的是【内部】Animation（Rightware.Kanzi.Tool.Logic.Project.AnimationItems.Animation）
            // —— wrapper 的 get_WrappedItem() 返回它。注意：不能用 Invoke（会把 Animation 当 IEnumerable 展开丢 ref），
            // 必须直接反射调用拿裸对象。
            if (string.IsNullOrEmpty(animation))
                throw new ArgumentException("animation 不能为空（传路径或 @obj 引用）");

            object wrapperObj;
            if (animation == "studio" || animation == "@studio") wrapperObj = _studio;
            else if (animation == "project" || animation == "@project") wrapperObj = _project;
            else wrapperObj = ResolveObject(animation);

            // 取内部 Animation：get_WrappedItem()（直扡反射，不经过 WrapResult）
            object internalAnim = GetWrappedItemRaw(wrapperObj);
            if (internalAnim == null)
                throw new InvalidOperationException($"无法从目标拿到内部 Animation 对象: '{animation}'");

            // ---- 2. 解析各类型（全反射，不引用具体类型）----
            var paramType = ResolveTypeByName("Rightware.Kanzi.Tool.Logic.Project.AnimationItems.Commands.ModifyAnimationCommandParameter");
            var interpType = ResolveTypeByName("Rightware.Kanzi.Tool.Logic.Project.AnimationItems.InterpolationType");
            var frameType  = ResolveTypeByName("Rightware.Kanzi.Tool.Logic.Project.AnimationItems.AnimationKeyFrame");
            var recordType = ResolveTypeByName("Rightware.Kanzi.Tool.Logic.Project.AnimationItems.Commands.ModifyAnimationCommandRecord");
            if (paramType == null || frameType == null || recordType == null)
                throw new InvalidOperationException("解析 ModifyAnimation 相关类型失败（LogicProject 未加载？）");

            // ---- 3. 建 ModifyAnimationCommandParameter（无参构造）----
            var param = Activator.CreateInstance(paramType);
            string paramRef = RegisterObject(param);

            // ---- 4. AddAnimation(内部Animation) → ModifiedAnimationData（注册 ref 供交互）----
            // AddAnimation 签名: ModifiedAnimationData AddAnimation(Animation)
            // ⚠️ 不能直接 GetMethod("AddAnimation")：若存在重载会抛 AmbiguousMatch。按参数类型精确定位 1 参版本。
            var addAnim = FindMethodByParamTypes(paramType, "AddAnimation", new[] { internalAnim.GetType() })
                          ?? FindMethodByParamCount(paramType, "AddAnimation", 1);
            if (addAnim == null) throw new MissingMethodException("ModifyAnimationCommandParameter 上找不到 AddAnimation(Animation)");
            var modifiedData = addAnim.Invoke(param, new object[] { internalAnim });
            if (modifiedData == null) throw new InvalidOperationException("AddAnimation 返回 null");
            string modifiedDataRef = RegisterObject(modifiedData);

            // 用于 remove：需要能按 time 构造一个只读参考帧传给 RemoveKeyframe。
            // remove 只需要 time（定位已有的帧），Value 可给默认。

            // ---- 5. 处理每个关键帧 ----
            var framesIn = new List<object>();
            if (keyframes is IEnumerable kfEnum)
                foreach (var kf in kfEnum) framesIn.Add(kf);
            else if (keyframes != null)
                framesIn.Add(keyframes);
            if (framesIn.Count == 0)
                throw new ArgumentException($"{action} 需要至少传一个 keyframes（[{{\"time\":1,\"value\":2, \"type\":\"LINEAR\"}}]）");

            var modifiedDataType = modifiedData.GetType();
            string methodName = action == "add" ? "AddKeyframe" : (action == "modify" ? "ModifyKeyframe" : "RemoveKeyframe");
            // ⚠️ 同样避免 GetMethod(name) 歧义（若存在重载）：按参数类型（AnimationKeyFrame）精确定位
            var kfMethod = FindMethodByParamTypes(modifiedDataType, methodName, new[] { frameType })
                          ?? FindMethodByParamCount(modifiedDataType, methodName, 1);
            if (kfMethod == null) throw new MissingMethodException($"ModifiedAnimationData 上找不到 {methodName}");

            var results = new List<object>();
            foreach (var kf in framesIn)
            {
                var dict = kf as Dictionary<string, object>;
                if (dict == null && kf is IDictionary id2)
                {
                    dict = new Dictionary<string, object>();
                    foreach (System.Collections.DictionaryEntry e in id2)
                        dict[e.Key?.ToString() ?? ""] = e.Value;
                }
                if (dict == null)
                {
                    // 允许直接传 { "time":.., "value":.. } 的字典；非字典则报错
                    throw new ArgumentException("keyframes 每项必须是对象 { time, value, type? }");
                }
                object frame = BuildAnimationKeyFrame(dict, frameType, interpType);
                string frameRef = RegisterObject(frame);

                object kfResult;
                try
                {
                    kfResult = kfMethod.Invoke(modifiedData, new object[] { frame });
                }
                catch (System.Reflection.TargetInvocationException tie)
                {
                    throw new InvalidOperationException($"{methodName}({DescribeFrame(dict)}) 失败: {tie.InnerException?.Message ?? tie.Message}");
                }
                results.Add(new Dictionary<string, object>
                {
                    ["frameRef"] = frameRef,
                    ["time"] = dict.ContainsKey("time") ? Convert.ToString(dict["time"]) : "",
                    ["value"] = dict.ContainsKey("value") ? Convert.ToString(dict["value"]) : "",
                    ["resultRef"] = kfResult != null ? RegisterObject(kfResult) : null
                });
            }

            // ---- 6. 建 ModifyAnimationCommandRecord(param) 并 Execute（真正执行修改）----
            // 构造器: .ctor(ModifyAnimationCommandParameter)
            var recordCtor = recordType.GetConstructor(new[] { paramType });
            if (recordCtor == null)
            {
                // 兜底：按参数可赋值匹配
                recordCtor = recordType.GetConstructors()
                    .FirstOrDefault(c => { var p = c.GetParameters(); return p.Length == 1 && p[0].ParameterType.IsAssignableFrom(paramType); });
            }
            if (recordCtor == null) throw new MissingMethodException("ModifyAnimationCommandRecord 上找不到接受 ModifyAnimationCommandParameter 的构造器");

            object record;
            try
            {
                record = recordCtor.Invoke(new object[] { param });
            }
            catch (System.Reflection.TargetInvocationException tie)
            {
                throw new InvalidOperationException($"创建 ModifyAnimationCommandRecord 失败: {tie.InnerException?.Message ?? tie.Message}");
            }
            string recordRef = RegisterObject(record);

            // Execute()：真正把改动写进动画（⚠️ 避免 GetMethod(name) 歧义：选无参版本）
            var execMethod = FindMethodByParamCount(recordType, "Execute", 0)
                          ?? recordType.GetMethod("Execute", Type.EmptyTypes);
            if (execMethod == null) throw new MissingMethodException("ModifyAnimationCommandRecord 上找不到 Execute");
            try
            {
                execMethod.Invoke(record, null);
            }
            catch (System.Reflection.TargetInvocationException tie)
            {
                throw new InvalidOperationException($"ModifyAnimationCommandRecord.Execute 失败: {tie.InnerException?.Message ?? tie.Message}");
            }

            string animName;
            try
            {
                var np = wrapperObj.GetType().GetProperty("Name");
                animName = np?.GetValue(wrapperObj)?.ToString() ?? animation;
            }
            catch { animName = animation; }

            return new Dictionary<string, object>
            {
                ["ok"] = true,
                ["animation"] = animName,
                ["action"] = action,
                ["executed"] = true,
                ["frameCount"] = results.Count,
                ["parameterRef"] = paramRef,
                ["modifiedDataRef"] = modifiedDataRef,
                ["commandRecordRef"] = recordRef,
                ["frames"] = results
            };
        }

        /// <summary>按参数类型精确定位方法（避免 GetMethod(name) 因重载抛 AmbiguousMatch）。找不到返回 null。</summary>
        private static MethodInfo FindMethodByParamTypes(Type type, string name, Type[] paramTypes)
        {
            if (type == null) return null;
            MethodInfo best = null;
            foreach (var m in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static))
            {
                if (m.Name != name) continue;
                var ps = m.GetParameters();
                if (ps.Length != paramTypes.Length) continue;
                bool ok = true;
                for (int i = 0; i < ps.Length; i++)
                    if (!ps[i].ParameterType.IsAssignableFrom(paramTypes[i])) { ok = false; break; }
                if (ok)
                {
                    best = m;
                    break;
                }
            }
            return best;
        }

        /// <summary>按参数个数定位方法（多个同参数量时优先取第一个 public 无重名歧义的）。找不到返回 null。</summary>
        private static MethodInfo FindMethodByParamCount(Type type, string name, int paramCount)
        {
            if (type == null) return null;
            foreach (var m in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static))
            {
                if (m.Name == name && m.GetParameters().Length == paramCount)
                    return m;
            }
            return null;
        }

        /// <summary>
        /// [V13 本地化资源] 读取本地化表里按 locale 使用的资源（字体等 NodeResource）。
        /// 反编译 LogicProject.dll 钉死的链路（2026-08-18，非脑补）：
        ///   路径1：wrapper.get_WrappedItem() → KanziLocalizationTable → get_LocalizationTableRecords() → KanziTranslationList → GetLocalizedResourceList() → IEnumerable&lt;NodeResource&gt;
        ///   路径2（兜底，不依赖 wrapper 暴露 get_WrappedItem）：AppDomain 已加载的 LogicProject 程序集 → GetType("KanziLocalizationTable") → 同链路
        /// 说明：普通文本走 GetTranslations（LocalizationTableRow.get_Translations），
        /// 字体等资源引用走 GetLocalizedResourceList，两者是不同通道。
        /// 只读，不影响现有工程；每个资源注册成 @obj 引用，可继续用 kz_invoke 操作。
        /// </summary>
        public object GetLocalizedResources(string target)
        {
            var wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
                throw new InvalidOperationException($"target '{target}' 解析为 null");

            // ---- 路径1：穿透 wrapper 拿内部对象（KanziLocalizationTable） ----
            var internalObj = GetWrappedItemRaw(wrapperObj) ?? wrapperObj;
            var results = TryGetLocalizedResourcesFromObject(internalObj);
            if (results != null)
                return results;

            // ---- 路径2：从 LogicProject 程序集按类型名反射定位（兜底，不依赖 get_WrappedItem） ----
            results = TryGetLocalizedResourcesFromLogicProject();
            if (results != null)
                return results;

            // 两条路径都失败 → 报错（不再静默返回空，便于排查）
            string usedType = internalObj?.GetType().FullName ?? "null";
            throw new InvalidOperationException(
                $"读本地化资源失败：wrapper 穿透对象({usedType})与 LogicProject 反射均拿不到" +
                $"  'get_LocalizationTableRecords'/'GetLocalizedResourceList'（本地化资源通道）。" +
                $"  target='{target}'");
        }

        /// <summary>
        /// 本地化表单条目操作（v13，不删表、保字体/A引用）。走内部对象 ResourceLocalizationItems.LocalizationTable 的
        /// ResourceDictionaryInterface 接口（GetEntry/Remove/Add/SetOrCreate/RenameResource），通过 GetInterfaceMap 调用
        ///（显式接口实现，普通反射看不到）。支持 operation：list/get/add/set/delete/rename。
        /// rows: [{ "resourceName":KEY, "type":"text|font|style|node", "defaultText":"...", "translations":{...}, "targetRef":"@objN" }]
        /// 全部单条目操作，绝不删整表 → 字体/A引用天然保留。纯反射，不缓存类型。
        /// </summary>
        public object LocalizationEntries(string target, string operation, object rows = null, object keys = null, object key = null)
        {
            if (!IsUiThread())
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                {
                    return app.Dispatcher.Invoke(new Func<object>(() =>
                        LocalizationEntriesCore(target, operation, rows, keys, key)));
                }
            }
            return LocalizationEntriesCore(target, operation, rows, keys, key);
        }

        private object LocalizationEntriesCore(string target, string operation, object rows, object keys, object key)
        {
            operation = (operation ?? "").Trim().ToLowerInvariant();
            if (operation == "")
                throw new ArgumentException("operation 不能为空（list/get/add/set/delete/rename）");

            // 解析目标并穿透到内部对象（ResourceLocalizationItems.LocalizationTable，有 ResourceDictionaryInterface）
            var wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
                throw new InvalidOperationException($"无法解析本地化表 target: '{target}'");
            var internalObj = GetWrappedItemRaw(wrapperObj) ?? wrapperObj;

            switch (operation)
            {
                case "list":
                    return ListEntries(internalObj);
                case "get":
                {
                    var gk = key?.ToString();
                    if (string.IsNullOrEmpty(gk) && keys is IEnumerable ike)
                        foreach (var kk in ike) { gk = kk?.ToString(); break; }
                    if (string.IsNullOrEmpty(gk))
                        throw new ArgumentException("get 需要传 key（resourceName）");
                    return GetEntryByKey(internalObj, gk);
                }
                case "add":
                {
                    if (rows == null)
                        throw new ArgumentException("add 需要传 rows（多行数组，每行带 resourceName + type）");
                    return AddEntries(internalObj, rows);
                }
                case "set":
                {
                    if (rows == null)
                        throw new ArgumentException("set 需要传 rows（多行数组）");
                    return SetEntries(internalObj, rows);
                }
                case "delete":
                {
                    var delKeys = new List<string>();
                    if (keys is IEnumerable de)
                        foreach (var kk in de) delKeys.Add(kk?.ToString() ?? "");
                    if (!string.IsNullOrEmpty(key?.ToString())) delKeys.Add(key.ToString());
                    if (delKeys.Count == 0)
                        throw new ArgumentException("delete 需要传 keys 数组或 key");
                    return DeleteEntries(internalObj, delKeys);
                }
                case "rename":
                {
                    var rnKeys = new List<string>();
                    if (keys is IEnumerable rne)
                        foreach (var kk in rne) rnKeys.Add(kk?.ToString() ?? "");
                    if (rnKeys.Count < 2)
                        throw new ArgumentException("rename 需要 keys=[旧key, 新key]");
                    return RenameEntry(internalObj, rnKeys[0], rnKeys[1]);
                }
                default:
                    throw new ArgumentException($"未知 operation: '{operation}'（支持 list/get/add/set/delete）");
            }
        }

        /// <summary>
        /// 本地化表【文本行】增/改（defaultText/translations）。走 wrapper 的 ImportTranslations(
        /// IEnumerable.LocalizationTableRow>) —— v8 实测通道。构造真实 LocalizationTableRow 对象
        /// （PluginInterface.LocalizationTableRow），设 ResourceName + Translations，再提交。
        /// 只改纯文本行；字体/style/node 条目的 ResourceReference 在 ResourceDictionary 字典，
        /// 不受此操作影响（v8 已验证：删表重建会丢字体引用，而 ImportTranslations 只覆盖文本值不删字典）。
        /// 纯反射，不缓存类型。
        /// </summary>
        public object LocalizationRowsWrite(string target, object rows)
        {
            if (!IsUiThread())
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                {
                    return app.Dispatcher.Invoke(new Func<object>(() => LocalizationRowsWriteCore(target, rows)));
                }
            }
            return LocalizationRowsWriteCore(target, rows);
        }

        private object LocalizationRowsWriteCore(string target, object rows)
        {
            var wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
                throw new InvalidOperationException($"无法解析本地化表 target: '{target}'");

            // 构造 LocalizationTableRow 类型：需具体类（接口无 ctor）。优先带 3 参 (string,string,IDictionary<string,string>) ctor
            // 的具体实现类；找不到可 new 的具体类则报错。
            Type rowType = null;
            ConstructorInfo rowCtor = null;
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (asm.IsDynamic) continue;
                Type[] types;
                try { types = asm.GetTypes(); } catch { continue; }
                foreach (var t in types)
                {
                    if (t == null || !t.IsClass || t.IsAbstract) continue;
                    if (t.Name == "LocalizationTableRow" || t.FullName?.Contains("LocalizationTableRow") == true)
                    {
                        var ctor = t.GetConstructor(new[] { typeof(string), typeof(string), typeof(IDictionary<string, string>) });
                        if (ctor != null)
                        {
                            rowType = t;
                            rowCtor = ctor;
                            break;
                        }
                    }
                }
                if (rowType != null) break;
            }
            if (rowType == null)
            {
                // 回退：任意具体 LocalizationTableRow，无参构造
                rowType = LoadTypeByFullName("Rightware.Kanzi.Studio.PluginInterface.LocalizationTableRow")
                          ?? LoadTypeByFullName("Rightware.Kanzi.Studio.PluginInterface.Implementation.LocalizationTableRow");
                if (rowType != null && rowType.IsClass && !rowType.IsAbstract)
                    rowCtor = rowType.GetConstructor(Type.EmptyTypes);
            }
            if (rowType == null || rowCtor == null)
                throw new InvalidOperationException("找不到可构造的 LocalizationTableRow 具体类（无 3 参/无参 ctor）");

            // 收集行的 resourceName + translations
            var translationsDict = new Dictionary<string, string>();
            var rowObjs = new List<object>();
            foreach (var r in rows as IEnumerable)
            {
                if (r == null) continue;
                var rn = DictRow(r, "resourceName");
                if (string.IsNullOrEmpty(rn)) continue;
                var defaultText = DictRow(r, "defaultText");
                // translations（若同传入语言映射）
                var tr = ExtractRow(r, "translations");
                var dict = new Dictionary<string, string>();
                if (tr is IDictionary io && io != null)
                    foreach (var kk in io.Keys) dict[kk.ToString()] = io[kk]?.ToString();
                object rowObj;
                var ctorPs = rowCtor.GetParameters();
                if (ctorPs.Length == 3)
                    rowObj = rowCtor.Invoke(new object[] { rn ?? "", defaultText ?? "", (object)dict });
                else
                {
                    rowObj = rowCtor.Invoke(null);
                    PopulateRowByReflection(rowObj, rn, dict.Count > 0 ? dict : null);
                }
                rowObjs.Add(rowObj);
            }
            if (rowObjs.Count == 0)
                return new Dictionary<string, object> { ["written"] = 0 };

            // 转成目标类型的 IList/数组（IEnumerable<LocalizationTableRow>）
            var arr = Array.CreateInstance(rowType, rowObjs.Count);
            for (int i = 0; i < rowObjs.Count; i++) arr.SetValue(rowObjs[i], i);

            // 调用 wrapper.ImportTranslations
            object result = null;
            try
            {
                result = InvokeCore(target, "ImportTranslations", new object[] { arr });
            }
            catch (Exception ex)
            {
                return new Dictionary<string, object> { ["written"] = 0, ["error"] = "ImportTranslations: " + ex.Message };
            }
            return new Dictionary<string, object> { ["written"] = rowObjs.Count, ["result"] = result?.ToString() };
        }

        /// <summary>从 row 字典取对象字段（translations 等）。</summary>
        private static object ExtractRow(object row, string field)
        {
            if (row is IDictionary<string, object> d && d.TryGetValue(field, out var v))
                return v;
            if (row is IDictionary dd && dd.Contains(field))
                return dd[field];
            return null;
        }

        /// <summary>
        /// 读本地化表单【单行】（按 ResourceName/key）。调 wrapper.ExportTranslations() 拿全部
        /// LocalizationTableRow，按 ResourceName 匹配，返回该行的 DefaultText + Translations
        /// （语言→值字典）。对文本行/字体行都适用——直接验证“每种语言能读到什么”。
        /// 全部纯反射，不碰对象图。
        /// </summary>
        public object LocalizationRowsRead(string target, string key)
        {
            if (!IsUiThread())
            {
                var app = System.Windows.Application.Current;
                if (app != null && app.Dispatcher != null)
                {
                    return app.Dispatcher.Invoke(new Func<object>(() => LocalizationRowsReadCore(target, key)));
                }
            }
            return LocalizationRowsReadCore(target, key);
        }

        private object LocalizationRowsReadCore(string target, string key)
        {
            var wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
                return new Dictionary<string, object> { ["error"] = $"无法解析本地化表 target: '{target}'" };
            // wrapper.ExportTranslations() -> IEnumerable<LocalizationTableRow>
            var rows = InvokeNamedMethod(wrapperObj, "ExportTranslations", new object[0]);
            if (rows is IEnumerable en)
            {
                foreach (var row in en)
                {
                    if (row == null) continue;
                    var rn = GetStringPropValue(row, "ResourceName");
                    if (string.IsNullOrEmpty(key) || string.Equals(rn, key, StringComparison.Ordinal))
                    {
                        return BuildRowReadResult(row);
                    }
                }
                return new Dictionary<string, object> { ["found"] = false, ["key"] = key };
            }
            throw new InvalidOperationException("ExportTranslations() 未返回可枚举行集合");
        }

        /// <summary>把单个 LocalizationTableRow 读成可用结果（DefaultText + 语言字典）。</summary>
        private Dictionary<string, object> BuildRowReadResult(object row)
        {
            var res = new Dictionary<string, object>
            {
                ["resourceName"] = GetStringPropValue(row, "ResourceName"),
                ["defaultText"] = GetStringPropValue(row, "DefaultText")
            };
            // get_Translations -> IEnumerable<KeyValuePair<string,string>>
            var tr = InvokeNamedMethod(row, "get_Translations", new object[0])
                      ?? TryCallInterfaceGetter(row, "get_Translations");
            var langs = new Dictionary<string, string>();
            if (tr is IEnumerable ten)
            {
                foreach (var kv in ten)
                {
                    try
                    {
                        // KeyValuePair<string,string>.Key / .Value
                        var k = kv.GetType().GetProperty("Key")?.GetValue(kv, null)?.ToString();
                        var v = kv.GetType().GetProperty("Value")?.GetValue(kv, null)?.ToString();
                        if (k != null) langs[k] = v;
                    }
                    catch { /* 单语言项忽略 */ }
                }
            }
            // 转成 Dictionary<string,object>，让 FormatInvokeResult 能展开每个语言值
            var langsObj = new Dictionary<string, object>();
            foreach (var kv in langs) langsObj[kv.Key] = kv.Value;
            res["translations"] = langsObj;
            res["languageCount"] = langs.Count;
            return res;
        }

        /// <summary>按名字直接 Invoke（普通反射，找不到返回 null）。</summary>
        private static object InvokeNamedMethod(object obj, string name, object[] args)
        {
            if (obj == null) return null;
            try
            {
                var m = obj.GetType().GetMethod(name);
                return m?.Invoke(obj, args);
            }
            catch { return null; }
        }

        /// <summary>读对象公开 string 属性，失败返回 null（与 TryGetStringProp 回调版对应，返回式）。</summary>
        private static string GetStringPropValue(object obj, string name)
        {
            try
            {
                var p = obj.GetType().GetProperty(name);
                if (p == null) return null;
                var v = p.GetValue(obj, null);
                return v != null ? Convert.ToString(v) : null;
            }
            catch { return null; }
        }

        /// <summary>返回式 bool 属性读取（对称 GetStringPropValue），失败返回 null。</summary>
        private static bool? GetBoolPropValue(object obj, string name)
        {
            try
            {
                var p = obj.GetType().GetProperty(name);
                if (p == null) return null;
                var v = p.GetValue(obj, null);
                return v is bool b ? b : (bool?)null;
            }
            catch { return null; }
        }

        /// <summary>
        /// 诊断：把“拿到 entry 的同一个内部对象”(ResourceLocalizationItems.LocalizationTable)
        /// 的【全部接口方法】列出来（public + 每个接口的显式方法，带签名），以便找出读翻译/文本的
        /// 隐藏接口入口（像 get_Entries 一样是显式接口实现）。只读元数据，绝不 Invoke，不碰对象图。
        /// </summary>
        public object LocalizationDumpInterfaces(string target)
        {
            var wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
                return new Dictionary<string, object> { ["error"] = $"无法解析 target: '{target}'" };
            var internalObj = GetWrappedItemRaw(wrapperObj) ?? wrapperObj;
            var t = internalObj.GetType();

            var ifaces = new List<object>();
            foreach (var ifc in t.GetInterfaces())
            {
                try
                {
                    var map = t.GetInterfaceMap(ifc);
                    var mlist = new List<object>();
                    for (int i = 0; i < map.InterfaceMethods.Length; i++)
                    {
                        var im = map.InterfaceMethods[i];
                        var tm = map.TargetMethods[i];
                        try
                        {
                            mlist.Add(new Dictionary<string, object>
                            {
                                ["name"] = im.Name + "(" + string.Join(", ", im.GetParameters().Select(p => p.ParameterType.Name)) + ") -> " + im.ReturnType.Name,
                                ["target"] = tm.Name,
                                ["explicit"] = tm.DeclaringType != t
                            });
                        }
                        catch { /* 单方法解析失败跳过 */ }
                    }
                    ifaces.Add(new Dictionary<string, object>
                    {
                        ["interface"] = ifc.FullName,
                        ["methods"] = mlist
                    });
                }
                catch { /* 该接口映射失败跳过 */ }
            }
            return new Dictionary<string, object>
            {
                ["target"] = target,
                ["type"] = t.FullName,
                ["interfaceCount"] = ifaces.Count,
                ["interfaces"] = ifaces,
                ["ownerNodeRef"] = TryResolveOwnerNodeRef(internalObj)
            };
        }

        /// <summary>诊断：尝试从内部对象调 get_OwnerNode()（接口方法），返回注册的引用（失败则为 null）。</summary>
        private object TryResolveOwnerNodeRef(object internalObj)
        {
            try
            {
                var owner = TryCallInterfaceGetter(internalObj, "get_OwnerNode");
                if (owner == null) return "(get_OwnerNode 返回 null)";
                return new Dictionary<string, object>
                {
                    ["ref_id"] = RegisterObject(owner),
                    ["type"] = owner.GetType().FullName
                };
            }
            catch (Exception ex) { return "(get_OwnerNode 异常: " + ex.Message + ")"; }
        }

        /// <summary>
        /// 通用：在 target 的内部对象（若 wrapper 可穿透）上调指定接口 getter 或 0 参接口方法。
        /// 用于挖普通反射看不到的显式接口实现（如 get_NodeReferences / GetFirstEntryForResource 等）。
        /// 结果：RegisterObject 引用 + 若是 IEnumerable 再展成一个受限列表（预算内）。
        /// </summary>
        public object LocalizationIface(string target, string method, object[] args = null, string key = null)
        {
            var wrapperObj = ResolveObject(target);
            if (wrapperObj == null)
                return new Dictionary<string, object> { ["error"] = $"无法解析 target: '{target}'" };
            var internalObj = GetWrappedItemRaw(wrapperObj) ?? wrapperObj;
            if (string.IsNullOrEmpty(method)) return new Dictionary<string, object> { ["error"] = "缺 method" };

            // 若给了 key 且没显式 args，则把 key 作为唯一参数传（如 GetEntry(key)）
            if (!string.IsNullOrEmpty(key) && (args == null || args.Length == 0))
                args = new object[] { key };

            object result = null;
            bool isGetter = method.StartsWith("get_", StringComparison.Ordinal);
            if (isGetter || args == null || args.Length == 0)
                result = TryCallInterfaceGetter(internalObj, method);
            // getter 也可能不是接口方法而是普通类方法 → 接口找不到时兜底普通反射
            if (result == null)
                result = InvokeNamedMethod(internalObj, method, args ?? new object[0]);
            if (result == null && !isGetter)
                result = TryCallInterfaceMethod(internalObj, method, args ?? new object[0]);

            if (result == null)
                return new Dictionary<string, object> { ["method"] = method, ["key"] = key, ["result"] = null };

            var res = new Dictionary<string, object>
            {
                ["method"] = method,
                ["resultType"] = result.GetType().FullName
            };
            // 枚举结果（受限）
            if (result is IEnumerable en)
            {
                var list = new List<object>();
                int n = 0;
                foreach (var item in en)
                {
                    if (n++ >= 200) { list.Add("...(>200 截断)"); break; }
                    var itemRef = RegisterObject(item);
                    var name = GetStringPropValue(item, "Name") ?? GetStringPropValue(item, "Key");
                    var entry = new Dictionary<string, object>
                    {
                        ["ref_id"] = itemRef,
                        ["type"] = item.GetType().Name,
                        ["name"] = name,
                        ["count"] = item is ICollection c ? c.Count : (object)null
                    };
                    // 若是 ResourceDictionaryEntry，补 isText + 资源引用目标（拿字体）
                    entry["isText"] = GetBoolPropValue(item, "IsText");
                    var rref = TryCallInterfaceGetter(item, "get_ResourceReference")
                                ?? InvokeNamedMethod(item, "get_ResourceReference", new object[0]);
                    if (rref != null)
                    {
                        var tgt = TryCallInterfaceGetter(rref, "get_Target")
                                  ?? InvokeNamedMethod(rref, "get_Target", new object[0]);
                        if (tgt != null)
                            entry["targetRef"] = RegisterObject(tgt);
                        entry["targetName"] = GetStringPropValue(rref, "DisplayName")
                                              ?? GetStringPropValue(rref, "Path")
                                              ?? GetStringPropValue(rref, "RelativePath");
                    }
                    list.Add(entry);
                }
                res["items"] = list;
                res["itemCount"] = n;
            }
            else
            {
                // 非枚举结果：若是 entry，展开它的 Key/isText/资源目标
                res["ref_id"] = RegisterObject(result);
                res["isText"] = GetBoolPropValue(result, "IsText");
                res["name"] = GetStringPropValue(result, "Name") ?? GetStringPropValue(result, "Key");
                var rref2 = TryCallInterfaceGetter(result, "get_ResourceReference")
                            ?? InvokeNamedMethod(result, "get_ResourceReference", new object[0]);
                if (rref2 != null)
                {
                    var tgt2 = TryCallInterfaceGetter(rref2, "get_Target")
                               ?? InvokeNamedMethod(rref2, "get_Target", new object[0]);
                    if (tgt2 != null)
                        res["targetRef"] = RegisterObject(tgt2);
                    res["targetName"] = GetStringPropValue(rref2, "DisplayName")
                                        ?? GetStringPropValue(rref2, "Path")
                                        ?? GetStringPropValue(rref2, "RelativePath");
                }
            }
            return res;
        }

        /// <summary>list：枚举所有条目（复用 get_Entries 通道）</summary>
        private object ListEntries(object internalObj)
        {
            var ent = TryCallInterfaceGetter(internalObj, "get_Entries");
            if (ent is IEnumerable en)
            {
                // 一次性建 Locale 地图（locale name -> Locale 对象），供逐条 GetEntry 查翻译（验证过比 get_Entries 可靠）
                var locales = GetLocalesList(internalObj);
                var defaultMap = BuildDefaultValueMap(internalObj, en);
                var resources = new List<object>();
                foreach (var entry in en)
                {
                    if (entry == null) continue;
                    var refId = RegisterObject(entry);
                    var info = BuildEntryInfo(entry, refId);
                    var key = GetStringPropValue(entry, "Key");
                    info["default"] = key != null && defaultMap.TryGetValue(key, out var dv) ? dv : null;
                    // 各语言翻译：逐条走 GetEntry(验证过可靠)
                    info["translations"] = key != null
                        ? ReadEntryAcrossLocales(locales, key)
                        : (object)new Dictionary<string, object>();
                    resources.Add(info);
                }
                return new Dictionary<string, object>
                {
                    ["count"] = resources.Count,
                    ["resources"] = resources
                };
            }
            throw new InvalidOperationException("本地化表 get_Entries() 未能调用（接口映射失败）");
        }

        /// <summary>get：按 key 取单个条目（GetEntry），附 default + 各语言翻译（走每个 Locale 的 GetEntry(key)，已验证可靠）。</summary>
        private object GetEntryByKey(object internalObj, string rn)
        {
            var entry = TryCallInterfaceMethod(internalObj, "GetEntry", new object[] { rn });
            if (entry == null)
                return new Dictionary<string, object> { ["found"] = false, ["key"] = rn };
            var refId = RegisterObject(entry);
            var info = BuildEntryInfo(entry, refId);
            var key = GetStringPropValue(entry, "Key") ?? rn;
            // default = 主表 entry 自身值（文本=RelativePath，字体=Target.Name）
            info["default"] = TryGetEntryValue(entry) ?? key;
            // 各语言翻译：遍历 get_Locales，逐个 Locale 调 GetEntry(key)（已验证可拿到每语言值）
            info["translations"] = ReadEntryAcrossLocales(internalObj, key);
            return info;
        }

        /// <summary>遍历 get_Locales，对每个 Locale 调 GetEntry(key) 取该语言的值（文本=RelativePath，字体=Target.Name）。
        /// 注意：internalObj 是表对象，虽实现 IEnumerable（枚举的是 entries），绝不能当 locale 列表用——必须 GetLocalesList。</summary>
        private static Dictionary<string, object> ReadEntryAcrossLocales(object internalObj, string key)
        {
            var locales = GetLocalesList(internalObj);
            return ReadEntryAcrossLocales(locales, key);
        }

        /// <summary>从 internalObj 枚举 get_Locales 返回 List（locale name -> Locale 对象表），供复用。</summary>
        private static List<object> GetLocalesList(object internalObj)
        {
            var list = new List<object>();
            try
            {
                var locales = TryCallInterfaceGetter(internalObj, "get_Locales")
                              ?? InvokeNamedMethod(internalObj, "get_Locales", new object[0]);
                if (locales is IEnumerable locEn)
                    foreach (var lo in locEn) list.Add(lo);
            }
            catch { }
            return list;
        }

        /// <summary>遍历 Locale 集合，逐个 Locale 调 GetEntry(key) 取该语言值。</summary>
        private static Dictionary<string, object> ReadEntryAcrossLocales(IEnumerable localeList, string key)
        {
            var result = new Dictionary<string, object>();
            try
            {
                if (localeList == null) return result;
                int budget = 60; // 14 locale × 少量调用
                foreach (var localeObj in localeList)
                {
                    if (--budget < 0) break;
                    var localeName = GetStringPropValue(localeObj, "LocaleName")
                                     ?? GetStringPropValue(localeObj, "Name");
                    if (localeName == null) localeName = "?";
                    var lentry = TryCallInterfaceMethod(localeObj, "GetEntry", new object[] { key })
                                 ?? InvokeNamedMethod(localeObj, "GetEntry", new object[] { key });
                    if (lentry != null)
                        result[localeName] = TryGetEntryValue(lentry) ?? GetStringPropValue(lentry, "Key");
                }
            }
            catch { /* 失败返回 partial */ }
            return result;
        }

        /// <summary>从单 entry 读值：isText→resourceRef.RelativePath（翻译文本），否则→Target.Name（如 FontFamily）。
        /// 兼容 locale 字体行：Target 可能解析为 DynamicProperty 集合而读不到 Name，此时从 resourceRef.ToString()
        /// （形如 "ProjectItemReference: SourceHanSansSC ABSOLUTE"）提取字体名。</summary>
        private static string TryGetEntryValue(object entry)
        {
            try
            {
                var t = entry.GetType();
                // 读 ResourceReference：优先接口 getter（穿透显式接口实现），再退普通属性
                object refVal = TryCallInterfaceGetter(entry, "get_ResourceReference");
                if (refVal == null)
                {
                    var refProp = t.GetProperty("ResourceReference");
                    refVal = refProp?.GetValue(entry, null);
                }
                if (refVal == null)
                {
                    // 无 ResourceReference：可能就是纯文本 entry，直接看 Key
                    return GetStringPropValue(entry, "Key") ?? GetStringPropValue(entry, "Name");
                }
                bool isText = false;
                try
                {
                    object iv = TryCallInterfaceGetter(entry, "get_IsText");
                    if (iv == null)
                    {
                        var it = entry.GetType().GetProperty("IsText");
                        iv = it?.GetValue(entry, null);
                    }
                    if (iv is bool b) isText = b;
                }
                catch { }
                if (isText)
                    return GetStringPropValue(refVal, "RelativePath")
                           ?? GetStringPropValue(refVal, "Path")
                           ?? GetStringPropValue(refVal, "DisplayName")
                           ?? ExtractRefName(refVal);
                // 字体/非文本：验证通过的流程——字体名在 resourceRef.ToString()（形如
                // "ProjectItemReference: SourceHanSansSC ABSOLUTE"），ExtractRefName 提取；
                // Target 常指向 DynamicProperty（如 FontFiles）读不到，仅作最后备援。
                var rn = ExtractRefName(refVal);
                if (!string.IsNullOrEmpty(rn)) return rn;
                return TryReadTargetName(refVal)
                       ?? GetStringPropValue(refVal, "DisplayName")
                       ?? GetStringPropValue(refVal, "Path")
                       ?? GetStringPropValue(refVal, "RelativePath");
            }
            catch { return null; }
        }

        /// <summary>读 ProjectItemReference 的 Target 的 Name（FontFamily 等）；Target 非单一对象时返回 null。</summary>
        private static string TryReadTargetName(object refVal)
        {
            try
            {
                var tp = refVal.GetType().GetProperty("Target");
                var tv = tp?.GetValue(refVal, null);
                if (tv != null)
                {
                    var n = GetStringPropValue(tv, "Name");
                    if (!string.IsNullOrEmpty(n)) return n;
                    var p = GetStringPropValue(tv, "Path");
                    if (!string.IsNullOrEmpty(p)) return p;
                }
                return null;
            }
            catch { return null; }
        }

        /// <summary>从 resourceRef 对象提取显示名：优先 Name；否则 ToString()（形如 "ProjectItemReference: SourceHanSansSC ABSOLUTE"）里取引用名。</summary>
        private static string ExtractRefName(object refObj)
        {
            try
            {
                var n = GetStringPropValue(refObj, "Name");
                if (!string.IsNullOrEmpty(n) && n.IndexOf("ProjectItemReference") < 0) return n;
                var n2 = GetStringPropValue(refObj, "Value");
                if (!string.IsNullOrEmpty(n2) && n2.IndexOf("ProjectItemReference") < 0) return n2;
                // ToString() 提取："ProjectItemReference: XXX ABSOLUTE" → XXX
                var toStr = refObj.ToString();
                if (!string.IsNullOrEmpty(toStr))
                {
                    var idx = toStr.LastIndexOf(":");
                    if (idx >= 0)
                    {
                        var seg = toStr.Substring(idx + 1).Trim();
                        // 去掉尾缀修饰（ABSOLUTE/RELATIVE）
                        var sp = seg.LastIndexOf(' ');
                        if (sp > 0) seg = seg.Substring(0, sp).Trim();
                        if (seg.Length > 0) return seg;
                    }
                }
                return toStr;
            }
            catch { return null; }
        }

        /// <summary>
        /// 一次性枚举 14 个 Locale，每个 Locale 的 get_Entries 建 {localeName -> {key -> value}}。
        /// 供 list/get 逐条取各语言翻译。预算受限（14 × 条目数），不在 UI 线程外跑巨量。
        /// </summary>
        /// <summary>主表 default：条目 key -> 值（文本=RelativePath，字体=Target.Name）。</summary>
        private static Dictionary<string, object> BuildDefaultValueMap(object internalObj, IEnumerable mainEntries)
        {
            var map = new Dictionary<string, object>();
            try
            {
                foreach (var entry in mainEntries)
                {
                    if (entry == null) continue;
                    var k = GetStringPropValue(entry, "Key");
                    if (k == null) continue;
                    map[k] = TryGetEntryValue(entry) ?? k;
                }
            }
            catch { }
            return map;
        }

        /// <summary>add：批量新增带 type 的多行（Add/SetOrCreate）</summary>
        private object AddEntries(object internalObj, object rows)
        {
            var added = new List<object>();
            var errors = new List<object>();
            foreach (var r in rows as IEnumerable)
            {
                if (r == null) continue;
                try
                {
                    var entry = BuildEntryFromRow(internalObj, r);
                    if (entry == null)
                    {
                        errors.Add(new Dictionary<string, object> { ["key"] = DictRow(r, "resourceName"), ["error"] = "无法构造对应 type 的条目" });
                        continue;
                    }
                    var addResult = new Dictionary<string, object>
                    {
                        ["key"] = DictRow(r, "resourceName"),
                        ["type"] = DictRow(r, "type"),
                        ["added"] = false,
                        ["defaultSetHow"] = _lastDefaultHow
                    };
                    try
                    {
                        var rn = DictRow(r, "resourceName");
                        addResult["signatures"] = DumpWriteMethodSignatures(internalObj);
                        addResult["entryCaps"] = DumpEntryTypeCaps(entry);
                        {
                            string howKey = null;
                            var keySet = TrySetEntryKeyViaInterface(entry, rn, out howKey);
                            addResult["entryKey"] = TryGetEntryKeyViaInterface(entry);   // 读回 entry 的 Key，确认是否设上
                            addResult["keySet"] = keySet;
                            addResult["keySetHow"] = howKey;
                        }
                        // 正确调用（运行时签名确认）：SetOrCreate(ResourceDictionaryEntry, bool) 优先（老隋指示），失败再试 Add。
                        var tried = new List<object>();
                        foreach (var mn in new[] { "SetOrCreate", "Add" })
                        {
                            object ok = null;
                            try
                            {
                                ok = TryCallInterfaceMethod(internalObj, mn, new object[] { entry, true });
                            }
                            catch (Exception ex2)
                            {
                                ok = "THROW:" + ex2.Message;
                            }
                            bool thisOk = ok == null || (ok is bool bb && bb);  // void 返回 null 视为成功（SetOrCreate 是 void）
                            tried.Add(new Dictionary<string, object>
                            {
                                ["method"] = mn,
                                ["return"] = ok == null ? null : (ok + "(" + ok.GetType().Name + ")"),
                                ["ok"] = thisOk
                            });
                        }
                        bool isOk = tried.OfType<Dictionary<string, object>>().Any(t => (bool)t["ok"]);
                        addResult["added"] = isOk;
                        addResult["tried"] = tried;
                        // 各语言翻译写入：row.translations = {语言:值}，对每个 Locale 构造含该语言值的 entry，SetOrCreate 到对应 Locale
                        try
                        {
                            var trObj = ExtractRow(r, "translations");
                            var trMap = new Dictionary<string, object>();
                            if (trObj is IDictionary trd)
                            {
                                var locales = GetLocalesList(internalObj);
                                int tbudget = 200;
                                foreach (System.Collections.DictionaryEntry de in trd)
                                {
                                    if (--tbudget < 0) break;
                                    var lang = de.Key?.ToString();
                                    var langVal = de.Value?.ToString();
                                    if (string.IsNullOrEmpty(lang)) continue;
                                    object localeObj = null;
                                    foreach (var lo in locales)
                                    {
                                        var ln = GetStringPropValue(lo, "LocaleName") ?? GetStringPropValue(lo, "Name");
                                        if (ln == lang) { localeObj = lo; break; }
                                    }
                                    if (localeObj == null)
                                    {
                                        trMap[lang] = "NO-LOCALE";
                                        continue;
                                    }
                                    // 构造该语言 text entry（Key=rn，值=langVal），SetOrCreate 到 Locale
                                    var lent = BuildTextEntry(internalObj, rn, langVal, out string lentHow);
                                    if (lent == null) { trMap[lang] = "BUILD-FAIL:" + lentHow; continue; }
                                    var lok = TryCallInterfaceMethod(localeObj, "SetOrCreate", new object[] { lent, true });
                                    trMap[lang] = lok == null ? "SET-OK(volatile)" : (lok + "(" + lok.GetType().Name + ")");
                                }
                            }
                            addResult["translationsTried"] = trMap;
                        }
                        catch (Exception ext)
                        {
                            addResult["translationsError"] = ext.Message;
                        }
                    }
                    catch (Exception ex)
                    {
                        addResult["error"] = ex.Message;
                    }
                    added.Add(addResult);
                }
                catch (Exception ex)
                {
                    errors.Add(new Dictionary<string, object> { ["key"] = DictRow(r, "resourceName"), ["error"] = ex.Message });
                }
            }
            return new Dictionary<string, object> { ["addedCount"] = added.Count, ["added"] = added, ["errors"] = errors };
        }

        /// <summary>set：批量修改多行。改文本/翻译/引用。取原条目→改字段→SetOrCreate，保留原 type/A引用。</summary>
        private object SetEntries(object internalObj, object rows)
        {
            var updated = new List<object>();
            var errors = new List<object>();
            foreach (var r in rows as IEnumerable)
            {
                if (r == null) continue;
                var rn = DictRow(r, "resourceName");
                try
                {
                    // 与 add 一致：用新构造重建 entry（SetOrCreate 对已有 key 即更新）。不依赖 ApplyRowToExisting(旧逻辑改内存对象)。
                    var entry = BuildEntryFromRow(internalObj, r);
                    if (entry == null)
                        throw new InvalidOperationException("构造条目失败");
                    var upd = new Dictionary<string, object> { ["key"] = rn, ["updated"] = false };
                    try
                    {
                        // 正确调用：SetOrCreate(ResourceDictionaryEntry, bool)。第一参 entry，第二参 bool=true。void 返回(null)即视为成功。
                        var ok = TryCallInterfaceMethod(internalObj, "SetOrCreate", new object[] { entry, true });
                        bool isOk = ok == null || (ok is bool bb && bb);   // void 返回 null 视为成功
                        upd["updated"] = isOk;
                        if (ok != null && !(ok is bool))
                            upd["return"] = ok + "(" + ok.GetType().Name + ")";
                        upd["defaultSetHow"] = _lastDefaultHow;
                        // 各语言翻译写入：与 add 一致
                        try
                        {
                            var trObj = ExtractRow(r, "translations");
                            var trMap = new Dictionary<string, object>();
                            if (trObj is IDictionary trd)
                            {
                                var locales = GetLocalesList(internalObj);
                                int tbudget = 200;
                                foreach (System.Collections.DictionaryEntry de in trd)
                                {
                                    if (--tbudget < 0) break;
                                    var lang = de.Key?.ToString();
                                    var langVal = de.Value?.ToString();
                                    if (string.IsNullOrEmpty(lang)) continue;
                                    object localeObj = null;
                                    foreach (var lo in locales)
                                    {
                                        var ln = GetStringPropValue(lo, "LocaleName") ?? GetStringPropValue(lo, "Name");
                                        if (ln == lang) { localeObj = lo; break; }
                                    }
                                    if (localeObj == null) { trMap[lang] = "NO-LOCALE"; continue; }
                                    var lent = BuildTextEntry(internalObj, rn, langVal, out string lentHow);
                                    if (lent == null) { trMap[lang] = "BUILD-FAIL:" + lentHow; continue; }
                                    var lok = TryCallInterfaceMethod(localeObj, "SetOrCreate", new object[] { lent, true });
                                    trMap[lang] = lok == null ? "SET-OK(volatile)" : (lok + "(" + lok.GetType().Name + ")");
                                }
                            }
                            upd["translationsTried"] = trMap;
                        }
                        catch (Exception ext)
                        {
                            upd["translationsError"] = ext.Message;
                        }
                    }
                    catch (Exception ex)
                    {
                        upd["error"] = "SetOrCreate: " + ex.Message;
                    }
                    updated.Add(upd);
                }
                catch (Exception ex)
                {
                    errors.Add(new Dictionary<string, object> { ["key"] = rn, ["error"] = ex.Message });
                }
            }
            return new Dictionary<string, object> { ["updatedCount"] = updated.Count, ["updated"] = updated, ["errors"] = errors };
        }

        /// <summary>delete：按 key 批量删单行（Remove，不删表）</summary>
        private object DeleteEntries(object internalObj, List<string> keys)
        {
            var deleted = new List<object>();
            var errors = new List<object>();
            foreach (var rn in keys)
            {
                var del = new Dictionary<string, object> { ["key"] = rn, ["deleted"] = false };
                try
                {
                    del["signatures"] = DumpWriteMethodSignatures(internalObj);
                    // 正确调用：Remove(string, bool) 删 key（返回 void(null)，不抛异常即视为删除生效）。
                    var ok = TryCallInterfaceMethod(internalObj, "Remove", new object[] { rn, true });
                    // Remove(string,bool) 返回 void(null)：返回 null 视为删除已执行，bool false 才算失败。
                    bool removed = ok == null || (ok is bool bb && bb);
                    del["deleted"] = removed;
                    if (ok != null && !(ok is bool))
                        del["return"] = ok + "(" + ok.GetType().Name + ")";
                }
                catch (Exception ex)
                {
                    del["error"] = "Remove: " + ex.Message;
                }
                deleted.Add(del);
            }
            return new Dictionary<string, object> { ["deletedCount"] = deleted.Count, ["deleted"] = deleted, ["errors"] = errors };
        }

        /// <summary>rename：重命名单条目（RenameResource）</summary>
        private object RenameEntry(object internalObj, string oldKey, string newKey)
        {
            // 尝试直接 RenameResource(old,new)。签名 (string,string,bool,Node)——只传前两参，其余默认 null/false
            object ok = null;
            try
            {
                ok = TryCallInterfaceMethod(internalObj, "RenameResource", new object[] { oldKey, newKey });
            }
            catch { ok = null; }
            // void 返回(null)即视为成功；只有抛异常才失败
            bool renamed = ok == null || (ok is bool b && b);
            if (!renamed)
                throw new InvalidOperationException($"重命名 '{oldKey}' → '{newKey}' 失败（RenameResource 返回 false）");
            return new Dictionary<string, object> { ["oldKey"] = oldKey, ["newKey"] = newKey, ["renamed"] = renamed };
        }

        /// <summary>从 row 构造 ResourceDictionaryEntry（带 type）。文本=无 ResourceReference；font/style/node=New 带引用。</summary>
        private object BuildEntryFromRow(object internalObj, object row)
        {
            var rn = DictRow(row, "resourceName");
            var type = (DictRow(row, "type") ?? "text").ToLowerInvariant();
            var entryType = LoadTypeByFullName(
                "Rightware.Kanzi.Tool.Logic.Project.ResourceDictionaryItems.ResourceDictionaryEntry");
            if (entryType == null)
                throw new InvalidOperationException("找不到 ResourceDictionaryEntry 类型");

            object entry;
            _lastDefaultHow = null;
            if (type == "text")
            {
                // 正确构造：new ResourceDictionaryEntry(key, new ProjectItemReference(text, ContentType.TEXT))
                var dt = DictRow(row, "defaultText") ?? rn;
                var pir = CreateProjectItemReferenceWithText(dt, "TEXT");
                if (pir == null) _lastDefaultHow = "PIR-CTOR-FAIL";
                else _lastDefaultHow = "pir(text=" + (dt ?? "") + ",TEXT)";
                entry = ConstructEntryWithRef(entryType, rn, pir);
            }
            else
            {
                // font/style/node：new ResourceDictionaryEntry(key, new ProjectItemReference(targetRef, ContentType))
                var targetRef = DictRow(row, "targetRef");
                string ctName = type.ToUpperInvariant();   // FONT/STYLE/NODE → ContentType
                if (type == "node") ctName = "NODE";
                if (type == "font") ctName = "FONT";
                if (type == "style") ctName = "STYLE";
                object pir = null;
                if (!string.IsNullOrEmpty(targetRef))
                {
                    var refObj = ResolveObject(targetRef);
                    if (refObj != null)
                        pir = CreateProjectItemReferenceForObj(refObj, ctName);
                }
                entry = ConstructEntryWithRef(entryType, rn, pir);
            }
            if (entry == null)
                throw new InvalidOperationException("构造 ResourceDictionaryEntry 失败");
            return entry;
        }

        /// <summary>构造带文本值的 text entry（用于写入某语言翻译）。用正确构造：new ResourceDictionaryEntry(key, new ProjectItemReference(text, TEXT))。</summary>
        private object BuildTextEntry(object internalObj, string rn, string langVal, out string how)
        {
            how = null;
            try
            {
                var entryType = LoadTypeByFullName(
                    "Rightware.Kanzi.Tool.Logic.Project.ResourceDictionaryItems.ResourceDictionaryEntry");
                if (entryType == null) { how = "NO-TYPE"; return null; }
                var pir = CreateProjectItemReferenceWithText(langVal, "TEXT");
                if (pir == null) { how = "PIR-CTOR-FAIL"; return null; }
                var entry = ConstructEntryWithRef(entryType, rn, pir);
                how = "entry(key=" + rn + ",pir(text=" + (langVal ?? "") + "))";
                return entry;
            }
            catch (Exception ex)
            {
                how = "THROW:" + ex.Message;
                return null;
            }
        }

        /// <summary>用 new ResourceDictionaryEntry(key, ProjectItemReference) 构造带 key + 引用的 entry。</summary>
        private static object ConstructEntryWithRef(Type entryType, string key, object pir)
        {
            if (pir == null) return null;
            try
            {
                var ctor = entryType.GetConstructor(new[] { typeof(string), pir.GetType() });
                if (ctor == null) return null;
                return ctor.Invoke(new object[] { key, pir });
            }
            catch { return null; }
        }

        /// <summary>new ProjectItemReference(text, ContentType.X) 构造承载文本的引用。</summary>
        private static object CreateProjectItemReferenceWithText(string text, string contentTypeName)
        {
            try
            {
                var pirType = LoadTypeByFullName("Rightware.Kanzi.Tool.Logic.Project.ProjectItemReference");
                if (pirType == null) return null;
                var ct = ResolveContentTypeEnum(contentTypeName);
                if (ct == null) return null;
                var ctor = pirType.GetConstructor(new[] { typeof(string), ct.GetType() });
                if (ctor == null) return null;
                return ctor.Invoke(new object[] { text, ct });
            }
            catch { return null; }
        }

        /// <summary>new ProjectItemReference(target, ContentType.X) 构造指向资源对象的引用（font/style/node）。</summary>
        private static object CreateProjectItemReferenceForObj(object target, string contentTypeName)
        {
            try
            {
                var pirType = LoadTypeByFullName("Rightware.Kanzi.Tool.Logic.Project.ProjectItemReference");
                if (pirType == null) return null;
                // 优先用 (ProjectItemInterface target) ctor
                var ctor1 = pirType.GetConstructor(new[] { target.GetType() });
                if (ctor1 != null) return ctor1.Invoke(new object[] { target });
                var ct = ResolveContentTypeEnum(contentTypeName);
                if (ct == null) return null;
                var ctor2 = pirType.GetConstructor(new[] { typeof(string), ct.GetType() });
                if (ctor2 == null) return null;
                return ctor2.Invoke(new object[] { GetStringPropValue(target, "Name") ?? target.ToString(), ct });
            }
            catch { return null; }
        }

        /// <summary>解析 ProjectItemReferenceContentType 枚举值（TEXT/FONT/STYLE/NODE 等）。</summary>
        private static object ResolveContentTypeEnum(string name)
        {
            try
            {
                var et = LoadTypeByFullName("Rightware.Kanzi.Tool.Logic.Project.ProjectItemReferenceContentType")
                         ?? AppDomain.CurrentDomain.GetAssemblies()
                             .SelectMany(a => { try { return a.GetTypes(); } catch { return new Type[0]; } })
                             .FirstOrDefault(t => t.Name == "ProjectItemReferenceContentType");
                if (et == null) return null;
                string fieldName = name.ToUpperInvariant() == "NODE" ? "NODE" : name.ToUpperInvariant();
                var f = et.GetField(fieldName) ?? et.GetFields().FirstOrDefault(x => x.Name.ToUpperInvariant() == name.ToUpperInvariant());
                if (f != null) return f.GetValue(null);
                // 枚举名里找匹配
                foreach (var fn in et.GetEnumNames())
                {
                    if (fn.ToUpperInvariant().Contains(name.ToUpperInvariant()) || name.ToUpperInvariant().Contains(fn.ToUpperInvariant()))
                        return Enum.Parse(et, fn);
                }
                return null;
            }
            catch { return null; }
        }

        /// <summary>对已有条目应用 row 的修改字段（改 defaultText/密钥/引用）。保留 type。</summary>
        private void ApplyRowToExisting(object internalObj, object entry, object row)
        {
            var rn = DictRow(row, "resourceName");
            if (!string.IsNullOrEmpty(rn))
                TrySetEntryKeyViaInterface(entry, rn, out _);
            var defaultText = DictRow(row, "defaultText");
            if (defaultText != null)
                TrySetStringDefaultText(entry, defaultText);
            var type = (DictRow(row, "type") ?? "").ToLowerInvariant();
            var targetRef = DictRow(row, "targetRef");
            if (type != "text" && !string.IsNullOrEmpty(targetRef))
            {
                var refObj = ResolveObject(targetRef);
                ApplyResourceReference(entry, refObj);
            }
        }

        /// <summary>设置 entry 的 ResourceReference（font/style/node）。refObj 是目标资源（FontFamily/Style/Node 等）。</summary>
        private void ApplyResourceReference(object entry, object refObj)
        {
            if (refObj == null) return;
            try
            {
                // 尝试直接 set_ResourceReference；若需要 ProjectItemReference 包装，fallback 到 set_ResourceReferenceNull
                var t = entry.GetType();
                var setRef = t.GetProperty("ResourceReference")?.GetSetMethod() ?? t.GetMethod("set_ResourceReference");
                if (setRef != null)
                {
                    // 若参数类型是 ProjectItemReference，需构造；否则直接放 refObj
                    var p0 = setRef.GetParameters()[0].ParameterType;
                    if (p0.IsAssignableFrom(refObj.GetType()))
                        setRef.Invoke(entry, new object[] { refObj });
                    else if (p0.FullName != null && p0.FullName.Contains("ProjectItemReference"))
                    {
                        var pir = CreateProjectItemReference(refObj);
                        if (pir != null) setRef.Invoke(entry, new object[] { pir });
                    }
                }
            }
            catch { /* 设置失败静默（调用方会报错） */ }
        }

        /// <summary>构造 ProjectItemReference 指向目标资源（若需包装）。</summary>
        private object CreateProjectItemReference(object target)
        {
            try
            {
                var pirType = LoadTypeByFullName(
                    "Rightware.Kanzi.Tool.Logic.Project.ProjectItemReference");
                if (pirType == null)
                {
                    // 用 new ResourceDictionaryEntry(ProjectItemReference, string) 走引用构造更稳
                    return null;
                }
                var ctor = pirType.GetConstructor(new[] { target.GetType() })
                           ?? pirType.GetConstructor(Type.EmptyTypes);
                if (ctor == null) return null;
                var pir = ctor.Invoke(new[] { target });
                return pir;
            }
            catch { return null; }
        }

        /// <summary>设置 DefaultText（若可写）。</summary>
        private static void TrySetStringDefaultText(object obj, string val)
        {
            try
            {
                var setter = obj.GetType().GetProperty("DefaultText")?.GetSetMethod()
                             ?? obj.GetType().GetMethod("set_DefaultText");
                setter?.Invoke(obj, new object[] { val });
            }
            catch { }
        }

        private static bool TrySetStringDefaultText2(object obj, string val, out string how)
        {
            how = null;
            if (obj == null || val == null) return false;
            try
            {
                var p = obj.GetType().GetProperty("DefaultText");
                var setter = p?.GetSetMethod(true);
                if (setter != null && setter.GetParameters()[0].ParameterType == typeof(string))
                {
                    setter.Invoke(obj, new object[] { val });
                    how = "DefaultText prop setter: " + setter.Name;
                    return true;
                }
                foreach (var f in new[] { BindingFlags.Public, BindingFlags.NonPublic, BindingFlags.Public | BindingFlags.NonPublic })
                {
                    var m = obj.GetType().GetMethod("set_DefaultText", f | BindingFlags.Instance);
                    if (m != null && m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType == typeof(string))
                    {
                        m.Invoke(obj, new object[] { val });
                        how = "set_DefaultText method (";
                        return true;
                    }
                }
                how = "NO-DEFAULTTEXT-SETTER";
            }
            catch (Exception ex)
            {
                how = "THROW:" + ex.Message;
            }
            return false;
        }

        /// <summary>设置 string 属性（Key 等）。</summary>
        private static void TrySetStringProp(object obj, string propName, string val)
        {
            try
            {
                var setter = obj.GetType().GetProperty(propName)?.GetSetMethod()
                             ?? obj.GetType().GetMethod("set_" + propName);
                setter?.Invoke(obj, new object[] { val });
            }
            catch { }
        }

        /// <summary>通过接口映射读取属性值（处理显式接口实现的属性，如 ResourceDictionaryEntry.Key 的 get_Key）。</summary>
        private static string TryGetEntryKeyViaInterface(object entry)
        {
            if (entry == null) return null;
            try
            {
                var g = entry.GetType().GetProperty("Key")?.GetGetMethod();
                if (g != null)
                {
                    var v = g.Invoke(entry, null);
                    return v?.ToString();
                }
                foreach (var ifc in entry.GetType().GetInterfaces())
                {
                    InterfaceMapping map;
                    try { map = entry.GetType().GetInterfaceMap(ifc); }
                    catch { continue; }
                    for (int i = 0; i < map.InterfaceMethods.Length; i++)
                    {
                        var im = map.InterfaceMethods[i];
                        var tm = map.TargetMethods[i];
                        if (im.Name == "get_Key" || im.Name.EndsWith(".get_Key")) return tm.Invoke(entry, null)?.ToString();
                    }
                }
            }
            catch { }
            return null;
        }

        /// <summary>通过接口映射设置属性（处理显式接口实现的属性，如 ResourceDictionaryEntry.Key 的 set_Key）。</summary>
        private static bool TrySetEntryKeyViaInterface(object entry, string key, out string how)
        {
            how = null;
            if (entry == null || key == null) return false;
            try
            {
                // 1) 普通属性 setter（含 private）
                var p = entry.GetType().GetProperty("Key");
                var setter = p?.GetSetMethod(true);   // true=incl nonpublic
                if (setter != null)
                {
                    setter.Invoke(entry, new object[] { key });
                    how = "prop setter: " + setter.Name;
                    return true;
                }
                // 2) set_Key 方法（Public + NonPublic）
                foreach (var f in new[] { BindingFlags.Public, BindingFlags.NonPublic, BindingFlags.Public | BindingFlags.NonPublic })
                {
                    var m = entry.GetType().GetMethod("set_Key", f | BindingFlags.Instance);
                    if (m != null && m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType == typeof(string))
                    {
                        m.Invoke(entry, new object[] { key });
                        how = "method " + m.Name + " (" + m.Attributes + ")";
                        return true;
                    }
                }
                // 3) 接口映射里的 set_Key（显式接口实现，方法名可能是 <Interface>.set_Key 或 set_Key）
                foreach (var ifc in entry.GetType().GetInterfaces())
                {
                    InterfaceMapping map;
                    try { map = entry.GetType().GetInterfaceMap(ifc); }
                    catch { continue; }
                    for (int i = 0; i < map.InterfaceMethods.Length; i++)
                    {
                        var im = map.InterfaceMethods[i];
                        var tm = map.TargetMethods[i];
                        if (im.Name == "set_Key" || im.Name.EndsWith(".set_Key"))
                        {
                            var ps = tm.GetParameters();
                            if (ps.Length == 1 && ps[0].ParameterType == typeof(string))
                            {
                                tm.Invoke(entry, new object[] { key });
                                how = "iface " + im.Name + " -> " + tm.Name + " (" + tm.Attributes + ")";
                                return true;
                            }
                        }
                    }
                }
                how = "NO-SETTER-FOUND";
            }
            catch (Exception ex)
            {
                how = "THROW:" + ex.Message;
            }
            return false;
        }

        /// <summary>从 dict 行取字段值。</summary>
        private static string DictRow(object row, string field)
        {
            if (row is IDictionary<string, object> d && d.TryGetValue(field, out var v))
                return v?.ToString();
            return null;
        }

        /// <summary>
        /// 通过接口映射精确调用带参数的接口方法（显式接口实现）。按名字匹配可兼容的参数数量/类型，
        /// 遍历所有接口；无匹配或不兼容返回 null。
        /// </summary>
        private static object TryCallInterfaceMethod(object obj, string methodName, object[] args)
        {
            if (obj == null || string.IsNullOrEmpty(methodName)) return null;
            var t = obj.GetType();
            object lastErr = null;
            int matched = 0;
            foreach (var ifc in t.GetInterfaces())
            {
                InterfaceMapping map;
                try { map = t.GetInterfaceMap(ifc); }
                catch { continue; }
                for (int i = 0; i < map.InterfaceMethods.Length; i++)
                {
                    if (map.InterfaceMethods[i].Name != methodName) continue;
                    var tm = map.TargetMethods[i];
                    var ps = tm.GetParameters();
                    if (ps.Length != (args?.Length ?? 0)) continue;   // 参数数量不匹配则跳过
                    // ★ 参数类型兼容性检查：每个实参类型必须能赋值给形参类型（避免匹配到同名同参数量但类型不符的重载，
                    //   如 Remove(string) 误匹配到 Remove(DynamicProperty)）
                    bool typeOk = true;
                    for (int k = 0; k < ps.Length; k++)
                    {
                        var arg = args[k];
                        var pt = ps[k].ParameterType;
                        if (arg == null)
                        {
                            // null 实参：仅当形参为引用类型或可空类型才可能匹配
                            if (pt.IsValueType && Nullable.GetUnderlyingType(pt) == null) { typeOk = false; break; }
                        }
                        else if (!pt.IsInstanceOfType(arg))
                        {
                            typeOk = false;
                            break;
                        }
                    }
                    if (!typeOk) continue;   // 类型不符 → 跳过，找真正的重载
                    matched++;
                    try
                    {
                        return tm.Invoke(obj, args);
                    }
                    catch (TargetInvocationException tie)
                    {
                        lastErr = tie.InnerException ?? tie;
                        continue;
                    }
                    catch (Exception ex) { lastErr = ex; continue; }
                }
            }
            if (matched > 0 && lastErr is Exception le)
                throw new InvalidOperationException($"接口方法 {methodName} 调用失败: {le.Message}");
            return null;
        }

        /// <summary>诊断：列出 Insert/Add/SetOrCreate/Remove 等写方法在 internalObj 上的运行时参数类型（含接口映射）。</summary>
        private static object DumpWriteMethodSignatures(object obj)
        {
            var res = new List<object>();
            if (obj == null) return new Dictionary<string, object> { ["type"] = "null", ["methods"] = res };
            var target = new[] { "Insert", "Add", "SetOrCreate", "Remove", "GenerateUniqueResourceID", "GetEntry", "get_Entries" };
            var seen = new HashSet<string>();
            int typeCount = 0, ifaceCount = 0;
            var typeName = obj.GetType().FullName;
            void AddSig(string from, string name, Type[] ps, Type ret)
            {
                var key = from + "#" + name + "#" + string.Join(",", ps.Select(p => (object)p.Name));
                if (!seen.Add(key)) return;
                res.Add(new Dictionary<string, object>
                {
                    ["from"] = from,
                    ["method"] = name,
                    ["params"] = ps.Select(p => (object)new Dictionary<string, object>
                    {
                        ["type"] = p.FullName ?? p.Name,
                        ["kind"] = p.IsValueType ? (Nullable.GetUnderlyingType(p) != null ? "nullable" : "val") : "ref"
                    }).ToList(),
                    ["return"] = ret?.FullName ?? ret?.Name
                });
            }
            try
            {
                foreach (var m in obj.GetType().GetMethods())
                {
                    if (target.Contains(m.Name)) { typeCount++; AddSig("type", m.Name, m.GetParameters().Select(p => p.ParameterType).ToArray(), m.ReturnType); }
                }
            }
            catch (Exception ex) { res.Add(new Dictionary<string, object> { ["typeErr"] = ex.Message }); }
            try
            {
                foreach (var ifc in obj.GetType().GetInterfaces())
                {
                    try
                    {
                        var map = obj.GetType().GetInterfaceMap(ifc);
                        for (int i = 0; i < map.InterfaceMethods.Length; i++)
                        {
                            var im = map.InterfaceMethods[i];
                            if (!target.Contains(im.Name)) continue;
                            ifaceCount++;
                            var tm = map.TargetMethods[i];
                            var ps = tm.GetParameters().Select(p => p.ParameterType).ToArray();
                            AddSig("iface:" + ifc.Name, im.Name, ps, tm.ReturnType);
                        }
                    }
                    catch (Exception ex) { res.Add(new Dictionary<string, object> { ["ifaceErr_" + ifc.Name] = ex.Message }); }
                }
            }
            catch (Exception ex) { res.Add(new Dictionary<string, object> { ["ifacesErr"] = ex.Message }); }
            // 汇总信息放最前
            var meta = new Dictionary<string, object>
            {
                ["type"] = typeName,
                ["typeMethodHits"] = typeCount,
                ["ifaceHits"] = ifaceCount,
                ["ifaces"] = obj.GetType().GetInterfaces().Select(i => i.Name).ToList()
            };
            res.Insert(0, meta);
            return res;
        }

        /// <summary>
        /// 从任意“能拿到本地化资源列表的对象”提取资源。核心链路（反编译钉死）：
        ///   obj → get_LocalizationTableRecords() → KanziTranslationList → GetLocalizedResourceList() → IEnumerable&lt;NodeResource&gt;
        /// 找不到核心方法时返回 null（让上一层走兜底路径），而非抛错。
        /// </summary>
        private object TryGetLocalizedResourcesFromObject(object obj)
        {
            if (obj == null) return null;
            return TryGetFromObjectWithDepth(obj, 0);
        }

        /// <summary>
        /// 从任意对象尝试读本地化资源。严格受限：绝不无限递归对象图。
        /// 只做确定性、有目标的查找（见 TryProbeOne），总调用次数/深度硬上限，避免卡死线程。
        /// </summary>
        private object TryGetFromObjectWithDepth(object obj, int depth)
        {
            if (obj == null) return null;
            var probe = new ProbeState { Budget = 60, MaxDepth = 3 };
            return ProbeRecursive(obj, 0, probe);
        }

        /// <summary>受控探测状态（总调用预算 + 深度上限 + 去重）。</summary>
        private sealed class ProbeState
        {
            public int Budget;
            public int MaxDepth;
            public readonly HashSet<object> Seen = new HashSet<object>(KzRefComparer.Instance);
        }

        /// <summary>
        /// 确定性探测：对 obj 及其直系关联对象做有限步骤查找，绝不遍历整个对象图。
        ///   a. 自身有 GetLocalizedResourceList → 直接读；
        ///   b. 自身有 get_LocalizationTableRecords → 对结果再查 GetLocalizedResourceList；
        ///   c. 通过 Item→wrappedItem→内部对象链只探 1 层；
        ///   每探一层都扣预算，超预算立即中止。
        /// </summary>
        private object ProbeRecursive(object obj, int depth, ProbeState st)
        {
            if (obj == null || depth > st.MaxDepth) return null;
            if (!st.Seen.Add(obj)) return null;

            var t = obj.GetType();

            // a. 自身有 GetLocalizedResourceList → 直接读
            var lm = FindMethodByParamCount(t, "GetLocalizedResourceList", 0);
            if (lm != null && st.Budget-- > 0)
            {
                object lr;
                try { lr = lm.Invoke(obj, null); }
                catch (TargetInvocationException tie)
                {
                    throw new InvalidOperationException($"GetLocalizedResourceList 调用失败: {tie.InnerException?.Message ?? tie.Message}");
                }
                if (lr != null) return BuildLocalizedResourcesResult(lr);
            }

            // a2. 自身有 get_Resources（字体=ResourceReference 通道，ResourceDictionaryWrapper 上有）→ 直接枚举
            if (st.Budget-- > 0)
            {
                var rm0 = t.GetMethod("get_Resources") ?? FindMethodByParamCount(t, "get_Resources", 0);
                if (rm0 != null)
                {
                    object res;
                    try { res = rm0.Invoke(obj, null); }
                    catch { res = null; }
                    if (res is IEnumerable resEnum)
                        return BuildLocalizedResourcesResult(resEnum);
                }
            }

            // a3. 通过接口映射精确调 get_Resources（显式接口实现，普通 GetMethod 看不到）
            if (st.Budget-- > 0)
            {
                object ifRes = TryCallInterfaceGetter(obj, "get_Resources");
                if (ifRes is IEnumerable ifResEnum)
                    return BuildLocalizedResourcesResult(ifResEnum);
            }

            // a4. 通过接口映射精确调 get_Entries（取所有资源字典条目：文本+字体等）。
            //     每行是 ResourceDictionaryEntry，其 get_ResourceReference() 即字体/资源引用。
            //     这是 ResourceLocalizationItems.LocalizationTable 上真正能拿到字体引用的通道（显式接口实现）。
            if (st.Budget > 0)
            {
                object ent = null;
                // 优先接口映射（get_Entries 是 ResourceDictionaryInterface 显式实现，普通反射看不到）
                ent = TryCallInterfaceGetter(obj, "get_Entries");
                if (ent == null)
                {
                    try
                    {
                        var en = obj.GetType().GetMethod("get_Entries")
                                 ?? FindMethodByParamCount(obj.GetType(), "get_Entries", 0);
                        ent = en?.Invoke(obj, null);
                    }
                    catch { ent = null; }
                }
                st.Budget--;
                if (ent is IEnumerable entEnum)
                    return BuildEntriesResult(entEnum);
            }

            // b. 自身有 get_LocalizationTableRecords → 结果递归
            if (st.Budget-- > 0)
            {
                var rm = t.GetMethod("get_LocalizationTableRecords")
                         ?? FindMethodByParamCount(t, "get_LocalizationTableRecords", 0);
                if (rm != null)
                {
                    object rl;
                    try { rl = rm.Invoke(obj, null); }
                    catch { rl = null; }
                    if (rl != null)
                    {
                        var r = ProbeRecursive(rl, depth + 1, st);
                        if (r != null) return r;
                    }
                }
            }

            // c. 只穿透关键关联：get_WrappedItem / get_HostingItem（1 层，不进接口海量方法）
            if (st.Budget-- > 0)
            {
                var inner = GetWrappedItemRaw(obj) ?? TryGetHostingItem(obj);
                if (inner != null && !ReferenceEquals(inner, obj))
                {
                    var r = ProbeRecursive(inner, depth + 1, st);
                    if (r != null) return r;
                }
            }

            return null;
        }

        /// <summary>尝试取 get_HostingItem（对象宿主），返回 null 表示无。</summary>
        private static object TryGetHostingItem(object obj)
        {
            if (obj == null) return null;
            try
            {
                var m = obj.GetType().GetMethod("get_HostingItem")
                        ?? FindMethodByParamCount(obj.GetType(), "get_HostingItem", 0);
                if (m == null) return null;
                var v = m.Invoke(obj, null);
                return v;
            }
            catch { return null; }
        }

        /// <summary>
        /// 通过接口映射精确调用指定名字的接口 getter（显式接口实现，普通 GetMethod 看不到）。
        /// 只按名字匹配，不遍历全部方法；返回 null 表示无此接口 getter 或调用失败。
        /// </summary>
        private static object TryCallInterfaceGetter(object obj, string getterName)
        {
            if (obj == null || string.IsNullOrEmpty(getterName)) return null;
            var t = obj.GetType();
            foreach (var ifc in t.GetInterfaces())
            {
                InterfaceMapping map;
                try { map = t.GetInterfaceMap(ifc); }
                catch { continue; }
                for (int i = 0; i < map.InterfaceMethods.Length; i++)
                {
                    if (map.InterfaceMethods[i].Name != getterName) continue;
                    var tm = map.TargetMethods[i];
                    try
                    {
                        var v = tm.Invoke(obj, null);
                        return v;
                    }
                    catch { return null; }
                }
            }
            return null;
        }

        /// <summary>占位（保留签名，避免外部引用出错；当前探测不依赖它）。</summary>
        private static bool SkipPropForTraversal(Type t) => true;

        /// <summary>引用相等比较器（兼容 .NET Framework，避免依赖 .NET 5+ 的 ReferenceEqualityComparer）。</summary>
        private sealed class KzRefComparer : IEqualityComparer<object>
        {
            public static readonly KzRefComparer Instance = new KzRefComparer();
            public bool Equals(object x, object y) => ReferenceEquals(x, y);
            public int GetHashCode(object obj) => System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(obj);
        }


        /// <summary>
        /// 路径2：兜底扫描，不依赖 wrapper 的 get_WrappedItem。
        /// ① 扫描对象池（@obj 引用缓存）：找任意带 GetLocalizedResourceList 方法的对象（如用户已引用的表记录集合）直接读；
        /// ② 若 LogicProject 程序集已加载且其类型实现了本地化记录接口（多态），则尝试按类型名匹配池内对象。
        /// 2. 全反射，不直接引用具体类型（符合 KzMCPPlugin 铁律）。
        /// </summary>
        private object TryGetLocalizedResourcesFromLogicProject()
        {
            // ① 扫描对象池：任意已注册对象，若它（或其内部对象）能提供 GetLocalizedResourceList 就直接读。
            //    全局预算保护：对象池可能很大，总探测次数超限立即放弃，绝不阻塞。
            int globalBudget = 1200;
            foreach (var kv in _objectStore.ToList())
            {
                if (globalBudget <= 0) break;
                globalBudget--;
                var obj = kv.Value;
                if (obj == null) continue;
                try
                {
                    // 本身有核心链路
                    var r1 = TryGetLocalizedResourcesFromObject(obj);
                    if (r1 != null) return r1;
                    // 穿透它拿内部对象再试
                    var inner = GetWrappedItemRaw(obj);
                    if (inner != null && !ReferenceEquals(inner, obj))
                    {
                        var r2 = TryGetLocalizedResourcesFromObject(inner);
                        if (r2 != null) return r2;
                    }
                }
                catch { /* 单个对象失败不阻塞整体扫描 */ }
            }
            return null;
        }

        /// <summary>把 GetLocalizedResourceList 的返回值（IEnumerable<NodeResource>）枚举成结构化字典列表。</summary>
        private object BuildLocalizedResourcesResult(object localizedResult)
        {
            var resources = new List<object>();
            if (localizedResult is IEnumerable en)
            {
                foreach (var resource in en)
                {
                    var refId = RegisterObject(resource);
                    resources.Add(BuildResourceInfo(resource, refId));
                }
            }
            else if (localizedResult != null)
            {
                var refId = RegisterObject(localizedResult);
                resources.Add(BuildResourceInfo(localizedResult, refId));
            }

            return new Dictionary<string, object>
            {
                ["count"] = resources.Count,
                ["resources"] = resources
            };
        }

        /// <summary>
        /// 枚举 ResourceDictionaryEntry 条目（get_Entries 的结果）。每行 = ResourceDictionaryEntry，
        /// 其中 get_Key() 为 resourceName、get_ResourceReference() 为字体/资源引用（ProjectItemReference）。
        /// 逐个提取可读信息并注册 @obj 引用，方便后续 kz_invoke 深入 target（FontFamily 等）。
        /// </summary>
        private object BuildEntriesResult(IEnumerable entries)
        {
            var resources = new List<object>();
            try
            {
                foreach (var entry in entries)
                {
                    if (entry == null) continue;
                    var refId = RegisterObject(entry);
                    resources.Add(BuildEntryInfo(entry, refId));
                }
            }
            catch (Exception ex)
            {
                // 单个条目失败不中断整体，记录错误并继续
                resources.Add(new Dictionary<string, object>
                {
                    ["error"] = "枚举 entry 失败: " + ex.Message
                });
            }

            return new Dictionary<string, object>
            {
                ["count"] = resources.Count,
                ["resources"] = resources
            };
        }

        /// <summary>从 ResourceDictionaryEntry 提取可读信息：Key / IsText / IsAlias / IsURL / ResourceReference 目标(FontFamily)。</summary>
        private Dictionary<string, object> BuildEntryInfo(object entry, string refId)
        {
            var t = entry.GetType();
            var info = new Dictionary<string, object>
            {
                ["ref_id"] = refId,
                ["type"] = t.Name,
                ["fullType"] = t.FullName
            };

            // 条目 key（resourceName，如 SourceHanSansSCfontFamily）
            TryGetStringProp(entry, "Key", v => info["key"] = v);

            // 条目属性标记
            TryGetBoolProp(entry, "IsText", v => info["isText"] = v);
            TryGetBoolProp(entry, "IsAlias", v => info["isAlias"] = v);
            TryGetBoolProp(entry, "IsURL", v => info["isUrl"] = v);
            // ★ 枚举 entry 所有可读公开属性（不含资源引用本身，避免递归）——给完整画面
            DumpReadableProps(entry, info);

            // 资源引用（get_ResourceReference → ProjectItemReference → Target = FontFamily 等）
            try
            {
                object refVal = null;
                var refProp = t.GetProperty("ResourceReference");
                if (refProp != null)
                    refVal = refProp.GetValue(entry, null);
                if (refVal != null)
                {
                    var rrRef = RegisterObject(refVal);
                    info["resourceRef"] = rrRef;
                    info["resourceRefType"] = refVal.GetType().Name;
                    info["resourceRefFullType"] = refVal.GetType().FullName;

                    // 引用目标（FontFamily 等）——ProjectItemReference.get_Target
                    TryGetStringProp(refVal, "Name", v => info["resourceRefName"] = v);
                    TryGetStringProp(refVal, "Path", v => info["resourceRefPath"] = v);
                    // resourceRef 全部可读属性
                    DumpReadableProps(refVal, info, "resourceRef_");
                    try
                    {
                        var targetProp = refVal.GetType().GetProperty("Target");
                        var targetVal = targetProp?.GetValue(refVal, null);
                        if (targetVal != null && !ReferenceEquals(targetVal, refVal))
                        {
                            var tgtRef = RegisterObject(targetVal);
                            info["targetRef"] = tgtRef;
                            info["targetType"] = targetVal.GetType().Name;
                            info["targetFullType"] = targetVal.GetType().FullName;
                            TryGetStringProp(targetVal, "Name", v => info["targetName"] = v);
                            TryGetStringProp(targetVal, "Path", v => info["targetPath"] = v);
                            DumpReadableProps(targetVal, info, "target_");
                        }
                    }
                    catch { /* Target 属性不存在则忽略 */ }
                }
            }
            catch { /* ResourceReference 属性不存在则忽略 */ }

            // ★ 内容类型（对齐 add 的 type）：text | font | style | node
            try
            {
                bool isText = info.TryGetValue("isText", out var it) && it is bool ib && ib;
                string targetTypeName = info.TryGetValue("targetType", out var tt) ? Convert.ToString(tt) : null;
                string ct;
                if (isText)
                    ct = "text";
                else if (targetTypeName != null && targetTypeName.IndexOf("Font", StringComparison.OrdinalIgnoreCase) >= 0)
                    ct = "font";
                else if (targetTypeName != null && targetTypeName.IndexOf("Style", StringComparison.OrdinalIgnoreCase) >= 0)
                    ct = "style";
                else
                    ct = "node";
                info["contentType"] = ct;
            }
            catch { info["contentType"] = "node"; }

            return info;
        }

        /// <summary>
        /// 安全枚举对象的可读公开属性：浅层读取，标量/字符串直接 ToString；复杂对象只记类型名，
        /// 不递归不 get 深层（避免触 Kanzi 巨大对象图/成环 → 崩溃）。用于给“增删改查走 Entry”做完整画面。
        /// </summary>
        /// <summary>dump entity 类型的构造函数 + 方法面（找设文本/值的正确入口）。</summary>
        private static object DumpEntryTypeCaps(object entry)
        {
            var res = new Dictionary<string, object>();
            try
            {
                var t = entry.GetType();
                res["type"] = t.FullName;
                res["ctors"] = t.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .Select(c => (object)("(" + string.Join(", ", c.GetParameters().Select(p => (p.ParameterType.FullName ?? p.ParameterType.Name) + " " + p.Name)) + ")"))
                    .ToList();
                res["props"] = t.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .Select(p => (object)(p.Name + ":" + (p.PropertyType.Name)))
                    .ToList();
                res["methods"] = t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                    .Select(m => m.Name)
                    .Distinct()
                    .Where(n => !n.StartsWith("get_") && !n.StartsWith("set_"))
                    .Select(n => (object)n)
                    .ToList();
                // resourceRef(ProjectItemReference) 的可写入口：setters + 属性 + 构造函数
                try
                {
                    var rr = t.GetProperty("ResourceReference")?.GetValue(entry, null);
                    if (rr != null)
                    {
                        var rt = rr.GetType();
                        var rrC = new Dictionary<string, object>();
                        rrC["type"] = rt.FullName;
                        rrC["props"] = rt.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                            .Where(p => p.CanWrite || p.CanRead)
                            .Select(p => (object)(p.Name + ":" + (p.PropertyType.Name) + (p.CanWrite ? "(w)" : "(r)")))
                            .ToList();
                        rrC["setters"] = rt.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                            .Where(m => m.Name.StartsWith("set_"))
                            .Select(m => (object)(m.Name + "(" + string.Join(",", m.GetParameters().Select(p => p.ParameterType.Name)) + ")"))
                            .ToList();
                        rrC["ctors"] = rt.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                            .Select(c => (object)("(" + string.Join(", ", c.GetParameters().Select(p => (p.ParameterType.FullName ?? p.ParameterType.Name) + " " + p.Name)) + ")"))
                            .ToList();
                        res["resourceRefCaps"] = rrC;
                    }
                }
                catch { }
            }
            catch (Exception ex) { res["error"] = ex.Message; }
            return res;
        }

        private static void DumpReadableProps(object obj, Dictionary<string, object> into, string prefix = "")
        {
            if (obj == null) return;
            Type t;
            try { t = obj.GetType(); } catch { return; }
            PropertyInfo[] props;
            try { props = t.GetProperties(BindingFlags.Public | BindingFlags.Instance); }
            catch { return; }
            foreach (var p in props)
            {
                if (p.GetIndexParameters().Length > 0) continue;      // 跳过索引器
                if (p.GetMethod == null) continue;                    // 只读不了就跳过
                if (!p.CanRead) continue;
                try
                {
                    var val = p.GetValue(obj, null);
                    if (val == null)
                        into[prefix + p.Name] = null;
                    else
                    {
                        // 标量表类型直接存；复杂对象只存类型名，避免递归
                        if (IsScalarType(val.GetType()))
                            into[prefix + p.Name] = val;
                        else
                            into[prefix + p.Name + "__type"] = val.GetType().Name;
                    }
                }
                catch { /* 个别属性 get 抛错就跳过 */ }
            }
        }

        private static bool IsScalarType(Type t)
        {
            if (t.IsPrimitive || t.IsEnum) return true;
            if (t == typeof(string) || t == typeof(decimal) || t == typeof(DateTime) || t == typeof(TimeSpan)) return true;
            var u = Nullable.GetUnderlyingType(t);
            if (u != null && (u.IsPrimitive || u.IsEnum || u == typeof(decimal))) return true;
            return false;
        }


        /// <summary>从 NodeResource/资源对象上提取可读信息（resourceID/name/path/引用标记），注册 @obj 引用。</summary>
        private Dictionary<string, object> BuildResourceInfo(object resource, string refId)
        {
            var t = resource.GetType();
            var info = new Dictionary<string, object>
            {
                ["ref_id"] = refId,
                ["type"] = t.Name,
                ["fullType"] = t.FullName
            };

            // NodeResource 常用只读字段，逐个兜底反射（存在才读，不存在忽略）
            TryGetStringProp(resource, "Name", v => info["name"] = v);
            TryGetStringProp(resource, "Path", v => info["path"] = v);
            TryGetStringProp(resource, "ResourceID", v => info["resourceID"] = v);

            // ProjectItemReference 才有：get_IsResourceReference / get_IsText / get_Target
            TryGetBoolProp(resource, "IsResourceReference", v => info["isResourceReference"] = v);
            TryGetBoolProp(resource, "IsText", v => info["isText"] = v);

            // 目标对象（FontFamily 等）——若 resource 是引用类型，get_Target 返回目标；若是 NodeResource 本体，目标即自身
            try
            {
                var targetProp = t.GetProperty("Target");
                var targetVal = targetProp?.GetValue(resource, null);
                if (targetVal != null && !ReferenceEquals(targetVal, resource))
                {
                    var tgtRef = RegisterObject(targetVal);
                    info["targetRef"] = tgtRef;
                    info["targetType"] = targetVal.GetType().Name;
                    info["targetFullType"] = targetVal.GetType().FullName;
                    TryGetStringProp(targetVal, "Name", v => info["targetName"] = v);
                    TryGetStringProp(targetVal, "Path", v => info["targetPath"] = v);
                }
            }
            catch { /* Target 属性不存在则忽略 */ }
            return info;
        }

        private static void TryGetStringProp(object obj, string name, Action<string> set)
        {
            try
            {
                var p = obj.GetType().GetProperty(name);
                if (p == null) return;
                var v = p.GetValue(obj, null);
                if (v != null) set(Convert.ToString(v));
            }
            catch { }
        }

        private static void TryGetBoolProp(object obj, string name, Action<bool> set)
        {
            try
            {
                var p = obj.GetType().GetProperty(name);
                if (p == null) return;
                if (p.GetValue(obj, null) is bool b) set(b);
            }
            catch { }
        }

        /// <summary>直扡反射调 get_WrappedItem 拿内部对象（不经过 WrapResult 的 IEnumerable 展开）</summary>
        private object GetWrappedItemRaw(object wrapperObj)
        {
            if (wrapperObj == null) return null;
            var t = wrapperObj.GetType();
            MethodInfo m = null;
            try { m = t.GetMethod("get_WrappedItem"); } catch { }
            if (m == null)
            {
                var prop = t.GetProperty("WrappedItem");
                m = prop?.GetGetMethod();
            }
            if (m == null) return null;
            try { return m.Invoke(wrapperObj, null); }
            catch { return null; }
        }

        /// <summary>构造一个 AnimationKeyFrame。type 默认 LINEAR。value 按目标类型转换（float/int/bool/string）。</summary>
        private object BuildAnimationKeyFrame(Dictionary<string, object> dict, Type frameType, Type interpType)
        {
            // Time: Single (float)
            float time = 0f;
            if (dict.ContainsKey("time")) time = Convert.ToSingle(dict["time"]);

            // Value: 按目标动画属性类型转换。Kanzi 动画 target 绝大多数是 Number(float)，
            // 所以纯数字优先转 float（避免整型被当成 int 导致数值型 target 不匹配）。
            object value;
            if (dict.ContainsKey("value") && dict["value"] != null)
            {
                string vs = Convert.ToString(dict["value"]);
                if (bool.TryParse(vs, out var b)) value = b;
                else if (float.TryParse(vs, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var fv)) value = fv;
                else if (TryParseColor(vs, out var col)) value = col;
                else value = vs; // 兜底字符串
            }
            else
            {
                value = 0f; // remove 等场景未给值，给默认 0
            }

            // InterpolationType（枚举）：默认 LINEAR
            object interpVal;
            string typeName = dict.ContainsKey("type") ? Convert.ToString(dict["type"]) : "LINEAR";
            try { interpVal = Enum.Parse(interpType, typeName, true); }
            catch { interpVal = Enum.Parse(interpType, "LINEAR"); }

            // 4参构造器: .ctor(Single, Object, InterpolationType, KeyFrameInterpolationData)
            // 最后一个 KeyFrameInterpolationData 传 null（默认插值）
            var ctor = frameType.GetConstructors()
                .FirstOrDefault(c => c.GetParameters().Length == 4);
            if (ctor == null) throw new MissingMethodException("AnimationKeyFrame 上找不到 4 参构造器");

            // 需要匹配 (Single, Object, InterpolationType, KeyFrameInterpolationData)
            // float 与 Single 相同。Enum 值直接放 ref 匹配（反射 Invoke 会拿真实枚举对象匹配）。
            return ctor.Invoke(new object[] { time, value, interpVal, null });
        }

        private static string DescribeFrame(Dictionary<string, object> dict)
        {
            try
            {
                var t = dict.ContainsKey("time") ? Convert.ToString(dict["time"]) : "";
                var v = dict.ContainsKey("value") ? Convert.ToString(dict["value"]) : "";
                return $"time={t}, value={v}";
            }
            catch { return "?"; }
        }

        /// <summary>尝试把字符串解析成 System.Windows.Media.Color（#AARRGGBB / #RRGGBB），失败返回 false。</summary>
        private static bool TryParseColor(string s, out object color)
        {
            color = null;
            if (string.IsNullOrWhiteSpace(s) || !s.StartsWith("#")) return false;
            try
            {
                var ct = ResolveTypeByName("System.Windows.Media.Color");
                if (ct == null) return false;
                // System.Windows.Media.ColorConverter.ConvertFromString(s)
                var cc = ResolveTypeByName("System.Windows.Media.ColorConverter");
                if (cc == null) return false;
                var convertMethod = cc.GetMethod("ConvertFromString", new[] { typeof(string) });
                if (convertMethod == null) return false;
                var obj = convertMethod.Invoke(null, new object[] { s });
                if (obj == null) return false;
                // ConvertFromString 可能返回 Color 或别的；确认赋给 Color
                if (ct.IsInstanceOfType(obj)) { color = obj; return true; }
                // 若返回的是别的（如可从 .ToString 转换），兜底
                color = obj;
                return true;
            }
            catch { return false; }
        }

        #endregion ModifyAnimation 关键帧编辑

        #region CreateNode 辅助方法

        /// <summary>
        /// 手动构造 CreateProjectItem&lt;T&gt; 泛型方法并调用。
        /// </summary>
        private object TryCreateByManualGeneric(string nodeType, string name, object parent)
        {
            try
            {
                var targetType = _project.GetType();
                MethodInfo genMethod = null;
                foreach (var m in targetType.GetMethods(BindingFlags.Public | BindingFlags.Instance))
                {
                    if (m.Name == "CreateProjectItem" && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 1)
                    {
                        genMethod = m;
                        break;
                    }
                }
                if (genMethod == null)
                {
                    foreach (var iface in targetType.GetInterfaces())
                    {
                        foreach (var m in iface.GetMethods(BindingFlags.Public | BindingFlags.Instance))
                        {
                            if (m.Name == "CreateProjectItem" && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 1)
                            {
                                genMethod = m;
                                break;
                            }
                        }
                        if (genMethod != null) break;
                    }
                }

                if (genMethod == null) return null;

                Type typeArg = null;

                // 先通过 ProjectItemTypeLibrary.GetItemByName 查找
                try
                {
                    var typeLibProp = targetType.GetProperty("ProjectItemTypeLibrary");
                    if (typeLibProp == null)
                    {
                        foreach (var iface in targetType.GetInterfaces())
                        {
                            typeLibProp = iface.GetProperty("ProjectItemTypeLibrary");
                            if (typeLibProp != null) break;
                        }
                    }
                    if (typeLibProp != null)
                    {
                        var typeLib = typeLibProp.GetValue(_project);
                        if (typeLib != null)
                        {
                            var getItem = typeLib.GetType().GetMethod("GetItemByName", new[] { typeof(string) });
                            if (getItem != null)
                            {
                                var typeItem = getItem.Invoke(typeLib, new[] { nodeType });
                                if (typeItem != null) typeArg = typeItem.GetType();
                            }
                        }
                    }
                }
                catch { }

                if (typeArg != null)
                {
                    var constructed = genMethod.MakeGenericMethod(typeArg);
                    var rawResult = constructed.Invoke(_project, new object[] { name, parent });
                    return rawResult;
                }
            }
            catch { }
            return null;
        }

        /// <summary>
        /// 通过 StateManagerLibrary 创建 StateManager。
        /// StateManager 是库级项目项，不在 ProjectItemTypeLibrary 中。
        /// </summary>
        private object CreateStateManagerViaLibrary(string name, object parent)
        {
            // 获取 StateManagerLibrary 对象
            // @project 上有 GetProjectItemByKzbUrl，能返回 StateManagerLibraryPluginWrapper
            var targetType = _project.GetType();
            MethodInfo getByUrlMethod = null;
            foreach (var iface in targetType.GetInterfaces())
            {
                var map = targetType.GetInterfaceMap(iface);
                for (int i = 0; i < map.InterfaceMethods.Length; i++)
                {
                    if (map.InterfaceMethods[i].Name == "GetProjectItemByKzbUrl")
                    {
                        if (map.InterfaceMethods[i].GetParameters().Length == 2)
                        {
                            getByUrlMethod = map.InterfaceMethods[i];
                            break;
                        }
                    }
                }
                if (getByUrlMethod != null) break;
            }

            if (getByUrlMethod == null) return null;

            // StateManager 库的路径
            string smLibraryPath = "/State Managers";
            // 确定父路径 - 如果传入的 parent 是容器节点，先创建在 State Managers 下
            // 否则用默认路径
            string parentPath = smLibraryPath;

            object smLibrary = getByUrlMethod.Invoke(_project, new object[] { smLibraryPath, false });
            if (smLibrary == null) return null;

            // 在 StateManagerLibrary 上调用 CreateProjectItem
            // 它实现了 ProjectItemLibrary<StateManager>，应该能创建
            var smLibType = smLibrary.GetType();
            MethodInfo createMethod = null;
            var allMethods = smLibType.GetMethods(BindingFlags.Public | BindingFlags.Instance);
            foreach (var m in allMethods)
            {
                if (m.Name == "CreateProjectItem" && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 1)
                {
                    createMethod = m;
                    break;
                }
            }

            if (createMethod != null)
            {
                try
                {
                    // 尝试直接用泛型方式
                    // T = StateManager 接口 — 从 smLibrary 的接口中获取
                    Type stateManagerIface = null;
                    foreach (var iface in smLibType.GetInterfaces())
                    {
                        if (iface.IsGenericType && iface.GetGenericTypeDefinition().Name.Contains("ProjectItemLibrary"))
                        {
                            var genArgs = iface.GetGenericArguments();
                            if (genArgs.Length == 1 && genArgs[0].Name == "StateManager")
                            {
                                stateManagerIface = genArgs[0];
                                break;
                            }
                        }
                    }

                    if (stateManagerIface != null)
                    {
                        var constructed = createMethod.MakeGenericMethod(stateManagerIface);
                        return constructed.Invoke(smLibrary, new object[] { name, parent });
                    }
                }
                catch { }
            }

            // 如果泛型不行，尝试查看是否有非泛型 Create 方法
            // 例如 ProjectItemLibrary 接口可能有 Create(string) 方法
            try
            {
                var createSimple = smLibType.GetMethod("Create", new[] { typeof(string) });
                if (createSimple != null)
                {
                    return createSimple.Invoke(smLibrary, new object[] { name });
                }
            }
            catch { }

            // 最后尝试：用 @project 创建 non-generic way
            // 使用已知有效的接口方法
            try
            {
                // Try InterfaceMapping for non-generic CreateProjectItem
                foreach (var iface in smLibType.GetInterfaces())
                {
                    var map = smLibType.GetInterfaceMap(iface);
                    for (int i = 0; i < map.InterfaceMethods.Length; i++)
                    {
                        var im = map.InterfaceMethods[i];
                        if (im.Name == "Create" && !im.IsGenericMethodDefinition && im.GetParameters().Length == 2 
                            && im.GetParameters()[0].ParameterType == typeof(string))
                        {
                            return im.Invoke(smLibrary, new object[] { name, parent });
                        }
                    }
                }
            }
            catch { }

            return null;
        }

        #endregion

        #region 内部辅助方法

        private void CacheReflectionTypes()
        {
            if (_projectType == null) return;
            var wrappedItemMethod = _projectType.GetMethod("get_WrappedItem",
                BindingFlags.Public | BindingFlags.Instance | BindingFlags.FlattenHierarchy,
                null, Type.EmptyTypes, null);
            object wrappedItem = null;
            if (wrappedItemMethod != null)
            {
                try { wrappedItem = wrappedItemMethod.Invoke(_project, null); }
                catch { }
            }
            if (wrappedItem != null)
            {
                _projectItem = wrappedItem;
                _projectItemType = wrappedItem.GetType();
            }
        }

        private object GetRootNode()
        {
            if (_project == null || _projectItem == null)
                throw new InvalidOperationException("没有打开的工程");
            return _projectItem;
        }

        private object GetProjectItem(string path)
        {
            // 方法1: GetProjectItemByKzbUrl(path, true)
            var getByKzb = FindMethod(_projectType, "GetProjectItemByKzbUrl",
                new[] { typeof(string), typeof(bool) });
            if (getByKzb != null)
            {
                try { return getByKzb.Invoke(_project, new object[] { path, true }); }
                catch { }
            }

            // 方法2: wrappedItem.GetProjectItem(path)
            if (_projectItemType != null)
            {
                var getProjItem = FindMethod(_projectItemType, "GetProjectItem", new[] { typeof(string) });
                if (getProjItem != null)
                {
                    try { return getProjItem.Invoke(_projectItem, new object[] { path }); }
                    catch { }
                }
            }

            // 方法3: Project.GetProjectItem(string)
            var getItem = FindMethod(_projectType, "GetProjectItem", new[] { typeof(string) });
            if (getItem != null)
            {
                try { return getItem.Invoke(_project, new object[] { path }); }
                catch { }
            }
            return null;
        }

        private object GetNodeByPath(string path)
        {
            if (string.IsNullOrEmpty(path) || _project == null || _projectItem == null)
                return null;

            path = path.TrimStart('/').TrimEnd('/');

            // 方法A: GetProjectItem
            var getItem = FindMethod(_projectType, "GetProjectItem", new[] { typeof(string) });
            if (getItem != null)
            {
                try
                {
                    var result = getItem.Invoke(_project, new object[] { path });
                    if (result != null) return result;
                }
                catch { }
            }

            // 方法B: GetProjectItemByKzbUrl
            var getByKzb = FindMethod(_projectType, "GetProjectItemByKzbUrl",
                new[] { typeof(string), typeof(bool) });
            if (getByKzb != null)
            {
                try
                {
                    var result = getByKzb.Invoke(_project, new object[] { path, true });
                    if (result != null) return result;
                }
                catch { }
            }

            // 方法C: _projectItemType.GetProjectItem
            if (_projectItemType != null)
            {
                var getProjItem = FindMethod(_projectItemType, "GetProjectItem", new[] { typeof(string) });
                if (getProjItem != null)
                {
                    try
                    {
                        var result = getProjItem.Invoke(_projectItem, new object[] { path });
                        if (result != null) return result;
                    }
                    catch { }
                }
            }

            // 空路径 = 根
            if (string.IsNullOrEmpty(path))
                return GetRootNode();

            // 手动遍历 Children
            var root = GetRootNode();
            if (root == null) return null;

            var rootType = root.GetType();
            var childrenProp = rootType.GetProperty("Children", BindingFlags.Public | BindingFlags.Instance);
            if (childrenProp == null)
            {
                foreach (var iface in rootType.GetInterfaces())
                {
                    childrenProp = iface.GetProperty("Children", BindingFlags.Public | BindingFlags.Instance);
                    if (childrenProp != null) break;
                }
            }
            if (childrenProp == null) return null;

            var nameProp = rootType.GetProperty("Name", BindingFlags.Public | BindingFlags.Instance);
            if (nameProp == null)
            {
                foreach (var iface in rootType.GetInterfaces())
                {
                    nameProp = iface.GetProperty("Name", BindingFlags.Public | BindingFlags.Instance);
                    if (nameProp != null) break;
                }
            }

            var parts = path.Split('/');
            object current = root;

            foreach (var part in parts)
            {
                if (string.IsNullOrEmpty(part)) continue;
                var children = childrenProp.GetValue(current) as IEnumerable;
                if (children == null) return null;

                bool found = false;
                foreach (var child in children)
                {
                    var childName = nameProp?.GetValue(child)?.ToString();
                    if (childName == part)
                    {
                        current = child;
                        found = true;
                        break;
                    }
                }
                if (!found) return null;
            }
            return current;
        }

        private string GetNodePath(object node)
        {
            var segments = new List<string>();
            var current = node;
            while (current != null)
            {
                var nameProp = current.GetType().GetProperty("Name",
                    BindingFlags.Public | BindingFlags.Instance);
                if (nameProp == null)
                {
                    foreach (var iface in current.GetType().GetInterfaces())
                    {
                        nameProp = iface.GetProperty("Name",
                            BindingFlags.Public | BindingFlags.Instance);
                        if (nameProp != null) break;
                    }
                }
                string name;
                try
                {
                    name = nameProp?.GetValue(current)?.ToString();
                }
                catch
                {
                    name = null;
                }
                if (name == null) break;
                segments.Insert(0, name);

                try
                {
                    var parentProp = current.GetType().GetProperty("Parent",
                        BindingFlags.Public | BindingFlags.Instance);
                    if (parentProp == null)
                    {
                        foreach (var iface in current.GetType().GetInterfaces())
                        {
                            parentProp = iface.GetProperty("Parent",
                                BindingFlags.Public | BindingFlags.Instance);
                            if (parentProp != null) break;
                        }
                    }
                    if (parentProp != null)
                        current = parentProp.GetValue(current);
                    else
                        current = null;
                }
                catch
                {
                    current = null;
                }
            }

            return "/" + string.Join("/", segments);
        }

        private Dictionary<string, object> SerializeNodeTree(object node)
        {
            var isProject = (node == _projectItem);

            // 纯反射获取 Name
            string nodeName = null;
            try
            {
                var nameProp = node.GetType().GetProperty("Name",
                    BindingFlags.Public | BindingFlags.Instance);
                if (nameProp == null)
                {
                    foreach (var iface in node.GetType().GetInterfaces())
                    {
                        nameProp = iface.GetProperty("Name",
                            BindingFlags.Public | BindingFlags.Instance);
                        if (nameProp != null) break;
                    }
                }
                nodeName = nameProp?.GetValue(node)?.ToString();
            }
            catch { }

            var result = new Dictionary<string, object>
            {
                ["name"] = nodeName ?? (isProject ? "(Project)" : "?"),
                ["path"] = isProject ? "/" : GetNodePath(node)
            };

            // 获取关键属性
            if (!isProject)
            {
                var interestingProps = new[] { "Text", "Width", "Height",
                    "HorizontalAlignment", "VerticalAlignment", "Background",
                    "Foreground", "FontSize", "Opacity", "Visible", "Enabled" };

                var propertiesDict = new Dictionary<string, object>();
                foreach (var prop in interestingProps)
                {
                    try
                    {
                        var val = CallNodeMethod(node, "Get", new object[] { prop });
                        if (val != null)
                            propertiesDict[prop] = val.ToString();
                    }
                    catch { }
                }
                if (propertiesDict.Count > 0)
                    result["properties"] = propertiesDict;
            }

            // 递归子节点
            try
            {
                var childrenProp = node.GetType().GetProperty("Children",
                    BindingFlags.Public | BindingFlags.Instance);
                if (childrenProp == null)
                {
                    foreach (var iface in node.GetType().GetInterfaces())
                    {
                        childrenProp = iface.GetProperty("Children",
                            BindingFlags.Public | BindingFlags.Instance);
                        if (childrenProp != null) break;
                    }
                }
                var childList = childrenProp?.GetValue(node) as IEnumerable;
                if (childList != null)
                {
                    var children = new List<object>();
                    foreach (var child in childList)
                    {
                        children.Add(SerializeNodeTree(child));
                    }
                    if (children.Count > 0)
                        result["children"] = children;
                }
            }
            catch { }

            return result;
        }

        /// <summary>
        /// 查找 ComponentType（用于 CreateComponentNode）。
        /// 纯反射：从 ComponentTypeLibrary 获取对应的 ComponentType 对象。
        /// </summary>
        /// <summary>
        /// 查找 NodeComponentType（用于 CreateNodeComponent）。
        /// 纯反射：从 NodeComponentTypeLibrary 获取对应的 NodeComponentType 对象。
        /// NodeComponentType 与 ComponentType 不同，前者是节点组件类型（如 TextBlock2D、Button3D），
        /// 后者是旧版组件类型。TypeLibrary 也存放于不同的 Library 中
        /// （NodeComponentTypeLibrary vs ComponentTypeLibrary）。
        /// </summary>
        /// <summary>
        /// 查找 ComponentType（用于 CreateComponentNode）。
        /// 纯反射：从 ComponentTypeLibrary 获取对应的 ComponentTypePluginWrapper 对象。
        /// </summary>
        private object FindComponentType(string typeName)
        {
            if (string.IsNullOrEmpty(typeName)) return null;

            try
            {
                // 处理类型名：支持 "Kanzi.TextBox2D" 和 "TextBox2D"
                var fullTypeName = typeName.Contains(".") ? typeName : $"Kanzi.{typeName}";

                // 从 project 获取 ComponentTypeLibrary
                var libProp = _projectType.GetProperty("ComponentTypeLibrary");
                if (libProp == null)
                {
                    foreach (var iface in _projectType.GetInterfaces())
                    {
                        libProp = iface.GetProperty("ComponentTypeLibrary");
                        if (libProp != null) break;
                    }
                }

                if (libProp == null && _projectItem != null)
                {
                    var piType = _projectItem.GetType();
                    libProp = piType.GetProperty("ComponentTypeLibrary");
                    if (libProp == null)
                    {
                        foreach (var iface in piType.GetInterfaces())
                        {
                            libProp = iface.GetProperty("ComponentTypeLibrary");
                            if (libProp != null) break;
                        }
                    }
                }

                if (libProp == null) return null;

                var compTypeLib = libProp.GetValue(_project);
                if (compTypeLib == null) return null;

                // 调用 GetComponentType(typeName)
                var getTypeMethod = compTypeLib.GetType().GetMethod("GetComponentType", new[] { typeof(string) });
                if (getTypeMethod == null)
                {
                    foreach (var iface in compTypeLib.GetType().GetInterfaces())
                    {
                        getTypeMethod = iface.GetMethod("GetComponentType", new[] { typeof(string) });
                        if (getTypeMethod != null) break;
                    }
                }

                if (getTypeMethod != null)
                {
                    var result = getTypeMethod.Invoke(compTypeLib, new object[] { fullTypeName });
                    if (result != null) return result;

                    // 如果没有完整名称，尝试只用简名
                    if (fullTypeName != typeName)
                    {
                        result = getTypeMethod.Invoke(compTypeLib, new object[] { typeName });
                        if (result != null) return result;
                    }
                }

                // 如果 GetComponentType 没用，遍历 Items
                var itemsProp = compTypeLib.GetType().GetProperty("Items");
                if (itemsProp == null)
                {
                    foreach (var iface in compTypeLib.GetType().GetInterfaces())
                    {
                        itemsProp = iface.GetProperty("Items");
                        if (itemsProp != null) break;
                    }
                }

                if (itemsProp != null)
                {
                    var items = itemsProp.GetValue(compTypeLib) as IEnumerable;
                    if (items != null)
                    {
                        foreach (var item in items)
                        {
                            var nameProp = item.GetType().GetProperty("Name");
                            if (nameProp == null)
                            {
                                foreach (var iface in item.GetType().GetInterfaces())
                                {
                                    nameProp = iface.GetProperty("Name");
                                    if (nameProp != null) break;
                                }
                            }
                            if (nameProp == null) continue;

                            var n = nameProp.GetValue(item)?.ToString();
                            if (string.IsNullOrEmpty(n)) continue;

                            var shortName = n.Contains('.') ? n.Substring(n.LastIndexOf('.') + 1) : n;
                            if (string.Equals(shortName, typeName, StringComparison.OrdinalIgnoreCase)
                                || string.Equals(n, fullTypeName, StringComparison.OrdinalIgnoreCase)
                                || string.Equals(n, typeName, StringComparison.OrdinalIgnoreCase))
                            {
                                return item;
                            }
                        }
                    }
                }
            }
            catch { }
            return null;
        }

        private object FindNodeComponentType(string typeName)
        {
            if (string.IsNullOrEmpty(typeName)) return null;

            try
            {
                // 从 project 获取 NodeComponentTypeLibrary
                // 可以尝试 _project（ProjectPluginWrapper）和 _projectItem（Project）
                var libProp = _projectType.GetProperty("NodeComponentTypeLibrary");
                if (libProp == null)
                {
                    foreach (var iface in _projectType.GetInterfaces())
                    {
                        libProp = iface.GetProperty("NodeComponentTypeLibrary");
                        if (libProp != null) break;
                    }
                }
                if (libProp == null && _projectItem != null)
                {
                    var piType = _projectItem.GetType();
                    libProp = piType.GetProperty("NodeComponentTypeLibrary");
                    if (libProp == null)
                    {
                        foreach (var iface in piType.GetInterfaces())
                        {
                            libProp = iface.GetProperty("NodeComponentTypeLibrary");
                            if (libProp != null) break;
                        }
                    }
                }
                if (libProp == null) return null;

                var nodeCompLib = libProp.GetValue(_project);
                if (nodeCompLib == null) return null;

                // 获取 Items 并遍历查找名称匹配的 NodeComponentType
                var itemsProp = nodeCompLib.GetType().GetProperty("Items");
                if (itemsProp == null)
                {
                    foreach (var iface in nodeCompLib.GetType().GetInterfaces())
                    {
                        itemsProp = iface.GetProperty("Items");
                        if (itemsProp != null) break;
                    }
                }
                if (itemsProp != null)
                {
                    var items = itemsProp.GetValue(nodeCompLib) as IEnumerable;
                    if (items != null)
                    {
                        foreach (var item in items)
                        {
                            var nameProp = item.GetType().GetProperty("Name");
                            if (nameProp == null) continue;
                            var n = nameProp.GetValue(item)?.ToString();
                            if (!string.IsNullOrEmpty(n))
                            {
                                // 名称格式如 "Kanzi.TextBlock2D"，支持简写或全名匹配
                                var shortName = n.Contains('.') ? n.Substring(n.LastIndexOf('.') + 1) : n;
                                if (string.Equals(shortName, typeName, StringComparison.OrdinalIgnoreCase)
                                    || string.Equals(n, typeName, StringComparison.OrdinalIgnoreCase))
                                {
                                    return item;
                                }
                            }
                        }
                    }
                }
            }
            catch { }
            return null;
        }

        private object ConvertValue(object value)
        {
            if (value == null) return null;
            string strVal = value.ToString();
            if (int.TryParse(strVal, out int intVal))
                return intVal;
            if (bool.TryParse(strVal, out bool boolVal))
                return boolVal;
            if (float.TryParse(strVal, out float floatVal))
                return floatVal;
            return strVal;
        }

        /// <summary>
        /// 在类型及其所有实现的接口上查找方法（包含继承的）
        /// </summary>
        private static MethodInfo FindMethod(Type type, string name, Type[] paramTypes)
        {
            var m = type.GetMethod(name, BindingFlags.Public | BindingFlags.Instance, null, paramTypes, null);
            if (m != null) return m;
            foreach (var iface in type.GetInterfaces())
            {
                m = iface.GetMethod(name, BindingFlags.Public | BindingFlags.Instance, null, paramTypes, null);
                if (m != null) return m;
            }

            // [临时诊断增强] 精确类型找不到时，做类型兼容匹配：
            // 实际参数类型是形参类型（或其子类/接口实现）也视为匹配。
            // 用于 CreateBinding(Property, EnumTag, String) 传子类 ColorDynamicPropertyType 等场景。
            // ⚠️ 临时 hack，问题解决后连同 @empty/@array/kz_get_* 一起还原。
            var candidates = type.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Where(c => c.Name == name && c.GetParameters().Length == paramTypes.Length && !c.IsGenericMethodDefinition)
                .ToList();
            foreach (var iface in type.GetInterfaces())
            {
                candidates.AddRange(iface.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                    .Where(c => c.Name == name && c.GetParameters().Length == paramTypes.Length && !c.IsGenericMethodDefinition));
            }
            candidates = candidates.GroupBy(c => c.ToString()).Select(g => g.First()).ToList();
            foreach (var candidate in candidates)
            {
                var pars = candidate.GetParameters();
                bool match = true;
                for (int i = 0; i < pars.Length; i++)
                {
                    var pt = pars[i].ParameterType;
                    var at = paramTypes[i];
                    if (pt.IsAssignableFrom(at)) continue;
                    match = false;
                    break;
                }
                if (match) return candidate;
            }
            return null;
        }

        /// <summary>
        /// 根据类型名称字符串查找对应的 ProjectItemType.
        /// 用于泛型方法 CreateProjectItem&lt;T&gt; 的 T 类型解析。
        /// </summary>
        /// <summary>
        /// 根据类型名称字符串查找对应的 ProjectItemType。
        /// 用于泛型方法 CreateProjectItem&lt;T&gt; 的 T 类型解析。
        /// </summary>
        private Type FindProjectItemType(object targetObj, string typeName)
        {
            if (string.IsNullOrEmpty(typeName)) return null;

            // 策略1: ProjectItemTypeLibrary.GetItemByName — 适用于视觉节点
            try
            {
                var typeLibraryProp = targetObj.GetType().GetProperty("ProjectItemTypeLibrary");
                if (typeLibraryProp == null)
                {
                    foreach (var iface in targetObj.GetType().GetInterfaces())
                    {
                        typeLibraryProp = iface.GetProperty("ProjectItemTypeLibrary");
                        if (typeLibraryProp != null) break;
                    }
                }
                if (typeLibraryProp != null)
                {
                    var typeLib = typeLibraryProp.GetValue(targetObj);
                    var getItem = typeLib?.GetType().GetMethod("GetItemByName", new[] { typeof(string) });
                    if (getItem != null)
                    {
                        var result = getItem.Invoke(typeLib, new[] { typeName });
                        if (result != null)
                            return result.GetType();
                    }
                }
            }
            catch { }

            // 策略2: 类型名映射 + Type.GetType (assemblyQualifiedName)
            var typeMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                ["StateManager"] = "Rightware.Kanzi.Studio.PluginInterface.StateManager, PluginInterface, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                ["StateGroup"] = "Rightware.Kanzi.Studio.PluginInterface.StateGroup, PluginInterface, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                ["State"] = "Rightware.Kanzi.Studio.PluginInterface.State, PluginInterface, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                ["StateObject"] = "Rightware.Kanzi.Studio.PluginInterface.StateObject, PluginInterface, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                ["StateTransition"] = "Rightware.Kanzi.Studio.PluginInterface.StateTransition, PluginInterface, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                ["Binding"] = "Rightware.Kanzi.Studio.PluginInterface.Binding, PluginInterface, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
                ["BindingHost"] = "Rightware.Kanzi.Studio.PluginInterface.BindingHost, PluginInterface, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null",
            };

            if (typeMap.TryGetValue(typeName, out var aqName))
            {
                try
                {
                    var t = Type.GetType(aqName);
                    if (t != null) return t;
                }
                catch { }
            }

            // 策略3: 在所有已加载程序集中按命名空间搜索
            try
            {
                var namespaces = new[]
                {
                    "Rightware.Kanzi.Studio.PluginInterface",
                    "Rightware.Kanzi.Tool.Logic.Project",
                    "Rightware.Kanzi.Tool.Logic.Project.Plugin"
                };
                foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    foreach (var ns in namespaces)
                    {
                        var t = asm.GetType($"{ns}.{typeName}");
                        if (t != null) return t;
                    }
                }
            }
            catch { }

            // 策略4: 遍历 ProjectItemTypeLibrary.Items 集合
            try
            {
                var typeLibraryProp = targetObj.GetType().GetProperty("ProjectItemTypeLibrary");
                if (typeLibraryProp == null)
                {
                    foreach (var iface in targetObj.GetType().GetInterfaces())
                    {
                        typeLibraryProp = iface.GetProperty("ProjectItemTypeLibrary");
                        if (typeLibraryProp != null) break;
                    }
                }
                if (typeLibraryProp != null)
                {
                    var typeLib = typeLibraryProp.GetValue(targetObj);
                    if (typeLib != null)
                    {
                        var itemsProp = typeLib.GetType().GetProperty("Items");
                        if (itemsProp != null)
                        {
                            var items = itemsProp.GetValue(typeLib) as System.Collections.IEnumerable;
                            if (items != null)
                            {
                                foreach (var item in items)
                                {
                                    var itemType = item.GetType();
                                    var itemName = itemType.GetProperty("Name")?.GetValue(item) as string;
                                    if (string.Equals(itemName, typeName, StringComparison.OrdinalIgnoreCase))
                                        return itemType;
                                }
                            }
                        }
                    }
                }
            }
            catch { }

            return null;
        }

        #endregion
    }
}
