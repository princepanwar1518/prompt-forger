package com.panwarstudio.promptforger.model;

import com.panwarstudio.promptforger.json.Json;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

public record Preset(String id, String name, FormState form, long updatedAt) {

    public static final int MAX_NAME = 80;

    public Preset {
        Objects.requireNonNull(id);
        Objects.requireNonNull(form);
        name = Objects.requireNonNull(name).strip();
        if (name.isEmpty() || name.length() > MAX_NAME) {
            throw new IllegalArgumentException("Preset name must be 1-" + MAX_NAME + " characters.");
        }
    }

    public Map<String, Object> toJson() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("name", name);
        m.put("form", form.toJson());
        m.put("updatedAt", updatedAt);
        return m;
    }

    public static Preset fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "preset");
        long updated = m.get("updatedAt") instanceof Long l ? l : 0L;
        return new Preset(
                Json.asString(m.get("id"), "id"),
                Json.asString(m.get("name"), "name"),
                FormState.fromJson(m.get("form")),
                updated);
    }

    @Override
    public String toString() {
        return name; // shown by ComboBox
    }
}
