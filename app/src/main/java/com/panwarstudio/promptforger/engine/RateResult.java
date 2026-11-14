package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import java.util.List;
import java.util.Map;

/** How well an AI reply met the brief. accuracy is null when nothing could be checked. */
public record RateResult(Integer accuracy, int passed, int checked, int total, int coverage, String verdict,
                         String summary, String judge, List<Check> checks) {

    /** passed is null when the check needs an AI judge and none was used. */
    public record Check(String kind, String item, Boolean passed, String reason, String how) {}

    static RateResult fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "rate");
        List<Check> checks = Json.asList(m.get("checks"), "checks").stream()
                .map(c -> Json.asObject(c, "check"))
                .map(c -> new Check(Json.optString(c, "kind", ""), Json.optString(c, "item", ""),
                        c.get("passed") instanceof Boolean b ? b : null,
                        Json.optString(c, "reason", ""), Json.optString(c, "how", "")))
                .toList();
        return new RateResult(
                m.get("accuracy") instanceof Long a ? a.intValue() : null,
                intOf(m, "passed"), intOf(m, "checked"), intOf(m, "total"), intOf(m, "coverage"),
                Json.optString(m, "verdict", ""), Json.optString(m, "summary", ""), Json.optString(m, "judge", "offline"),
                checks);
    }

    private static int intOf(Map<String, Object> m, String key) {
        return m.get(key) instanceof Long l ? l.intValue() : 0;
    }
}
