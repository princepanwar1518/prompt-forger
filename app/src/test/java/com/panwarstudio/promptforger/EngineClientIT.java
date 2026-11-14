package com.panwarstudio.promptforger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.panwarstudio.promptforger.engine.AiSettings;
import com.panwarstudio.promptforger.engine.DescribeResult;
import com.panwarstudio.promptforger.engine.EngineClient;
import com.panwarstudio.promptforger.engine.EngineException;
import com.panwarstudio.promptforger.engine.EngineLocator;
import com.panwarstudio.promptforger.engine.EngineMeta;
import com.panwarstudio.promptforger.engine.ForgeResult;
import com.panwarstudio.promptforger.model.FormState;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

/** Talks to the real Python engine from ../engine. Skipped when Python is not available. */
class EngineClientIT {

    private static boolean engineAvailable() {
        try {
            return Files.isRegularFile(Path.of(System.getProperty("user.dir")).resolveSibling("engine").resolve("engine_main.py"))
                    && EngineLocator.locate() != null;
        } catch (RuntimeException e) {
            return false;
        }
    }

    @Test
    void forgesThroughTheRealEngine() throws Exception {
        assumeTrue(engineAvailable(), "Python engine not available");
        try (EngineClient client = new EngineClient()) {
            EngineMeta meta = client.meta().get(30, TimeUnit.SECONDS);
            assertEquals(4, meta.formats().size());

            ForgeResult ok = client.forge(FormState.EXAMPLE).get(10, TimeUnit.SECONDS);
            ForgeResult.Success s = assertInstanceOf(ForgeResult.Success.class, ok);
            assertEquals("PROMPT.md", s.files().getFirst().path());
            assertTrue(s.files().getFirst().content().contains("<promise>COMPLETE</promise>"));

            FormState unicode = new FormState("ingénieur", "Écrire un résumé — vite 😀", "", "", "", "", "", "", "", "",
                    "standard", "gpt", "concise", "", "");
            ForgeResult.Success u = assertInstanceOf(ForgeResult.Success.class, client.forge(unicode).get(10, TimeUnit.SECONDS));
            assertTrue(u.files().getFirst().content().contains("Écrire un résumé — vite 😀"));

            // Quality report and plain-English explanation come back with every forge.
            assertTrue(s.quality().score() > 0 && !s.quality().grade().isBlank());
            assertTrue(s.explanation().startsWith("This is a Ralph loop"));

            // Describe it, offline rules: plain language fills the form; user settings are kept.
            FormState current = new FormState("", "", "", "", "", "", "", "", "", "", "standard", "gpt", "balanced", "900", "");
            DescribeResult d = client.describe("I need emails for clients who haven't paid, polite but firm, under 120 words",
                    List.of(), AiSettings.DEFAULT, current).get(10, TimeUnit.SECONDS);
            assertEquals("professional business writer", d.form().role());
            assertEquals("gpt", d.form().model());
            assertEquals("900", d.form().tokenBudget());
            assertTrue(d.filled().contains("constraints"));
            assertEquals("rules", d.source());

            // AI provider without a key: friendly error code, not a crash.
            // Answers to clarifying questions land in the right fields, not glued into the task.
            DescribeResult improved = client.describe("help me with stuff", List.of(
                    java.util.Map.entry("What exactly should the result be (an email, code, a plan, a post...)?", "an email"),
                    java.util.Map.entry("Who is it for?", "my clients who haven't paid"),
                    java.util.Map.entry("How will you know the result is good?", "they pay within 7 days")),
                    AiSettings.DEFAULT, current).get(10, TimeUnit.SECONDS);
            assertEquals("professional business writer", improved.form().role());
            assertEquals("Help me with stuff. Deliverable: an email.", improved.form().task());
            assertTrue(improved.form().context().contains("Audience: my clients who haven't paid."));
            assertTrue(improved.form().successCriteria().startsWith("They pay within 7 days."));
            assertTrue(improved.questions().isEmpty());

            Throwable err = assertThrows(java.util.concurrent.ExecutionException.class, () -> client.describe(
                    "anything", List.of(), AiSettings.DEFAULT.withProvider("anthropic"), current).get(10, TimeUnit.SECONDS));
            assertInstanceOf(EngineException.class, err.getCause());

            // v1.2: score breakdown, Enhance (offline) and reply rating.
            assertEquals(5, s.quality().dimensions().size());
            FormState weak = new FormState("assistant", "Write a payment reminder email to a client whose invoice is overdue.",
                    "", "The client is a small shop. Never threaten legal action.", "", "", "", "", "", "",
                    "standard", "claude-sonnet", "detailed", "100", "");
            com.panwarstudio.promptforger.engine.EnhanceResult en = client.enhance(weak, AiSettings.DEFAULT).get(10, TimeUnit.SECONDS);
            assertTrue(en.after() > en.before(), "enhance improves the score");
            assertEquals("offline", en.source());
            assertEquals("professional business writer", en.form().role());
            assertTrue(en.changes().stream().anyMatch(c -> c.field().equals("constraints")));

            FormState brief = new FormState("writer", "Reminder email", "", "", "Keep it under 120 words.", "Sounds friendly",
                    "", "Subject: <subject>\n\n<body>", "", "", "standard", "claude-sonnet", "balanced", "", "");
            com.panwarstudio.promptforger.engine.RateResult good = client.rate(brief,
                    "Subject: Reminder\n\nHi Asha, invoice #77 is due Friday. Thanks!", AiSettings.DEFAULT).get(10, TimeUnit.SECONDS);
            com.panwarstudio.promptforger.engine.RateResult poor = client.rate(brief, "PAY NOW ".repeat(200), AiSettings.DEFAULT)
                    .get(10, TimeUnit.SECONDS);
            assertEquals(Integer.valueOf(100), good.accuracy());
            assertTrue(poor.accuracy() != null && poor.accuracy() < good.accuracy());
            assertTrue(good.checks().stream().anyMatch(c -> c.passed() == null), "judgement checks stay unchecked offline");

            ForgeResult bad = client.forge(FormState.DEFAULT).get(10, TimeUnit.SECONDS);
            ForgeResult.Invalid inv = assertInstanceOf(ForgeResult.Invalid.class, bad);
            assertEquals("Role is required.", inv.errors().get("role"));
        }
    }
}
