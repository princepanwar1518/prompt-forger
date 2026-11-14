package com.panwarstudio.promptforger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.panwarstudio.promptforger.engine.ForgeFile;
import com.panwarstudio.promptforger.storage.OutputWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class OutputWriterTest {

    @Test
    void writesNestedFilesInsideRoot() throws Exception {
        Path root = Files.createTempDirectory("pf-out");
        List<ForgeFile> files = List.of(
                new ForgeFile(".claude/agents/x.md", "markdown", "", "hello"),
                new ForgeFile("ralph.sh", "bash", "", "#!/bin/sh\n"));
        assertTrue(OutputWriter.clashes(root, files).isEmpty());
        OutputWriter.writeAll(root, files);
        assertEquals("hello", Files.readString(root.resolve(".claude/agents/x.md")));
        assertEquals(List.of(".claude/agents/x.md", "ralph.sh"), OutputWriter.clashes(root, files));
    }

    @Test
    void rejectsPathsThatEscapeTheRoot() throws Exception {
        Path root = Files.createTempDirectory("pf-out");
        for (String bad : List.of("../evil.md", "a/../../evil.md", "/etc/passwd", "", ".", "a/..")) {
            assertThrows(IllegalArgumentException.class, () -> OutputWriter.resolveInside(root, bad), bad);
        }
        // nothing written when any path in the batch is bad
        List<ForgeFile> mixed = List.of(new ForgeFile("ok.md", "markdown", "", "x"), new ForgeFile("../no.md", "markdown", "", "x"));
        assertThrows(IllegalArgumentException.class, () -> OutputWriter.writeAll(root, mixed));
        assertFalse(Files.exists(root.resolve("ok.md")));
    }
}
