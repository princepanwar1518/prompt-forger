package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import com.panwarstudio.promptforger.model.FormState;
import java.util.List;
import java.util.Map;

/** What "Describe it" proposed: a merged form, which fields it filled, and any clarifying questions. */
public record DescribeResult(FormState form, List<String> filled, List<String> questions, double confidence,
                             String source, List<String> notes) {

    static DescribeResult fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "describe");
        double conf = m.get("confidence") instanceof Double d ? d : m.get("confidence") instanceof Long l ? l : 0;
        return new DescribeResult(
                FormState.fromJson(m.get("form")),
                Json.asList(m.get("filled"), "filled").stream().map(String::valueOf).toList(),
                Json.asList(m.get("questions"), "questions").stream().map(String::valueOf).toList(),
                conf,
                Json.optString(m, "source", "rules"),
                Json.asList(m.get("notes"), "notes").stream().map(String::valueOf).toList());
    }
}
