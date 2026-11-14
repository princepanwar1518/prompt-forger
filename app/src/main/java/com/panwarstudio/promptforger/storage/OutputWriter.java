package com.panwarstudio.promptforger.storage;

import com.panwarstudio.promptforger.engine.ForgeFile;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.ArrayList;
import java.util.List;

/** Writes generated files under a chosen folder. Rejects any path that would escape that folder. */
public final class OutputWriter {

    private OutputWriter() {}

    public static Path resolveInside(Path root, String relative) {
        if (relative == null || relative.isBlank() || relative.indexOf('\0') >= 0) {
            throw new IllegalArgumentException("Empty or invalid file path.");
        }
        Path rel = Path.of(relative.replace('\\', '/'));
        if (rel.isAbsolute() || rel.getRoot() != null) throw new IllegalArgumentException("Absolute path not allowed: " + relative);
        Path base = root.toAbsolutePath().normalize();
        Path target = base.resolve(rel).normalize();
        if (!target.startsWith(base) || target.equals(base)) {
            throw new IllegalArgumentException("Path escapes the target folder: " + relative);
        }
        return target;
    }

    /** Files that already exist and would be overwritten. */
    public static List<String> clashes(Path root, List<ForgeFile> files) {
        List<String> out = new ArrayList<>();
        for (ForgeFile f : files) if (Files.exists(resolveInside(root, f.path()))) out.add(f.path());
        return out;
    }

    /** Validates every path first, then writes, so a bad path never leaves a half-written set. */
    public static void writeAll(Path root, List<ForgeFile> files) throws IOException {
        List<Path> targets = files.stream().map(f -> resolveInside(root, f.path())).toList();
        for (int i = 0; i < files.size(); i++) write(targets.get(i), files.get(i).content());
    }

    public static void write(Path target, String content) throws IOException {
        Path parent = target.getParent();
        if (parent != null) Files.createDirectories(parent);
        Files.writeString(target, content, StandardCharsets.UTF_8);
        if (target.getFileName().toString().endsWith(".sh")) {
            try {
                Files.setPosixFilePermissions(target, PosixFilePermissions.fromString("rwxr-xr-x"));
            } catch (UnsupportedOperationException windows) {
                // NTFS has no exec bit; WSL/git handle this themselves
            }
        }
    }
}
