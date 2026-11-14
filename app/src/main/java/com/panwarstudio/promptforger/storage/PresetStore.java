package com.panwarstudio.promptforger.storage;

import com.panwarstudio.promptforger.json.Json;
import com.panwarstudio.promptforger.model.FormState;
import com.panwarstudio.promptforger.model.Preset;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/** Named presets in presets.json. Saving with an existing name (case-insensitive) updates it. */
public final class PresetStore {

    private static final int MAX_PRESETS = 500;
    private final JsonFile file;

    public PresetStore(Path dataDir) {
        this.file = new JsonFile(dataDir.resolve("presets.json"));
    }

    public synchronized List<Preset> list() throws IOException {
        List<Preset> presets = new ArrayList<>();
        Object raw = file.read().orElse(List.of());
        try {
            for (Object item : Json.asList(raw, "presets")) {
                try {
                    presets.add(Preset.fromJson(item));
                } catch (RuntimeException skipBadEntry) {
                    // one malformed entry should not hide the rest
                }
            }
        } catch (IllegalArgumentException notAList) {
            file.quarantine();
            return List.of();
        }
        presets.sort(Comparator.comparingLong(Preset::updatedAt).reversed());
        return List.copyOf(presets);
    }

    public synchronized List<Preset> save(String name, FormState form) throws IOException {
        String key = name.strip().toLowerCase(Locale.ROOT);
        List<Preset> next = new ArrayList<>();
        String id = UUID.randomUUID().toString();
        for (Preset p : list()) {
            if (p.name().toLowerCase(Locale.ROOT).equals(key)) id = p.id(); // keep identity on update
            else next.add(p);
        }
        next.addFirst(new Preset(id, name, form, System.currentTimeMillis()));
        if (next.size() > MAX_PRESETS) next = new ArrayList<>(next.subList(0, MAX_PRESETS));
        persist(next);
        return List.copyOf(next);
    }

    public synchronized List<Preset> delete(String id) throws IOException {
        List<Preset> next = new ArrayList<>(list());
        next.removeIf(p -> p.id().equals(id));
        persist(next);
        return List.copyOf(next);
    }

    /** Writes every preset to a JSON file the user chose (for sharing or backup). */
    public synchronized int exportTo(Path target) throws IOException {
        List<Preset> all = list();
        new JsonFile(target).write(all.stream().map(Preset::toJson).toList());
        return all.size();
    }

    /**
     * Merges presets from a JSON file. Malformed entries are skipped; a preset whose name matches an existing
     * one (case-insensitive) replaces it. Returns how many were imported.
     */
    public synchronized int importFrom(Path source) throws IOException {
        Object raw = new JsonFile(source).readStrict();
        List<Preset> incoming = new ArrayList<>();
        for (Object item : Json.asList(raw, "presets")) {
            try {
                Preset p = Preset.fromJson(item);
                incoming.add(new Preset(UUID.randomUUID().toString(), p.name(), p.form(), System.currentTimeMillis()));
            } catch (RuntimeException skip) {
                // ignore malformed entry
            }
        }
        if (incoming.isEmpty()) throw new IOException("No valid presets found in that file.");
        List<Preset> next = new ArrayList<>(incoming);
        for (Preset existing : list()) {
            String key = existing.name().toLowerCase(Locale.ROOT);
            if (incoming.stream().noneMatch(p -> p.name().toLowerCase(Locale.ROOT).equals(key))) next.add(existing);
        }
        if (next.size() > MAX_PRESETS) next = new ArrayList<>(next.subList(0, MAX_PRESETS));
        persist(next);
        return incoming.size();
    }

    private void persist(List<Preset> presets) throws IOException {
        file.write(presets.stream().map(Preset::toJson).toList());
    }
}
