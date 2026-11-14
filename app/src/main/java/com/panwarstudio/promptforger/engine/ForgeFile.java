package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import java.util.Map;

/** One generated file. {@code path} is relative and may contain folders (e.g. .claude/agents/x.md). */
public record ForgeFile(String path, String language, String description, String content) {

    static ForgeFile fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "file");
        return new ForgeFile(
                Json.asString(m.get("path"), "file.path"),
                Json.optString(m, "language", "markdown"),
                Json.optString(m, "description", ""),
                Json.asString(m.get("content"), "file.content"));
    }

    public String fileName() {
        int slash = path.lastIndexOf('/');
        return slash >= 0 ? path.substring(slash + 1) : path;
    }

    /** Same rough heuristic as the engine: ~4 characters per token. */
    public int estimatedTokens() {
        return content.isEmpty() ? 0 : (content.length() + 3) / 4;
    }
}
