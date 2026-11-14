package com.panwarstudio.promptforger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.panwarstudio.promptforger.json.Json;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class JsonTest {

    @Test
    void roundTripsNestedValues() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("s", "line1\nline2 \"quoted\" \\ é 😀");
        m.put("n", 42L);
        m.put("d", 1.5);
        m.put("b", true);
        m.put("nil", null);
        m.put("list", List.of(1L, "two", List.of()));
        String text = Json.write(m);
        assertTrue(text.chars().allMatch(c -> c < 128), "writer output must be ASCII");
        assertEquals(m, Json.parse(text));
        assertEquals(m, Json.parse(Json.writePretty(m)));
    }

    @Test
    void parsesUnicodeEscapesAndSurrogates() {
        assertEquals("é😀", Json.parse("\"\\u00e9\\ud83d\\ude00\""));
    }

    @Test
    void rejectsMalformedInput() {
        for (String bad : List.of("", "{", "{\"a\":}", "[1,]", "tru", "\"unterminated", "{} x", "\"\\q\"", "01x")) {
            assertThrows(Json.ParseException.class, () -> Json.parse(bad), bad);
        }
    }

    @Test
    void rejectsExcessiveNesting() {
        String deep = "[".repeat(100) + "]".repeat(100);
        assertThrows(Json.ParseException.class, () -> Json.parse(deep));
    }
}
