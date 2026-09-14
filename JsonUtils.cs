using System;
using System.Collections.Generic;
using System.Text;

namespace KzMCPChatPlugin
{
    /// <summary>
    /// 简易 JSON 序列化/反序列化（避免引入第三方库）
    /// </summary>
    internal static class JsonUtils
    {
        public static string Serialize(object obj)
        {
            if (obj == null) return "null";
            if (obj is string s) return EscapeString(s);
            if (obj is bool b) return b ? "true" : "false";
            if (obj is int || obj is long || obj is float || obj is double || obj is decimal)
                return obj.ToString().Replace(',', '.');
            if (obj is Dictionary<string, object> dict)
                return SerializeDict(dict);
            if (obj is List<object> listVal)
                return SerializeList(listVal);
            if (obj.GetType().IsArray)
            {
                var arr = (Array)obj;
                var list = new List<object>();
                foreach (var item in arr) list.Add(item);
                return SerializeList(list);
            }
            // 匿名类型：反射属性
            var props = obj.GetType().GetProperties();
            var d = new Dictionary<string, object>();
            foreach (var p in props)
                d[p.Name] = p.GetValue(obj);
            return SerializeDict(d);
        }

        private static string SerializeDict(Dictionary<string, object> dict)
        {
            var sb = new StringBuilder("{");
            bool first = true;
            foreach (var kv in dict)
            {
                if (!first) sb.Append(",");
                first = false;
                sb.Append(EscapeString(kv.Key));
                sb.Append(":");
                sb.Append(Serialize(kv.Value));
            }
            sb.Append("}");
            return sb.ToString();
        }

        private static string SerializeList(List<object> list)
        {
            var sb = new StringBuilder("[");
            bool first = true;
            foreach (var item in list)
            {
                if (!first) sb.Append(",");
                first = false;
                sb.Append(Serialize(item));
            }
            sb.Append("]");
            return sb.ToString();
        }

        private static string EscapeString(string s)
        {
            if (s == null) return "null";
            var sb = new StringBuilder();
            sb.Append('"');
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20)
                            sb.Append($"\\u{(int)c:X4}");
                        else
                            sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
            return sb.ToString();
        }

        // ── 反序列化 ──

        public static Dictionary<string, object> Deserialize(string json)
        {
            if (string.IsNullOrEmpty(json)) return null;
            json = json.Trim();
            if (!json.StartsWith("{") || !json.EndsWith("}")) return null;
            var result = new Dictionary<string, object>();
            json = json.Substring(1, json.Length - 2);
            int i = 0;
            while (i < json.Length)
            {
                SkipWs(json, ref i);
                if (i >= json.Length || json[i] != '"') break;
                string key = ReadString(json, ref i);
                SkipWs(json, ref i);
                if (i >= json.Length || json[i] != ':') break;
                i++; // skip ':'
                SkipWs(json, ref i);
                var val = ReadValue(json, ref i);
                result[key] = val;
                SkipWs(json, ref i);
                if (i < json.Length && json[i] == ',') i++;
            }
            return result;
        }

        public static List<object> DeserializeArray(string json)
        {
            if (string.IsNullOrEmpty(json)) return null;
            json = json.Trim();
            if (!json.StartsWith("[") || !json.EndsWith("]")) return null;
            var result = new List<object>();
            json = json.Substring(1, json.Length - 2);
            int i = 0;
            while (i < json.Length)
            {
                SkipWs(json, ref i);
                if (i >= json.Length) break;
                var val = ReadValue(json, ref i);
                result.Add(val);
                SkipWs(json, ref i);
                if (i < json.Length && json[i] == ',') i++;
            }
            return result;
        }

