package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import com.panwarstudio.promptforger.model.FormState;
import java.util.List;
import java.util.Map;

/** An enhanced form plus every change made, so the user can review before applying. */
public record EnhanceResult(FormState form, List<Change> changes, List<String> needsYou, int before, int after,
                            String source, List<String> notes) {

    public record Change(String field, String action, String summary, String before, String after) {}

    static EnhanceResult fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "enhance");
        List<Change> changes = Json.asList(m.get("changes"), "changes").stream()
                .map(c -> Json.asObject(c, "change"))
                .map(c -> new Change(Json.optString(c, "field", ""), Json.optString(c, "action", ""),
                        Json.optString(c, "summary", ""), Json.optString(c, "before", ""), Json.optString(c, "after", "")))
                .toList();
        return new EnhanceResult(
                FormState.fromJson(m.get("form")), changes,
                Json.asList(m.get("needsYou"), "needsYou").stream().map(String::valueOf).toList(),
                m.get("before") instanceof Long b ? b.intValue() : 0,
                m.get("after") instanceof Long a ? a.intValue() : 0,
                Json.optString(m, "source", "offline"),
                Json.asList(m.get("notes"), "notes").stream().map(String::valueOf).toList());
    }
}
