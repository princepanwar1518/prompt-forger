package com.panwarstudio.promptforger.ui;

import com.panwarstudio.promptforger.engine.AiSettings;
import com.panwarstudio.promptforger.engine.EngineClient;
import com.panwarstudio.promptforger.engine.EngineMeta.Option;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CompletionException;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.ButtonType;
import javafx.scene.control.ComboBox;
import javafx.scene.control.Dialog;
import javafx.scene.control.Label;
import javafx.scene.control.PasswordField;
import javafx.scene.control.ProgressIndicator;
import javafx.scene.control.TextArea;
import javafx.scene.control.TextField;
import javafx.scene.layout.GridPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.VBox;

/** Settings (AI providers + API keys), Test it, and clarifying-question dialogs. */
final class Dialogs {

    private Dialogs() {}

    static void style(Dialog<?> dialog, Scene owner, String title) {
        dialog.setTitle(title);
        if (owner != null) {
            dialog.initOwner(owner.getWindow());
            dialog.getDialogPane().getStylesheets().setAll(owner.getStylesheets());
            if (ThemeManager.isDark(owner.getRoot())) dialog.getDialogPane().getStyleClass().add("dark");
        }
    }

    static String rootMessage(Throwable t) {
        Throwable c = t instanceof CompletionException && t.getCause() != null ? t.getCause() : t;
        return c.getMessage() == null ? c.toString() : c.getMessage();
    }

    // ------------------------------------------------------------------ settings

    static Optional<AiSettings> settings(Scene owner, EngineClient engine, List<Option> providers, AiSettings current) {
        Dialog<AiSettings> d = new Dialog<>();
        style(d, owner, "AI settings");
        d.setHeaderText("AI settings");

        ComboBox<Option> provider = new ComboBox<>();
        provider.getItems().setAll(providers);
        providers.stream().filter(p -> p.id().equals(current.provider())).findFirst()
                .ifPresentOrElse(provider::setValue, () -> provider.getSelectionModel().selectFirst());
        provider.setMaxWidth(Double.MAX_VALUE);

        TextField claudeModel = new TextField(current.anthropicModel());
        TextField openaiModel = new TextField(current.openaiModel());
        TextField ollamaModel = new TextField(current.ollamaModel());
        TextField ollamaUrl = new TextField(current.ollamaUrl());
        Label store = new Label();
        store.getStyleClass().add("hint");
        store.setWrapText(true);
        store.setMaxWidth(540);

        VBox claude = keyBlock(engine, "anthropic", "Claude (Anthropic)", "Get a key at console.anthropic.com", claudeModel, store);
        VBox openai = keyBlock(engine, "openai", "OpenAI", "Get a key at platform.openai.com", openaiModel, store);

        Label ollamaTitle = new Label("Ollama (runs on this computer)");
        ollamaTitle.getStyleClass().add("card-title");
        Label ollamaHint = new Label("Free and private. Install from ollama.com, then run: ollama pull " + current.ollamaModel());
        ollamaHint.getStyleClass().add("hint");
        ollamaHint.setWrapText(true);
        GridPane og = grid();
        og.addRow(0, new Label("Model"), ollamaModel);
        og.addRow(1, new Label("Address"), ollamaUrl);
        VBox ollama = new VBox(8, ollamaTitle, ollamaHint, og);
        ollama.getStyleClass().addAll("card", "flat");

        Label defaultLabel = new Label("Default for \"Describe it\" and \"Test it\"");
        defaultLabel.getStyleClass().add("field-label");
        VBox content = new VBox(14, defaultLabel, provider, claude, openai, ollama, store);
        content.setPadding(new Insets(4));
        content.setPrefWidth(560);
        d.getDialogPane().setContent(content);
        d.getDialogPane().getButtonTypes().setAll(ButtonType.OK, ButtonType.CANCEL);

        Button ok = (Button) d.getDialogPane().lookupButton(ButtonType.OK);
        ok.getStyleClass().add("primary");
        ok.addEventFilter(javafx.event.ActionEvent.ACTION, e -> {
            String url = ollamaUrl.getText().strip();
            if (!url.startsWith("http://") && !url.startsWith("https://")) {
                store.setText("The Ollama address must start with http:// or https://");
                e.consume();
            }
        });

        engine.keyStatus().whenComplete((s, err) -> Platform.runLater(() -> {
            if (err == null) store.setText("API keys are stored in " + s.get("store") + ", never in the app's settings or logs.");
        }));

        d.setResultConverter(b -> b == ButtonType.OK ? new AiSettings(
                provider.getValue() == null ? "rules" : provider.getValue().id(),
                orDefault(claudeModel, AiSettings.DEFAULT.anthropicModel()),
                orDefault(openaiModel, AiSettings.DEFAULT.openaiModel()),
                orDefault(ollamaModel, AiSettings.DEFAULT.ollamaModel()),
                orDefault(ollamaUrl, AiSettings.DEFAULT.ollamaUrl())) : null);
        return d.showAndWait();
    }

