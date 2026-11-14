package com.panwarstudio.promptforger.engine;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * Finds the Python engine. Order:
 * <ol>
 *   <li>{@code -Dpromptforger.engine=PATH} or env {@code PROMPT_FORGER_ENGINE}: an engine executable, or a .py script.</li>
 *   <li>The bundled engine shipped with the app: either a frozen {@code <app>/engine/prompt-forger-engine(.exe)},
 *       or a private Python at {@code <app>/engine/python/} running {@code <app>/engine/engine_main.py}.</li>
 *   <li>Development: {@code engine/engine_main.py} found by walking up from the working directory,
 *       run with the local Python ({@code py -3} or {@code python} on Windows, {@code python3} elsewhere).</li>
 * </ol>
 */
public final class EngineLocator {

    public record EngineCommand(List<String> command, Path workingDir, String description) {}

    private static final boolean WINDOWS =
            System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("win");
    private static final String EXE = WINDOWS ? "prompt-forger-engine.exe" : "prompt-forger-engine";

    private EngineLocator() {}

    public static EngineCommand locate() {
        return override()
                .or(EngineLocator::bundled)
                .or(EngineLocator::development)
                .orElseThrow(() -> new EngineException(
                        "not_found",
                        "Could not find the Prompt Forger engine. Reinstall the app, or for development run "
                                + "from the project folder with Python 3.11+ on PATH."));
    }

    private static Optional<EngineCommand> override() {
        String value = System.getProperty("promptforger.engine", System.getenv("PROMPT_FORGER_ENGINE"));
        if (value == null || value.isBlank()) return Optional.empty();
        Path path = Path.of(value.strip()).toAbsolutePath().normalize();
        if (!Files.isRegularFile(path)) {
            throw new EngineException("not_found", "Engine override does not exist: " + path);
        }
        Path dir = path.getParent();
        if (path.toString().endsWith(".py")) {
            List<String> cmd = new ArrayList<>(pythonLauncher());
            cmd.add(path.toString());
            return Optional.of(new EngineCommand(cmd, dir, "Python script (override): " + path));
        }
        return Optional.of(new EngineCommand(List.of(path.toString()), dir, "Engine (override): " + path));
    }

    private static Optional<EngineCommand> bundled() {
        List<Path> roots = new ArrayList<>();
        // Set by the Windows launcher to the install folder.
        String home = System.getProperty("promptforger.home");
        if (home != null && !home.isBlank()) roots.add(Path.of(home));
        // jpackage sets this to the native launcher. --app-content lands next to the app/ folder:
        // Windows: <root>/PromptForger.exe + <root>/engine; Linux: <root>/bin/launcher + <root>/lib/engine.
        String appPath = System.getProperty("jpackage.app-path");
        if (appPath != null) {
            Path launcherDir = Path.of(appPath).toAbsolutePath().getParent();
            if (launcherDir != null) {
                roots.add(launcherDir);
                roots.add(launcherDir.resolve("app"));
                roots.add(launcherDir.resolveSibling("lib"));
                roots.add(launcherDir.resolveSibling("app"));
            }
        }
        roots.add(Path.of(System.getProperty("user.dir")));
        for (Path root : roots) {
            Path engineDir = root.resolve("engine").normalize();
            Path exe = engineDir.resolve(EXE);
            if (Files.isRegularFile(exe) && Files.isExecutable(exe)) {
                return Optional.of(new EngineCommand(List.of(exe.toString()), engineDir, "Bundled engine: " + exe));
            }
            Path python = engineDir.resolve("python").resolve(WINDOWS ? "python.exe" : "bin/python3");
            Path script = engineDir.resolve("engine_main.py");
            if (Files.isRegularFile(python) && Files.isRegularFile(script)) {
                // -E -s: ignore the user's PYTHON* variables and user site-packages, so a local Python setup can't interfere.
                List<String> cmd = List.of(python.toString(), "-E", "-s", "-X", "utf8", script.toString());
                return Optional.of(new EngineCommand(cmd, engineDir, "Bundled Python engine: " + script));
            }
        }
        return Optional.empty();
    }

    private static Optional<EngineCommand> development() {
        Path dir = Path.of(System.getProperty("user.dir")).toAbsolutePath();
        for (int i = 0; i < 5 && dir != null; i++, dir = dir.getParent()) {
            Path script = dir.resolve("engine").resolve("engine_main.py");
            if (Files.isRegularFile(script)) {
                List<String> cmd = new ArrayList<>(pythonLauncher());
                cmd.add(script.toString());
                return Optional.of(new EngineCommand(cmd, script.getParent(), "Python source: " + script));
            }
        }
        return Optional.empty();
    }

    /** First Python 3 interpreter that answers {@code --version}. */
    static List<String> pythonLauncher() {
        List<List<String>> candidates = WINDOWS
                ? List.of(List.of("py", "-3"), List.of("python"), List.of("python3"))
                : List.of(List.of("python3"), List.of("python"));
        for (List<String> candidate : candidates) {
            List<String> probe = new ArrayList<>(candidate);
            probe.add("--version");
            try {
                Process p = new ProcessBuilder(probe).redirectErrorStream(true).start();
                p.getInputStream().readAllBytes();
                if (p.waitFor(5, TimeUnit.SECONDS) && p.exitValue() == 0) return candidate;
                p.destroyForcibly();
            } catch (IOException e) {
                // not installed; try the next one
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        throw new EngineException("no_python", "Python 3.11+ was not found on PATH (tried py, python, python3).");
    }
}
