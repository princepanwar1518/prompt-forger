package com.panwarstudio.promptforger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import com.panwarstudio.promptforger.engine.AiSettings;
import com.panwarstudio.promptforger.model.FormState;
import com.panwarstudio.promptforger.storage.SettingsStore;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class SettingsStoreTest {

    @Test
    void roundTripsAiSettingsWithoutSecrets() throws Exception {
        Path dir = Files.createTempDirectory("pf-settings");
        SettingsStore store = new SettingsStore(dir);
        AiSettings ai = new AiSettings("ollama", "claude-x", "gpt-x", "qwen2.5", "http://127.0.0.1:11434");
        store.save(new SettingsStore.Settings(SettingsStore.Theme.DARK, FormState.EXAMPLE, ai));
        SettingsStore.Settings back = new SettingsStore(dir).load();
        assertEquals(ai, back.ai());
        assertEquals(FormState.EXAMPLE, back.draft());
        String raw = Files.readString(dir.resolve("settings.json"));
        assertFalse(raw.toLowerCase().contains("key"), "settings.json must never contain API keys");
    }

    @Test
    void oldSettingsFileGetsDefaultAi() throws Exception {
        Path dir = Files.createTempDirectory("pf-settings");
        Files.writeString(dir.resolve("settings.json"), "{\"theme\":\"LIGHT\",\"draft\":{\"role\":\"r\"}}");
        SettingsStore.Settings s = new SettingsStore(dir).load();
        assertEquals(AiSettings.DEFAULT, s.ai());
        assertEquals("r", s.draft().role());
    }
}