    private static VBox keyBlock(EngineClient engine, String id, String title, String hintText, TextField model, Label store) {
        Label t = new Label(title);
        t.getStyleClass().add("card-title");
        Label hint = new Label(hintText);
        hint.getStyleClass().add("hint");
        PasswordField key = new PasswordField();
        key.setPromptText("Paste API key");
        HBox.setHgrow(key, Priority.ALWAYS);
        Button save = new Button("Save key");
        save.getStyleClass().add("primary");
        Button remove = new Button("Remove");
        remove.getStyleClass().add("ghost");
        Label status = new Label("Checking…");
        status.getStyleClass().add("eyebrow");

        Runnable refresh = () -> engine.keyStatus().whenComplete((s, err) -> Platform.runLater(() ->
                status.setText(err != null ? "KEY STATUS UNKNOWN" : Boolean.TRUE.equals(s.get(id)) ? "● KEY SAVED" : "○ NO KEY")));
        refresh.run();
        save.setOnAction(e -> {
            String value = key.getText().strip();
            if (value.isEmpty()) return;
            save.setDisable(true);
            engine.setKey(id, value).whenComplete((s, err) -> Platform.runLater(() -> {
                save.setDisable(false);
                if (err != null) {
                    status.setText("NOT SAVED");
                    store.setText(rootMessage(err));
                } else {
                    key.clear();
                    status.setText("● KEY SAVED");
                    store.setText(title + " key saved in " + s.get("store") + ".");
                }
            }));
        });
        remove.setOnAction(e -> engine.deleteKey(id).whenComplete((s, err) -> Platform.runLater(refresh)));

        HBox keyRow = new HBox(8, key, save, remove);
        keyRow.setAlignment(Pos.CENTER_LEFT);
        GridPane g = grid();
        g.addRow(0, new Label("Model"), model);
        HBox head = new HBox(10, t, status);
        head.setAlignment(Pos.BASELINE_LEFT);
        VBox box = new VBox(8, head, hint, keyRow, g);
        box.getStyleClass().addAll("card", "flat");
        return box;
    }

    private static GridPane grid() {
        GridPane g = new GridPane(10, 8);
        javafx.scene.layout.ColumnConstraints c0 = new javafx.scene.layout.ColumnConstraints(70);
        javafx.scene.layout.ColumnConstraints c1 = new javafx.scene.layout.ColumnConstraints();
        c1.setHgrow(Priority.ALWAYS);
        g.getColumnConstraints().addAll(c0, c1);
        return g;
    }

    private static String orDefault(TextField f, String fallback) {
        String v = f.getText().strip();
        return v.isEmpty() ? fallback : v;
    }

    // ------------------------------------------------------------------ test it

