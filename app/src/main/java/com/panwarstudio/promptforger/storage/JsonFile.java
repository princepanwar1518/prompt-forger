package com.panwarstudio.promptforger.storage;

import com.panwarstudio.promptforger.json.Json;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Optional;

/** Reads and atomically writes one JSON document. Corrupt files are set aside, never silently lost. */
final class JsonFile {

    private final Path path;

    JsonFile(Path path) {
        this.path = path;
    }

    Optional<Object> read() throws IOException {
        String text;
        try {
            text = Files.readString(path, StandardCharsets.UTF_8);
        } catch (NoSuchFileException e) {
            return Optional.empty();
        }
        try {
            return Optional.ofNullable(Json.parse(text));
        } catch (RuntimeException e) {
            quarantine();
            return Optional.empty();
        }
    }

    /** Like read(), but a missing or corrupt file is an error (used for user-chosen import files). */
    Object readStrict() throws IOException {
        String text = Files.readString(path, StandardCharsets.UTF_8);
        if (text.length() > 20_000_000) throw new IOException("File is too large.");
        try {
            return Json.parse(text);
        } catch (RuntimeException e) {
            throw new IOException("That file is not valid JSON: " + e.getMessage(), e);
        }
    }

    void write(Object value) throws IOException {
        Files.createDirectories(path.getParent());
        Path tmp = path.resolveSibling(path.getFileName() + ".tmp");
        Files.writeString(tmp, Json.writePretty(value), StandardCharsets.UTF_8);
        try {
            Files.move(tmp, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (AtomicMoveNotSupportedException e) {
            Files.move(tmp, path, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    void quarantine() {
        try {
            Files.move(path, path.resolveSibling(path.getFileName() + ".corrupt-" + System.currentTimeMillis()));
        } catch (IOException ignored) {
            // best effort
        }
    }
}
