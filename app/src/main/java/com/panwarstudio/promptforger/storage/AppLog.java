package com.panwarstudio.promptforger.storage;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.logging.FileHandler;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.logging.SimpleFormatter;

/** Rotating log file in the data folder (3 x 1 MB), so support questions have something to read. */
public final class AppLog {

    private static final Logger LOG = Logger.getLogger("promptforger");
    private static Path dir;

    private AppLog() {}

    public static synchronized void init(Path dataDir) {
        if (dir != null) return;
        dir = dataDir.resolve("logs");
        try {
            Files.createDirectories(dir);
            System.setProperty("java.util.logging.SimpleFormatter.format", "%1$tF %1$tT %4$s %5$s%6$s%n");
            FileHandler handler = new FileHandler(dir.resolve("prompt-forger-%g.log").toString(), 1_000_000, 3, true);
            handler.setFormatter(new SimpleFormatter());
            LOG.addHandler(handler);
            LOG.setLevel(Level.INFO);
        } catch (IOException | RuntimeException e) {
            System.err.println("Logging disabled: " + e.getMessage());
        }
    }

    public static Logger get() {
        return LOG;
    }

    public static Path folder() {
        return dir;
    }
}
