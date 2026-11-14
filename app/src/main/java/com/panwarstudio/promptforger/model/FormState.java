package com.panwarstudio.promptforger.model;

import com.panwarstudio.promptforger.json.Json;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Raw form exactly as the user typed it. Every value is text; the Python engine owns validation,
 * so the UI and engine can never disagree about the rules.
 */
public record FormState(
        String role,
        String task,
        String steps,
        String context,
        String constraints,
        String successCriteria,
        String examples,
        String outputSchema,
        String variables,
        String tools,
        String format,
        String model,
        String verbosity,
        String tokenBudget,
        String maxIterations) {

    public static final FormState DEFAULT = new FormState(
            "", "", "", "", "", "", "", "", "", "", "standard", "claude-sonnet", "balanced", "", "");

    public static final FormState EXAMPLE = new FormState(
            "senior backend engineer",
            "Build a REST API for a todo app with JWT authentication, using Node.js, Express and PostgreSQL.",
            "Design the database schema\nImplement auth (register, login, refresh)\nBuild CRUD endpoints for todos\nAdd validation and error handling\nWrite integration tests",
            "The repo already uses TypeScript, Prisma and Vitest. Follow the existing folder structure.",
            "Never store plain-text passwords\nNo new dependencies without a reason",
            "All integration tests pass\nEvery endpoint returns typed errors with status codes",
            "",
            "",
            "",
            "",
            "ralph",
            "claude-sonnet",
            "balanced",
            "2000",
            "25");

    public FormState {
        Objects.requireNonNull(role);
        Objects.requireNonNull(task);
        Objects.requireNonNull(steps);
        Objects.requireNonNull(context);
        Objects.requireNonNull(constraints);
        Objects.requireNonNull(successCriteria);
        Objects.requireNonNull(examples);
        Objects.requireNonNull(outputSchema);
        Objects.requireNonNull(variables);
        Objects.requireNonNull(tools);
        Objects.requireNonNull(format);
        Objects.requireNonNull(model);
        Objects.requireNonNull(verbosity);
        Objects.requireNonNull(tokenBudget);
        Objects.requireNonNull(maxIterations);
    }

    public Map<String, Object> toJson() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("role", role);
        m.put("task", task);
        m.put("steps", steps);
        m.put("context", context);
        m.put("constraints", constraints);
        m.put("successCriteria", successCriteria);
        m.put("examples", examples);
        m.put("outputSchema", outputSchema);
        m.put("variables", variables);
        m.put("tools", tools);
        m.put("format", format);
        m.put("model", model);
        m.put("verbosity", verbosity);
        m.put("tokenBudget", tokenBudget);
        m.put("maxIterations", maxIterations);
        return m;
    }

    /** Lenient: missing or wrong-typed fields fall back to defaults (old drafts and presets still load). */
    public static FormState fromJson(Object value) {
        Map<String, Object> m = Json.asObject(value, "form");
        FormState d = DEFAULT;
        return new FormState(
                Json.optString(m, "role", d.role),
                Json.optString(m, "task", d.task),
                Json.optString(m, "steps", d.steps),
                Json.optString(m, "context", d.context),
                Json.optString(m, "constraints", d.constraints),
                Json.optString(m, "successCriteria", d.successCriteria),
                Json.optString(m, "examples", d.examples),
                Json.optString(m, "outputSchema", d.outputSchema),
                Json.optString(m, "variables", d.variables),
                Json.optString(m, "tools", d.tools),
                Json.optString(m, "format", d.format),
                Json.optString(m, "model", d.model),
                Json.optString(m, "verbosity", d.verbosity),
                Json.optString(m, "tokenBudget", d.tokenBudget),
                Json.optString(m, "maxIterations", d.maxIterations));
    }

    /** Clears the content but keeps the user's settings (format, model, verbosity). */
    public FormState cleared() {
        return new FormState("", "", "", "", "", "", "", "", "", "", format, model, verbosity, "", "");
    }

    public boolean isLoop() {
        return "ralph".equals(format) || "graph".equals(format);
    }
}
