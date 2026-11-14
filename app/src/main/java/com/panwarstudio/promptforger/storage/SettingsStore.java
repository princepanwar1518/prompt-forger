package com.panwarstudio.promptforger.storage;

import com.panwarstudio.promptforger.engine.AiSettings;
import com.panwarstudio.promptforger.json.Json;
import com.panwarstudio.promptforger.model.FormState;
import java.io.IOException;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/** Small app state: theme, AI settings (no secrets) and the unsaved draft, so closing never loses work. */
public final class SettingsStore {

    public enum Theme { SYSTEM, LIGHT, DARK }

    public record Settings(Theme theme, FormState draft, AiSettings ai) {
        public Settings withAi(AiSettings next) {
            return new Settings(theme, draft, next);
        }
    }

    private final JsonFile file;

    public SettingsStore(Path dataDir) {
        this.file = new JsonFile(dataDir.resolve("settings.json"));
    }

    public synchronized Settings load() {
        try {
            Object raw = file.read().orElse(null);
            if (raw == null) return new Settings(Theme.SYSTEM, FormState.DEFAULT, AiSettings.DEFAULT);
            Map<String, Object> m = Json.asObject(raw, "settings");
            Theme theme;
            try {
                theme = Theme.valueOf(Json.optString(m, "theme", "SYSTEM"));
            } catch (IllegalArgumentException e) {
                theme = Theme.SYSTEM;
            }
            FormState draft = m.get("draft") instanceof Map<?, ?> d ? FormState.fromJson(d) : FormState.DEFAULT;
            return new Settings(theme, draft, AiSettings.fromJson(m.get("ai")));
        } catch (IOException | RuntimeException e) {
            return new Settings(Theme.SYSTEM, FormState.DEFAULT, AiSettings.DEFAULT);
        }
    }

    public synchronized void save(Settings settings) throws IOException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("theme", settings.theme().name());
        m.put("draft", settings.draft().toJson());
        m.put("ai", settings.ai().toJson());
        file.write(m);
    }
}
