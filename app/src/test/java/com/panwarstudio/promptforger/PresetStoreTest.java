package com.panwarstudio.promptforger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.panwarstudio.promptforger.model.FormState;
import com.panwarstudio.promptforger.model.Preset;
import com.panwarstudio.promptforger.storage.PresetStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class PresetStoreTest {

    @Test
    void savesUpdatesByNameAndDeletes() throws Exception {
        Path dir = Files.createTempDirectory("pf-presets");
        PresetStore store = new PresetStore(dir);
        assertTrue(store.list().isEmpty());

        store.save("API builder", FormState.EXAMPLE);
        List<Preset> afterUpdate = store.save("api BUILDER", FormState.DEFAULT);
        assertEquals(1, afterUpdate.size(), "same name (case-insensitive) updates");
        assertEquals(FormState.DEFAULT, afterUpdate.getFirst().form());

        store.save("Other", FormState.EXAMPLE);
        List<Preset> reloaded = new PresetStore(dir).list();
        assertEquals(List.of("Other", "api BUILDER"), reloaded.stream().map(Preset::name).toList());

        assertEquals(1, store.delete(reloaded.getFirst().id()).size());
    }

    @Test
    void exportsAndImportsPresetsAndOldFormatStillLoads() throws Exception {
        Path a = Files.createTempDirectory("pf-a");
        PresetStore store = new PresetStore(a);
        store.save("One", FormState.EXAMPLE);
        store.save("Two", FormState.DEFAULT);
        Path file = a.resolve("export.json");
        assertEquals(2, store.exportTo(file));

        Path b = Files.createTempDirectory("pf-b");
        PresetStore other = new PresetStore(b);
        other.save("two", FormState.EXAMPLE); // same name, different case: replaced by the import
        assertEquals(2, other.importFrom(file));
        assertEquals(2, other.list().size());
        assertEquals(FormState.DEFAULT, other.list().stream().filter(p -> p.name().equals("Two")).findFirst().orElseThrow().form());

        // A v1.0 preset (no constraints/success/etc fields) still loads with defaults for the new fields.
        Path old = b.resolve("old.json");
        Files.writeString(old, "[{\"id\":\"x\",\"name\":\"Old\",\"updatedAt\":1,\"form\":{\"role\":\"r\",\"task\":\"t\",\"format\":\"graph\"}}]");
        assertEquals(1, other.importFrom(old));
        FormState f = other.list().stream().filter(p -> p.name().equals("Old")).findFirst().orElseThrow().form();
        assertEquals("graph", f.format());
        assertEquals("", f.constraints());

        Files.writeString(old, "{not json");
        assertThrows(java.io.IOException.class, () -> other.importFrom(old));
        Files.writeString(old, "[1, 2]");
        assertThrows(java.io.IOException.class, () -> other.importFrom(old));
    }

    @Test
    void survivesCorruptFile() throws Exception {
        Path dir = Files.createTempDirectory("pf-presets");
        Files.writeString(dir.resolve("presets.json"), "{not json");
        assertTrue(new PresetStore(dir).list().isEmpty());
        try (var files = Files.list(dir)) {
            assertTrue(files.anyMatch(p -> p.getFileName().toString().startsWith("presets.json.corrupt-")));
        }
    }
}
