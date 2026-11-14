package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Either generated files with a quality report, or per-field validation errors from the engine. */
public sealed interface ForgeResult {

    record Finding(String level, String field, String message) {
        public boolean isWarning() {
            return "warning".equals(level);
        }
    }

    record Dimension(String name, int score, String hint) {}

    record Quality(int score, String grade, List<Finding> findings, List<Dimension> dimensions) {
        public Quality {
            findings = List.copyOf(findings);
            dimensions = List.copyOf(dimensions);
        }
    }

    record Success(List<ForgeFile> files, List<String> warnings, Quality quality, String explanation,
                   List<String> variables) implements ForgeResult {
        public Success {
            files = List.copyOf(files);
            warnings = List.copyOf(warnings);
            variables = List.copyOf(variables);
        }
    }

    record Invalid(Map<String, String> errors) implements ForgeResult {
        public Invalid {
            errors = Map.copyOf(errors);
        }
    }

    static ForgeResult fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "result");
        if (Boolean.TRUE.equals(m.get("ok"))) {
            List<ForgeFile> files = Json.asList(m.get("files"), "files").stream().map(ForgeFile::fromJson).toList();
            List<String> warnings = strings(m.get("warnings"));
            Quality quality = new Quality(100, "Excellent", List.of(), List.of());
            if (m.get("quality") instanceof Map<?, ?> q) {
                Map<String, Object> qm = Json.asObject(q, "quality");
                int score = qm.get("score") instanceof Long l ? l.intValue() : 0;
                List<Finding> findings = Json.asList(qm.get("findings"), "findings").stream()
                        .map(f -> Json.asObject(f, "finding"))
                        .map(f -> new Finding(Json.optString(f, "level", "tip"), Json.optString(f, "field", ""),
                                Json.optString(f, "message", "")))
                        .toList();
                List<Dimension> dims = Json.asList(qm.get("dimensions"), "dimensions").stream()
                        .map(d -> Json.asObject(d, "dimension"))
                        .map(d -> new Dimension(Json.optString(d, "name", ""),
                                d.get("score") instanceof Long l ? l.intValue() : 0, Json.optString(d, "hint", "")))
                        .toList();
                quality = new Quality(score, Json.optString(qm, "grade", ""), findings, dims);
            }
            return new Success(files, warnings, quality, Json.optString(m, "explanation", ""), strings(m.get("variables")));
        }
        Map<String, String> errors = new LinkedHashMap<>();
        Json.asObject(m.getOrDefault("errors", Map.of()), "errors").forEach((k, v) -> errors.put(k, String.valueOf(v)));
        return new Invalid(errors);
    }

    private static List<String> strings(Object list) {
        return Json.asList(list, "list").stream().map(String::valueOf).toList();
    }
}
