package com.panwarstudio.promptforger.engine;

import com.panwarstudio.promptforger.json.Json;
import com.panwarstudio.promptforger.model.FormState;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Supplier;

/**
 * Talks to the long-lived Python engine over JSON lines (one request / one response per line).
 * Thread-safe. Restarts the engine if it dies, with a cap so a crash loop can't spin forever.
 */
public final class EngineClient implements AutoCloseable {

    private static final Duration STARTUP_TIMEOUT = Duration.ofSeconds(20);
    private static final Duration REQUEST_TIMEOUT = Duration.ofSeconds(10);
    /** AI calls go over the network and can be slow (local models especially). */
    private static final Duration AI_TIMEOUT = Duration.ofSeconds(150);
    private static final int MAX_RESTARTS_PER_MINUTE = 3;
    private static final int STDERR_TAIL_LINES = 40;

    private final Supplier<EngineLocator.EngineCommand> locator;
    private final Map<Long, CompletableFuture<Object>> pending = new ConcurrentHashMap<>();
    private final AtomicLong ids = new AtomicLong();
    private final Deque<String> stderrTail = new ArrayDeque<>();
    private final Deque<Long> restarts = new ArrayDeque<>();

    private Process process;
    private BufferedWriter writer;
    private EngineLocator.EngineCommand command;
    private boolean freshStart;
    private volatile boolean closed;

    public EngineClient() {
        this(EngineLocator::locate);
    }

    public EngineClient(Supplier<EngineLocator.EngineCommand> locator) {
        this.locator = locator;
    }

    // ------------------------------------------------------------------ public API

    public CompletableFuture<EngineMeta> meta() {
        return request("meta", null).thenApply(EngineMeta::fromJson);
    }

    public CompletableFuture<ForgeResult> forge(FormState form) {
        return request("forge", form.toJson()).thenApply(ForgeResult::fromJson);
    }

    /** answers: question/answer pairs from the clarifying-questions dialog (may be empty). */
    public CompletableFuture<DescribeResult> describe(String text, List<Map.Entry<String, String>> answers, AiSettings ai,
                                                      FormState current) {
        Map<String, Object> params = new LinkedHashMap<>(ai.params(ai.provider()));
        params.put("text", text);
        List<Object> qa = new java.util.ArrayList<>();
        for (Map.Entry<String, String> e : answers) {
            Map<String, Object> pair = new LinkedHashMap<>();
            pair.put("question", e.getKey());
            pair.put("answer", e.getValue());
            qa.add(pair);
        }
        params.put("answers", qa);
        params.put("form", current.toJson());
        return request("describe", params, AI_TIMEOUT).thenApply(DescribeResult::fromJson);
    }

    /** "Test it": runs a prompt against the chosen provider and returns the reply text. */
    public CompletableFuture<String> run(String prompt, String input, AiSettings ai) {
        Map<String, Object> params = new LinkedHashMap<>(ai.params(ai.provider()));
        params.put("prompt", prompt);
        params.put("input", input);
        return request("run", params, AI_TIMEOUT).thenApply(r -> Json.optString(Json.asObject(r, "run"), "reply", ""));
    }

    /** Exact token count (Claude only); completes with null for providers without a counting endpoint. */
    public CompletableFuture<Long> exactTokens(String text, AiSettings ai) {
        Map<String, Object> params = new LinkedHashMap<>(ai.params(ai.provider()));
        params.put("text", text);
        return request("tokens", params, AI_TIMEOUT).thenApply(r -> Json.asObject(r, "tokens").get("tokens") instanceof Long l ? l : null);
    }

    public CompletableFuture<Map<String, Object>> keyStatus() {
        return request("keys.status", null).thenApply(r -> Json.asObject(r, "keys"));
    }

    public CompletableFuture<Map<String, Object>> setKey(String provider, String key) {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("provider", provider);
        params.put("key", key);
        return request("keys.set", params).thenApply(r -> Json.asObject(r, "keys"));
    }

    public CompletableFuture<Map<String, Object>> deleteKey(String provider) {
        return request("keys.delete", Map.of("provider", provider)).thenApply(r -> Json.asObject(r, "keys"));
    }

    public CompletableFuture<String> ping() {
        return request("ping", null).thenApply(r -> Json.optString(Json.asObject(r, "ping"), "version", "?"));
    }

    /** Human-readable description of how the engine was launched (for error screens). */
    public synchronized String describe() {
        return command == null ? "Engine not started" : command.description();
    }

    public String stderrTail() {
        synchronized (stderrTail) {
            return String.join(System.lineSeparator(), stderrTail);
        }
    }

    // ------------------------------------------------------------------ transport

    private CompletableFuture<Object> request(String method, Object params) {
        return request(method, params, null);
    }

