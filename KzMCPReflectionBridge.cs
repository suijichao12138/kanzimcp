using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
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

        // ====== 对象引用缓存 ======
        private readonly Dictionary<string, object> _objectStore = new Dictionary<string, object>();
        private readonly Dictionary<object, string> _objectToRefId = new Dictionary<object, string>();
        private long _nextRefId = 1;

        // ====== 构造函数 ======
        public KzMCPReflectionBridge(KanziStudio studio)
        {
            _studio = studio ?? throw new ArgumentNullException(nameof(studio));
            _project = _studio.ActiveProject;
            _projectType = _project?.GetType();
            if (_project != null)
                CacheReflectionTypes();
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
                if (_objectStore.TryGetValue(refOrPath, out var obj))
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

        #endregion 对象引用管理

        #region 通用反射调用

        /// <summary>
        /// 通用反射调用：在任意目标上调用任意方法。
        /// target 支持: "@refId", "@studio", "@project", "@projectItem", "/path/to/node"
        /// </summary>
        public object Invoke(string target, string method, object[] args)
        {
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
            object targetObj;
            if (target == "studio" || target == "@studio")
                targetObj = _studio;
            else if (target == "project" || target == "@project")
                targetObj = _project;
            else if (target == "projectItem" || target == "@projectItem")
                targetObj = _projectItem;
            else
                targetObj = ResolveObject(target);

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
                    return WrapResult(rawResult);
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
                                return WrapResult(rawResult);
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
                                    return WrapResult(rawResult);
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
                                        return WrapResult(rawResult);
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
                                                return WrapResult(rawResult);
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
                                            return WrapResult(rawResult);
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
                                        return WrapResult(rawResult);
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
                return WrapResult(rawResult);
            }
            catch (TargetInvocationException tie)
            {
                throw new InvalidOperationException($"调用 {method} 失败: {tie.InnerException?.Message ?? tie.Message}");
            }
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
                if (s.StartsWith("@") && _objectStore.ContainsKey(s))
                {
                    var resolved = _objectStore[s];
                    // 对 RuntimeType 对象，保持为字符串引用而不是提前解析
                    // 这样泛型方法匹配时能识别第一参为类型名字符串
                    if (resolved is Type)
                        return s;
                    return resolved;
                }
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

        #endregion 便捷操作

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
