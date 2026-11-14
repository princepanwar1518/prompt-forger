package com.panwarstudio.promptforger.storage;

import java.nio.file.Path;
import java.util.Locale;

/** Per-user data folder: %APPDATA%\PromptForger on Windows, ~/.config/prompt-forger elsewhere. */
public final class AppPaths {

    private AppPaths() {}

    public static Path dataDir() {
        String override = System.getProperty("promptforger.dataDir");
        if (override != null && !override.isBlank()) return Path.of(override);
        boolean windows = System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("win");
        String appData = System.getenv("APPDATA");
        if (windows && appData != null && !appData.isBlank()) return Path.of(appData, "PromptForger");
        String xdg = System.getenv("XDG_CONFIG_HOME");
        Path base = xdg != null && !xdg.isBlank() ? Path.of(xdg) : Path.of(System.getProperty("user.home"), ".config");
        return base.resolve("prompt-forger");
    }
}