    private CompletableFuture<Object> request(String method, Object params, Duration overrideTimeout) {
        if (closed) return CompletableFuture.failedFuture(new EngineException("closed", "Engine client is closed."));
        long id = ids.incrementAndGet();
        CompletableFuture<Object> future = new CompletableFuture<>();
        pending.put(id, future);

        Map<String, Object> msg = new LinkedHashMap<>();
        msg.put("id", id);
        msg.put("method", method);
        if (params != null) msg.put("params", params);

        Duration timeout;
        try {
            synchronized (this) {
                ensureRunning();
                timeout = overrideTimeout != null ? overrideTimeout : freshStart ? STARTUP_TIMEOUT : REQUEST_TIMEOUT;
                freshStart = false;
                writer.write(Json.write(msg));
                writer.write('\n');
                writer.flush();
            }
        } catch (IOException | RuntimeException e) {
            pending.remove(id);
            EngineException ex = e instanceof EngineException ee
                    ? ee
                    : new EngineException("io", "Could not send request to engine: " + e.getMessage(), e);
            return CompletableFuture.failedFuture(ex);
        }

        return future.orTimeout(timeout.toMillis(), TimeUnit.MILLISECONDS).whenComplete((r, err) -> pending.remove(id));
    }

    private void ensureRunning() throws IOException {
        if (process != null && process.isAlive()) return;
        if (process != null) recordRestart();

        command = locator.get();
        ProcessBuilder pb = new ProcessBuilder(command.command()).directory(command.workingDir().toFile());
        Map<String, String> env = pb.environment();
        env.put("PYTHONUTF8", "1");
        env.put("PYTHONIOENCODING", "utf-8");
        env.put("PYTHONDONTWRITEBYTECODE", "1");
        env.put("PYTHONUNBUFFERED", "1");

        Process p;
        try {
            p = pb.start();
        } catch (IOException e) {
            throw new EngineException("start_failed", "Could not start engine (" + command.description() + "): " + e.getMessage(), e);
        }
        process = p;
        freshStart = true;
        writer = new BufferedWriter(new OutputStreamWriter(p.getOutputStream(), StandardCharsets.UTF_8));
        daemon("engine-stdout", () -> readStdout(p));
        daemon("engine-stderr", () -> readStderr(p));
    }

    private void recordRestart() {
        long now = System.currentTimeMillis();
        restarts.addLast(now);
        while (!restarts.isEmpty() && now - restarts.peekFirst() > 60_000) restarts.removeFirst();
        if (restarts.size() > MAX_RESTARTS_PER_MINUTE) {
            throw new EngineException("crash_loop", "The engine keeps crashing.\n" + stderrTail());
        }
    }

    private void readStdout(Process p) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (!line.isBlank()) dispatch(line);
            }
        } catch (IOException e) {
            // stream closed: handled below
        }
        failAll(new EngineException("exited", "The engine stopped unexpectedly." + tailSuffix()));
    }

    private void dispatch(String line) {
        Map<String, Object> msg;
        try {
            msg = Json.asObject(Json.parse(line), "response");
        } catch (RuntimeException e) {
            appendStderr("[bad response] " + line);
            return;
        }
        if (!(msg.get("id") instanceof Long id)) {
            appendStderr("[engine] " + line);
            return;
        }
        CompletableFuture<Object> future = pending.remove(id);
        if (future == null) return; // timed out already
        if (msg.get("error") instanceof Map<?, ?> err) {
            future.completeExceptionally(new EngineException(
                    String.valueOf(err.get("code")), String.valueOf(err.get("message"))));
        } else {
            future.complete(msg.get("result"));
        }
    }

    private void readStderr(Process p) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(p.getErrorStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) appendStderr(line);
        } catch (IOException ignored) {
            // process ended
        }
    }

    private void appendStderr(String line) {
        synchronized (stderrTail) {
            stderrTail.addLast(line);
            while (stderrTail.size() > STDERR_TAIL_LINES) stderrTail.removeFirst();
        }
    }

    private String tailSuffix() {
        String tail = stderrTail();
        return tail.isBlank() ? "" : System.lineSeparator() + tail;
    }

    private void failAll(EngineException ex) {
        for (Long id : List.copyOf(pending.keySet())) {
            CompletableFuture<Object> f = pending.remove(id);
            if (f != null) f.completeExceptionally(ex);
        }
    }

    private static void daemon(String name, Runnable task) {
        Thread t = new Thread(task, name);
        t.setDaemon(true);
        t.start();
    }

    @Override
    public void close() {
        closed = true;
        Process p;
        synchronized (this) {
            p = process;
            if (p != null && p.isAlive() && writer != null) {
                try {
                    writer.write("{\"id\":0,\"method\":\"shutdown\"}\n");
                    writer.flush();
                } catch (IOException ignored) {
                    // already gone
                }
            }
        }
        if (p != null) {
            try {
                if (!p.waitFor(1500, TimeUnit.MILLISECONDS)) p.destroyForcibly();
            } catch (InterruptedException e) {
                p.destroyForcibly();
                Thread.currentThread().interrupt();
            }
        }
        failAll(new EngineException("closed", "Engine client is closed."));
    }
}
