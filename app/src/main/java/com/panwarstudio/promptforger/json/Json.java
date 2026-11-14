package com.panwarstudio.promptforger.json;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Minimal, strict JSON codec (RFC 8259) so the app ships with zero third-party dependencies.
 *
 * <p>Parsed values: {@code Map<String,Object>} (insertion-ordered), {@code List<Object>}, {@code String},
 * {@code Long} for integers, {@code Double} for other numbers, {@code Boolean}, or {@code null}.
 * The writer escapes all non-ASCII characters, so output is safe on any Windows code page.
 */
public final class Json {

    private static final int MAX_DEPTH = 64;

    private Json() {}

    public static final class ParseException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public ParseException(String message, int position) {
            super(message + " at position " + position);
        }
    }

    // ---------------------------------------------------------------- parse

    public static Object parse(String text) {
        Parser p = new Parser(text);
        p.skipWhitespace();
        Object value = p.readValue(0);
        p.skipWhitespace();
        if (p.pos != text.length()) throw new ParseException("Unexpected trailing content", p.pos);
        return value;
    }

    private static final class Parser {
        private final String s;
        private int pos;

        Parser(String s) {
            this.s = s;
        }

        void skipWhitespace() {
            while (pos < s.length()) {
                char c = s.charAt(pos);
                if (c == ' ' || c == '\t' || c == '\n' || c == '\r') pos++;
                else break;
            }
        }

        Object readValue(int depth) {
            if (depth > MAX_DEPTH) throw new ParseException("Nesting too deep", pos);
            if (pos >= s.length()) throw new ParseException("Unexpected end of input", pos);
            char c = s.charAt(pos);
            return switch (c) {
                case '{' -> readObject(depth);
                case '[' -> readArray(depth);
                case '"' -> readString();
                case 't' -> readLiteral("true", Boolean.TRUE);
                case 'f' -> readLiteral("false", Boolean.FALSE);
                case 'n' -> readLiteral("null", null);
                default -> {
                    if (c == '-' || (c >= '0' && c <= '9')) yield readNumber();
                    throw new ParseException("Unexpected character '" + c + "'", pos);
                }
            };
        }

        private Object readLiteral(String word, Object value) {
            if (!s.startsWith(word, pos)) throw new ParseException("Invalid literal", pos);
            pos += word.length();
            return value;
        }

        private Map<String, Object> readObject(int depth) {
            Map<String, Object> map = new LinkedHashMap<>();
            pos++; // {
            skipWhitespace();
            if (peek() == '}') {
                pos++;
                return map;
            }
            while (true) {
                skipWhitespace();
                if (peek() != '"') throw new ParseException("Expected string key", pos);
                String key = readString();
                skipWhitespace();
                expect(':');
                skipWhitespace();
                map.put(key, readValue(depth + 1));
                skipWhitespace();
                char c = next();
                if (c == '}') return map;
                if (c != ',') throw new ParseException("Expected ',' or '}'", pos - 1);
            }
        }

        private List<Object> readArray(int depth) {
            List<Object> list = new ArrayList<>();
            pos++; // [
            skipWhitespace();
            if (peek() == ']') {
                pos++;
                return list;
            }
            while (true) {
                skipWhitespace();
                list.add(readValue(depth + 1));
                skipWhitespace();
                char c = next();
                if (c == ']') return list;
                if (c != ',') throw new ParseException("Expected ',' or ']'", pos - 1);
            }
        }

        private String readString() {
            expect('"');
            StringBuilder sb = new StringBuilder();
            while (true) {
                if (pos >= s.length()) throw new ParseException("Unterminated string", pos);
                char c = s.charAt(pos++);
                if (c == '"') return sb.toString();
                if (c < 0x20) throw new ParseException("Control character in string", pos - 1);
                if (c != '\\') {
                    sb.append(c);
                    continue;
                }
                char e = next();
                switch (e) {
                    case '"', '\\', '/' -> sb.append(e);
                    case 'b' -> sb.append('\b');
                    case 'f' -> sb.append('\f');
                    case 'n' -> sb.append('\n');
                    case 'r' -> sb.append('\r');
                    case 't' -> sb.append('\t');
                    case 'u' -> {
                        if (pos + 4 > s.length()) throw new ParseException("Bad unicode escape", pos);
                        try {
                            sb.append((char) Integer.parseInt(s.substring(pos, pos + 4), 16));
                        } catch (NumberFormatException ex) {
                            throw new ParseException("Bad unicode escape", pos);
                        }
                        pos += 4;
                    }
                    default -> throw new ParseException("Bad escape '\\" + e + "'", pos - 1);
                }
            }
        }

        private Object readNumber() {
            int start = pos;
            if (peek() == '-') pos++;
            boolean integral = true;
            while (pos < s.length()) {
                char c = s.charAt(pos);
                if (c >= '0' && c <= '9') pos++;
                else if (c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-') {
                    integral = false;
                    pos++;
                } else break;
            }
            String num = s.substring(start, pos);
            try {
                if (integral) return Long.parseLong(num);
                return Double.parseDouble(num);
            } catch (NumberFormatException ex) {
                throw new ParseException("Invalid number '" + num + "'", start);
            }
        }

        private char peek() {
            if (pos >= s.length()) throw new ParseException("Unexpected end of input", pos);
            return s.charAt(pos);
        }

        private char next() {
            char c = peek();
            pos++;
            return c;
        }

        private void expect(char c) {
            if (next() != c) throw new ParseException("Expected '" + c + "'", pos - 1);
        }
    }

    // ---------------------------------------------------------------- write

    public static String write(Object value) {
        StringBuilder sb = new StringBuilder();
        write(sb, value, -1, 0);
        return sb.toString();
    }

    /** Pretty-printed with two-space indentation. */
    public static String writePretty(Object value) {
        StringBuilder sb = new StringBuilder();
        write(sb, value, 2, 0);
        return sb.toString();
    }

    private static void write(StringBuilder sb, Object v, int indent, int level) {
        switch (v) {
            case null -> sb.append("null");
            case String str -> writeString(sb, str);
            case Boolean b -> sb.append(b);
            case Integer i -> sb.append(i);
            case Long l -> sb.append(l);
            case Double d -> {
                if (d.isNaN() || d.isInfinite()) throw new IllegalArgumentException("Non-finite number");
                sb.append(d);
            }
            case Map<?, ?> map -> {
                sb.append('{');
                boolean first = true;
                for (Map.Entry<?, ?> e : map.entrySet()) {
                    if (!first) sb.append(',');
                    first = false;
                    newline(sb, indent, level + 1);
                    writeString(sb, String.valueOf(e.getKey()));
                    sb.append(indent >= 0 ? ": " : ":");
                    write(sb, e.getValue(), indent, level + 1);
                }
                if (!map.isEmpty()) newline(sb, indent, level);
                sb.append('}');
            }
            case List<?> list -> {
                sb.append('[');
                for (int i = 0; i < list.size(); i++) {
                    if (i > 0) sb.append(',');
                    newline(sb, indent, level + 1);
                    write(sb, list.get(i), indent, level + 1);
                }
                if (!list.isEmpty()) newline(sb, indent, level);
                sb.append(']');
            }
            default -> throw new IllegalArgumentException("Unsupported JSON type: " + v.getClass().getName());
        }
    }

    private static void newline(StringBuilder sb, int indent, int level) {
        if (indent < 0) return;
        sb.append('\n');
        sb.append(" ".repeat(indent * level));
    }

    private static void writeString(StringBuilder sb, String s) {
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20 || c > 0x7e) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
                }
            }
        }
        sb.append('"');
    }

    // ---------------------------------------------------------------- typed access helpers

    @SuppressWarnings("unchecked")
    public static Map<String, Object> asObject(Object v, String what) {
        if (v instanceof Map<?, ?> m) return (Map<String, Object>) m;
        throw new IllegalArgumentException(what + " must be a JSON object");
    }

    public static List<Object> asList(Object v, String what) {
        if (v == null) return Collections.emptyList();
        if (v instanceof List<?> l) return Collections.unmodifiableList(new ArrayList<>(l));
        throw new IllegalArgumentException(what + " must be a JSON array");
    }

    public static String asString(Object v, String what) {
        if (v instanceof String str) return str;
        throw new IllegalArgumentException(what + " must be a string");
    }

    public static String optString(Map<String, Object> m, String key, String fallback) {
        return m.get(key) instanceof String str ? str : fallback;
    }
}