    static void test(Scene owner, EngineClient engine, AiSettings ai, String providerLabel, String fileName, String prompt) {
        Dialog<Void> d = new Dialog<>();
        style(d, owner, "Test it");
        d.setHeaderText("Test " + fileName + " with " + providerLabel);

        TextField input = new TextField();
        input.setPromptText("Optional first message, e.g. a sample input (default: \"Please begin.\")");
        HBox.setHgrow(input, Priority.ALWAYS);
        Button send = new Button("Send  →");
        send.getStyleClass().add("ink");
        ProgressIndicator spin = new ProgressIndicator();
        spin.setMaxSize(22, 22);
        spin.setVisible(false);
        TextArea reply = new TextArea();
        reply.setEditable(false);
        reply.setWrapText(true);
        reply.setPrefRowCount(16);
        reply.getStyleClass().add("code");
        reply.setPromptText("The AI's reply appears here.");
        Label note = new Label("Uses your " + providerLabel + " settings. Cloud providers bill your account per request.");
        note.getStyleClass().add("hint");
        note.setWrapText(true);

        send.setOnAction(e -> {
            send.setDisable(true);
            spin.setVisible(true);
            reply.setText("");
            long started = System.nanoTime();
            engine.run(prompt, input.getText(), ai).whenComplete((text, err) -> Platform.runLater(() -> {
                send.setDisable(false);
                spin.setVisible(false);
                if (err != null) {
                    reply.setText("Couldn't run the test:\n" + rootMessage(err));
                } else {
                    reply.setText(text);
                    note.setText(String.format("Reply in %.1f s from %s.", (System.nanoTime() - started) / 1e9, providerLabel));
                }
            }));
        });

        HBox row = new HBox(8, input, spin, send);
        row.setAlignment(Pos.CENTER_LEFT);
        VBox content = new VBox(12, row, reply, note);
        content.setPrefWidth(720);
        d.getDialogPane().setContent(content);
        d.getDialogPane().getButtonTypes().setAll(ButtonType.CLOSE);
        d.showAndWait();
    }

    // ------------------------------------------------------------------ clarifying questions

    /** Returns question/answer pairs (blank answers dropped), or empty if the user skipped or answered nothing. */
    static Optional<List<java.util.Map.Entry<String, String>>> questions(Scene owner, List<String> questions) {
        Dialog<List<java.util.Map.Entry<String, String>>> d = new Dialog<>();
        style(d, owner, "A few quick questions");
        d.setHeaderText("A few quick questions make a much better prompt");
        List<TextField> answers = new ArrayList<>();
        VBox content = new VBox(10);
        for (String q : questions) {
            Label l = new Label(q);
            l.getStyleClass().add("field-label");
            l.setWrapText(true);
            TextField a = new TextField();
            a.setPromptText("Your answer (optional)");
            answers.add(a);
            content.getChildren().addAll(l, a);
        }
        content.setPrefWidth(520);
        d.getDialogPane().setContent(content);
        ButtonType improve = new ButtonType("Improve the form", javafx.scene.control.ButtonBar.ButtonData.OK_DONE);
        ButtonType skip = new ButtonType("Skip", javafx.scene.control.ButtonBar.ButtonData.CANCEL_CLOSE);
        d.getDialogPane().getButtonTypes().setAll(improve, skip);
        ((Button) d.getDialogPane().lookupButton(improve)).getStyleClass().add("primary");
        d.setResultConverter(b -> {
            if (b != improve) return null;
            List<java.util.Map.Entry<String, String>> out = new ArrayList<>();
            for (int i = 0; i < questions.size(); i++) {
                String a = answers.get(i).getText().strip();
                if (!a.isEmpty()) out.add(java.util.Map.entry(questions.get(i), a));
            }
            return out;
        });
        if (!answers.isEmpty()) Platform.runLater(() -> answers.getFirst().requestFocus());
        return d.showAndWait().filter(list -> !list.isEmpty());
    }
}
