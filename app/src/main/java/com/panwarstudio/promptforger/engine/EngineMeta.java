package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import java.util.List;
import java.util.Map;

/** Option lists published by the engine, so labels and hints live in one place. */
public record EngineMeta(List<Option> formats, List<Option> models, List<Option> verbosity, List<Option> providers) {

    public record Option(String id, String label, String hint) {
        @Override
        public String toString() {
            return label;
        }
    }

    static EngineMeta fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "meta");
        return new EngineMeta(options(m.get("formats")), options(m.get("models")), options(m.get("verbosity")),
                options(m.get("providers")));
    }

    private static List<Option> options(Object list) {
        return Json.asList(list, "options").stream()
                .map(o -> Json.asObject(o, "option"))
                .map(o -> new Option(
                        Json.asString(o.get("id"), "option.id"),
                        Json.asString(o.get("label"), "option.label"),
                        Json.optString(o, "hint", "")))
                .toList();
    }
}
