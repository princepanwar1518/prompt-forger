package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import java.util.LinkedHashMap;
import java.util.Map;

/** Non-secret AI settings. API keys live in the OS keychain, managed by the engine. */
public record AiSettings(String provider, String anthropicModel, String openaiModel, String ollamaModel, String ollamaUrl) {

    public static final AiSettings DEFAULT =
            new AiSettings("rules", "claude-haiku-5-5", "gpt-4o-mini", "llama3.2", "http://localhost:11434");

    public String modelFor(String p) {
        return switch (p) {
            case "anthropic" -> anthropicModel;
            case "openai" -> openaiModel;
            case "ollama" -> ollamaModel;
            default -> "";
        };
    }

    /** Request params the engine expects for a given provider. */
    public Map<String, Object> params(String p) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("provider", p);
        m.put("model", modelFor(p));
        m.put("ollamaUrl", ollamaUrl);
        return m;
    }

    public AiSettings withProvider(String p) {
        return new AiSettings(p, anthropicModel, openaiModel, ollamaModel, ollamaUrl);
    }

    public Map<String, Object> toJson() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("provider", provider);
        m.put("anthropicModel", anthropicModel);
        m.put("openaiModel", openaiModel);
        m.put("ollamaModel", ollamaModel);
        m.put("ollamaUrl", ollamaUrl);
        return m;
    }

    public static AiSettings fromJson(Object value) {
        if (!(value instanceof Map<?, ?>)) return DEFAULT;
        Map<String, Object> m = Json.asObject(value, "ai");
        AiSettings d = DEFAULT;
        return new AiSettings(
                Json.optString(m, "provider", d.provider),
                Json.optString(m, "anthropicModel", d.anthropicModel),
                Json.optString(m, "openaiModel", d.openaiModel),
                Json.optString(m, "ollamaModel", d.ollamaModel),
                Json.optString(m, "ollamaUrl", d.ollamaUrl));
    }
}