        private static void SkipWs(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        private static string ReadString(string s, ref int i)
        {
            if (s[i] != '"') return "";
            int start = i + 1;
            i = start;
            while (i < s.Length)
            {
                if (s[i] == '\\') i += 2;
                else if (s[i] == '"') break;
                else i++;
            }
            string raw = s.Substring(start, i - start);
            i++; // skip closing quote
            return Unescape(raw);
        }

        private static string Unescape(string s)
        {
            if (string.IsNullOrEmpty(s) || !s.Contains("\\")) return s;
            var sb = new StringBuilder(s.Length);
            for (int j = 0; j < s.Length; j++)
            {
                if (s[j] == '\\' && j + 1 < s.Length)
                {
                    char n = s[j + 1];
                    switch (n)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (j + 5 < s.Length && int.TryParse(s.Substring(j + 2, 4),
                                System.Globalization.NumberStyles.HexNumber, null, out int c))
                            {
                                sb.Append((char)c);
                                j += 5;
                                continue;
                            }
                            break;
                        default: sb.Append(n); break;
                    }
                    j++;
                }
                else
                {
                    sb.Append(s[j]);
                }
            }
            return sb.ToString();
        }

        private static object ReadValue(string s, ref int i)
        {
            if (i >= s.Length) return null;
            char c = s[i];
            if (c == '"') return ReadString(s, ref i);
            if (c == '{')
            {
                int depth = 1, start = i;
                i++;
                while (i < s.Length && depth > 0)
                {
                    if (s[i] == '{' || s[i] == '[') depth++;
                    else if (s[i] == '}' || s[i] == ']') depth--;
                    i++;
                }
                return Deserialize(s.Substring(start, i - start));
            }
            if (c == '[')
            {
                int depth = 1, start = i;
                i++;
                while (i < s.Length && depth > 0)
                {
                    if (s[i] == '{' || s[i] == '[') depth++;
                    else if (s[i] == '}' || s[i] == ']') depth--;
                    i++;
                }
                return DeserializeArray(s.Substring(start, i - start));
            }
            // 数字/布尔/null
            int vs = i;
            while (i < s.Length && s[i] != ',' && s[i] != '}' && s[i] != ']' && !char.IsWhiteSpace(s[i])) i++;
            string seg = s.Substring(vs, i - vs);
            if (seg == "true") return true;
            if (seg == "false") return false;
            if (seg == "null") return null;
            if (long.TryParse(seg, out long l)) return l;
            if (double.TryParse(seg,
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out double d))
                return d;
            return seg;
        }

        // ── 便捷访问 ──

        public static string GetStr(Dictionary<string, object> d, string key, string def = "")
        {
            if (d == null) return def;
            return d.TryGetValue(key, out var v) ? v?.ToString() ?? def : def;
        }

        public static long GetInt(Dictionary<string, object> d, string key, long def = -1)
        {
            if (d == null) return def;
            if (d.TryGetValue(key, out var v))
            {
                if (v is long l) return l;
                if (v is int iv) return iv;
                if (long.TryParse(v?.ToString(), out l)) return l;
            }
            return def;
        }

        /// <summary>取原始值(不做类型强转): 用于 JSON-RPC id 这类"整数/字符串都合法"的字段,
        /// 保证原样透传, 避免字符串 id 被按整数解析失败而落成默认值。</summary>
        public static object GetRaw(Dictionary<string, object> d, string key, object def = null)
        {
            if (d == null) return def;
            return d.TryGetValue(key, out var v) ? v : def;
        }

        public static Dictionary<string, object> GetDict(Dictionary<string, object> d, string key, bool create = true)
        {
            if (d == null) return create ? new Dictionary<string, object>() : null;
            if (d.TryGetValue(key, out var v) && v is Dictionary<string, object> dict)
                return dict;
            return create ? new Dictionary<string, object>() : null;
        }

        public static List<object> GetList(Dictionary<string, object> d, string key)
        {
            if (d == null) return new List<object>();
            if (d.TryGetValue(key, out var v) && v is List<object> list)
                return list;
            return new List<object>();
        }
    }
}
