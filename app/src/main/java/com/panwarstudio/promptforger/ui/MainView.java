package com.panwarstudio.promptforger.ui;

import com.panwarstudio.promptforger.engine.AiSettings;
import com.panwarstudio.promptforger.engine.DescribeResult;
import com.panwarstudio.promptforger.engine.EngineClient;
import com.panwarstudio.promptforger.engine.EngineException;
import com.panwarstudio.promptforger.engine.EngineMeta;
import com.panwarstudio.promptforger.engine.ForgeFile;
import com.panwarstudio.promptforger.engine.ForgeResult;
import com.panwarstudio.promptforger.model.FormState;
import com.panwarstudio.promptforger.model.Preset;
import com.panwarstudio.promptforger.storage.AppLog;
import com.panwarstudio.promptforger.storage.OutputWriter;
import com.panwarstudio.promptforger.storage.PresetStore;
import com.panwarstudio.promptforger.storage.SettingsStore;
import com.panwarstudio.promptforger.storage.SettingsStore.Settings;
import com.panwarstudio.promptforger.storage.SettingsStore.Theme;
import java.io.File;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletionException;
import java.util.concurrent.atomic.AtomicLong;
import java.util.logging.Level;
import javafx.animation.PauseTransition;
import javafx.application.Platform;
import javafx.geometry.Pos;
import javafx.scene.control.Alert;
import javafx.scene.control.Button;
import javafx.scene.control.ButtonType;
import javafx.scene.control.ComboBox;
import javafx.scene.control.Dialog;
import javafx.scene.control.Label;
import javafx.scene.control.MenuButton;
import javafx.scene.control.MenuItem;
import javafx.scene.control.RadioMenuItem;
import javafx.scene.control.SeparatorMenuItem;
import javafx.scene.control.SplitPane;
import javafx.scene.control.TextInputDialog;
import javafx.scene.control.ToggleGroup;
import javafx.scene.control.Tooltip;
import javafx.scene.input.Clipboard;
import javafx.scene.input.ClipboardContent;
import javafx.scene.input.KeyCode;
import javafx.scene.input.KeyCodeCombination;
import javafx.scene.input.KeyCombination;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.StackPane;
import javafx.stage.DirectoryChooser;
import javafx.stage.FileChooser;
import javafx.stage.Window;
import javafx.util.Duration;

/** Main screen: header, Describe-it card + form on the left, live output with quality report on the right. */
public final class MainView extends BorderPane {

    private final EngineClient engine;
    private final EngineMeta meta;
    private final PresetStore presets;
    private final SettingsStore settingsStore;
    private final Toast toast;
    private final DescribeCard describeCard;
    private final FormPane form;
    private final OutputPane output;
    private final ComboBox<Preset> presetBox = new ComboBox<>();
    private final Button deletePreset = new Button("Delete");
    private final PauseTransition forgeDebounce = new PauseTransition(Duration.millis(180));
    private final PauseTransition saveDebounce = new PauseTransition(Duration.millis(800));
    private final AtomicLong forgeSeq = new AtomicLong();
    private Theme theme;
    private AiSettings ai;
    private boolean applyingPreset;
    private String lastDescription = "";

    public MainView(EngineClient engine, EngineMeta meta, PresetStore presets, SettingsStore settingsStore,
                    Settings settings, Toast toast) {
        this.engine = engine;
        this.meta = meta;
        this.presets = presets;
        this.settingsStore = settingsStore;
        this.toast = toast;
        this.theme = settings.theme();
        this.ai = settings.ai();
        getStyleClass().add("main");

        describeCard = new DescribeCard(meta.providers(), ai.provider(), this::describe, p -> {
            ai = ai.withProvider(p);
            persistSettings();
        });
        form = new FormPane(meta, describeCard);
        output = new OutputPane(new OutputPane.Actions() {
            @Override
            public void copy(ForgeFile file) {
                copyToClipboard(file);
            }

            @Override
            public void save(ForgeFile file) {
                saveFile(file);
            }

            @Override
            public void saveAll(List<ForgeFile> files) {
                saveFiles(files);
            }

            @Override
            public void test(ForgeFile file) {
                testPrompt(file);
            }

            @Override
            public void focusField(String field) {
                form.focusField(field);
            }

            @Override
            public void enhance() {
                enhancePrompt();
            }
        });

        setTop(buildHeader());
        SplitPane split = new SplitPane(form, output);
        split.setDividerPositions(0.44);
        split.getStyleClass().add("main-split");
        SplitPane.setResizableWithParent(form, false);
        setCenter(split);

        forgeDebounce.setOnFinished(e -> forgeNow());
        saveDebounce.setOnFinished(e -> persistSettings());
        form.setOnChange(() -> {
            forgeDebounce.playFromStart();
            saveDebounce.playFromStart();
            if (!applyingPreset) presetBox.getSelectionModel().clearSelection();
        });

        form.write(settings.draft());
        reloadPresets(null);
        sceneProperty().addListener((obs, o, scene) -> {
            if (scene != null) {
                installShortcuts();
                ThemeManager.apply(scene.getRoot(), theme);
            }
        });
        // New users start at "Describe it"; returning users with a draft go straight to the form.
        Platform.runLater(() -> {
            if (form.isBlank()) describeCard.focusInput();
            else form.focusFirst();
        });
    }

    // ------------------------------------------------------------------ header

    private HBox buildHeader() {
        Region dot = new Region();
        dot.getStyleClass().add("wordmark-dot");
        Label title = new Label("Prompt Forger®");
        title.getStyleClass().add("wordmark");
        Label version = new Label("v1.2");
        version.getStyleClass().add("version-pill");

        presetBox.setPromptText("Presets");
        presetBox.setPrefWidth(210);
        presetBox.setAccessibleText("Load a saved preset");
        presetBox.valueProperty().addListener((obs, o, n) -> {
            deletePreset.setDisable(n == null);
            if (n != null && !applyingPreset) {
                applyingPreset = true;
                try {
                    form.write(n.form());
                } finally {
                    applyingPreset = false;
                }
                toast.show("Loaded \"" + n.name() + "\"", Toast.Tone.INFO);
            }
        });

        Button savePreset = new Button("Save preset");
        savePreset.setTooltip(new Tooltip("Save the current form as a reusable preset"));
        savePreset.setOnAction(e -> promptSavePreset());
        deletePreset.setDisable(true);
        deletePreset.getStyleClass().add("ghost");
        deletePreset.setOnAction(e -> deleteSelectedPreset());

        Button settings = new Button("AI settings");
        settings.setTooltip(new Tooltip("Choose Claude, OpenAI or Ollama and add API keys"));
        settings.setOnAction(e -> openSettings());

        MenuButton more = new MenuButton("More");
        MenuItem example = new MenuItem("Load example");
        example.setOnAction(e -> {
            form.write(FormState.EXAMPLE);
            toast.show("Example loaded", Toast.Tone.INFO);
        });
        MenuItem clear = new MenuItem("Clear form");
        clear.setOnAction(e -> {
            if (confirm("Clear the form?", "This resets every field. Saved presets are not affected.")) {
                form.write(form.read().cleared());
            }
        });
        MenuItem importPresets = new MenuItem("Import presets…");
        importPresets.setOnAction(e -> importPresets());
        MenuItem exportPresets = new MenuItem("Export presets…");
        exportPresets.setOnAction(e -> exportPresets());
        ToggleGroup themeGroup = new ToggleGroup();
        RadioMenuItem system = themeItem("System theme", Theme.SYSTEM, themeGroup);
        RadioMenuItem light = themeItem("Light theme", Theme.LIGHT, themeGroup);
        RadioMenuItem dark = themeItem("Dark theme", Theme.DARK, themeGroup);
        MenuItem engineInfo = new MenuItem("About & diagnostics");
        engineInfo.setOnAction(e -> showEngineInfo());
        more.getItems().addAll(example, clear, new SeparatorMenuItem(), importPresets, exportPresets,
                new SeparatorMenuItem(), system, light, dark, new SeparatorMenuItem(), engineInfo);

        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);
        HBox header = new HBox(10, dot, title, version, spacer, presetBox, savePreset, deletePreset, settings, more);
        header.setAlignment(Pos.CENTER_LEFT);
        header.getStyleClass().add("header");
        return header;
    }

    private RadioMenuItem themeItem(String label, Theme value, ToggleGroup group) {
        RadioMenuItem item = new RadioMenuItem(label);
        item.setToggleGroup(group);
        item.setSelected(theme == value);
        item.setOnAction(e -> {
            theme = value;
            if (getScene() != null) ThemeManager.apply(getScene().getRoot(), theme);
            persistSettings();
        });
        return item;
    }

    // ------------------------------------------------------------------ forging

    private void forgeNow() {
        FormState state = form.read();
        long seq = forgeSeq.incrementAndGet();
        engine.forge(state).whenComplete((result, error) -> Platform.runLater(() -> {
            if (seq != forgeSeq.get()) return; // a newer request is in flight
            if (error != null) {
                AppLog.get().log(Level.WARNING, "forge failed", error);
                output.showError("Engine error", Dialogs.rootMessage(error));
                return;
            }
            render(result);
        }));
    }

    private void render(ForgeResult result) {
        switch (result) {
            case ForgeResult.Success s -> {
                form.showErrors(Map.of());
                output.showResult(s);
            }
            case ForgeResult.Invalid inv -> {
                form.showErrors(inv.errors());
                Map<String, String> errors = inv.errors();
                boolean onlyMissingBasics = errors.keySet().stream().allMatch(k -> k.equals("role") || k.equals("task"))
                        && errors.values().stream().allMatch(m -> m.endsWith("is required."));
                if (onlyMissingBasics) {
                    output.showEmpty("Nothing forged yet.",
                            "Describe what you need on the left, or fill in Role and Task. The prompt builds live as you type.");
                } else {
                    output.showError("Check the form", String.join("\n", errors.values()));
                }
            }
        }
    }

    // ------------------------------------------------------------------ describe it

    private void describe(String text, String provider) {
        ai = ai.withProvider(provider);
        lastDescription = text;
        runDescribe(text, List.of(), true);
    }

    private void runDescribe(String text, List<Map.Entry<String, String>> answers, boolean mayAsk) {
        describeCard.setBusy(true);
        long started = System.nanoTime();
        engine.describe(text, answers, ai, form.read()).whenComplete((r, err) -> Platform.runLater(() -> {
            describeCard.setBusy(false);
            if (err != null) {
                String msg = Dialogs.rootMessage(err);
                describeCard.setStatus("✕ " + msg);
                AppLog.get().log(Level.INFO, "describe failed: " + msg);
                if (err.getCause() instanceof EngineException ee && "no_key".equals(ee.code())) openSettings();
                return;
            }
            applyDescribe(r, (System.nanoTime() - started) / 1e9);
            if (mayAsk && !r.questions().isEmpty()) {
                Dialogs.questions(getScene(), r.questions())
                        .ifPresent(ans -> runDescribe(lastDescription, ans, false));
            }
        }));
    }

    private void applyDescribe(DescribeResult r, double seconds) {
        form.write(r.form());
        String by = switch (r.source()) {
            case "anthropic" -> "Claude";
            case "openai" -> "OpenAI";
            case "ollama" -> "Ollama";
            default -> "offline rules";
        };
        String status = String.format("✓ Filled %d field%s with %s in %.1f s. Review them below.",
                r.filled().size(), r.filled().size() == 1 ? "" : "s", by, seconds);
        if (!r.notes().isEmpty()) status += " " + String.join(" ", r.notes());
        describeCard.setStatus(status);
        toast.show("Form filled — check the score on the right", Toast.Tone.SUCCESS);
    }

    // ------------------------------------------------------------------ actions

    private void copyToClipboard(ForgeFile file) {
        ClipboardContent content = new ClipboardContent();
        content.putString(file.content());
        Clipboard.getSystemClipboard().setContent(content);
        toast.show("Copied " + file.fileName(), Toast.Tone.SUCCESS);
    }

    private void testPrompt(ForgeFile file) {
        if ("rules".equals(ai.provider())) {
            toast.show("Pick Claude, OpenAI or Ollama in AI settings to test prompts", Toast.Tone.ERROR);
            openSettings();
            if ("rules".equals(ai.provider())) return;
        }
        String label = meta.providers().stream().filter(p -> p.id().equals(ai.provider())).findFirst()
                .map(EngineMeta.Option::label).orElse(ai.provider());
        Dialogs.test(getScene(), engine, ai, label, file.fileName(), file.content(), form.read());
    }

    private void enhancePrompt() {
        toast.show("rules".equals(ai.provider()) ? "Enhancing offline…" : "Enhancing with AI…", Toast.Tone.INFO);
        engine.enhance(form.read(), ai).whenComplete((r, err) -> Platform.runLater(() -> {
            if (err != null) {
                String msg = Dialogs.rootMessage(err);
                AppLog.get().info("enhance failed: " + msg);
                error("Couldn't enhance the prompt", msg);
                return;
            }
            if (Dialogs.enhance(getScene(), r)) {
                form.write(r.form());
                toast.show("Enhanced: score " + r.before() + " → " + r.after(), Toast.Tone.SUCCESS);
            }
        }));
    }

    private void openSettings() {
        Dialogs.settings(getScene(), engine, meta.providers(), ai).ifPresent(next -> {
            ai = next;
            persistSettings();
            toast.show("AI settings saved", Toast.Tone.SUCCESS);
        });
    }

    private void saveFile(ForgeFile file) {
        FileChooser chooser = new FileChooser();
        chooser.setTitle("Save " + file.fileName());
        chooser.setInitialFileName(file.fileName());
        String name = file.fileName();
        String ext = name.contains(".") ? name.substring(name.lastIndexOf('.')) : "";
        if (!ext.isEmpty()) chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter(ext + " file", "*" + ext));
        chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("All files", "*.*"));
        File target = chooser.showSaveDialog(window());
        if (target == null) return;
        try {
            OutputWriter.write(target.toPath(), file.content());
            toast.show("Saved " + target.getName(), Toast.Tone.SUCCESS);
        } catch (IOException | RuntimeException e) {
            error("Could not save file", e.getMessage());
        }
    }

    private void saveFiles(List<ForgeFile> files) {
        DirectoryChooser chooser = new DirectoryChooser();
        chooser.setTitle("Choose a folder for the generated files");
        File dir = chooser.showDialog(window());
        if (dir == null) return;
        Path root = dir.toPath();
        try {
            List<String> clashes = OutputWriter.clashes(root, files);
            if (!clashes.isEmpty() && !confirm("Overwrite " + clashes.size() + " file(s)?", String.join("\n", clashes))) return;
            OutputWriter.writeAll(root, files);
            toast.show("Saved " + files.size() + " files to " + dir.getName(), Toast.Tone.SUCCESS);
        } catch (IOException | RuntimeException e) {
            error("Could not save files", e.getMessage());
        }
    }

    private void importPresets() {
        FileChooser chooser = new FileChooser();
        chooser.setTitle("Import presets");
        chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("Prompt Forger presets", "*.json"));
        File f = chooser.showOpenDialog(window());
        if (f == null) return;
        try {
            int n = presets.importFrom(f.toPath());
            reloadPresets(null);
            toast.show("Imported " + n + " preset" + (n == 1 ? "" : "s"), Toast.Tone.SUCCESS);
        } catch (IOException | RuntimeException e) {
            error("Could not import presets", e.getMessage());
        }
    }

    private void exportPresets() {
        FileChooser chooser = new FileChooser();
        chooser.setTitle("Export presets");
        chooser.setInitialFileName("prompt-forger-presets.json");
        chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("Prompt Forger presets", "*.json"));
        File f = chooser.showSaveDialog(window());
        if (f == null) return;
        try {
            int n = presets.exportTo(f.toPath());
            toast.show("Exported " + n + " preset" + (n == 1 ? "" : "s"), Toast.Tone.SUCCESS);
        } catch (IOException | RuntimeException e) {
            error("Could not export presets", e.getMessage());
        }
    }

    private void promptSavePreset() {
        FormState state = form.read();
        if (state.role().isBlank() && state.task().isBlank()) {
            toast.show("Fill in at least Role or Task before saving a preset", Toast.Tone.ERROR);
            return;
        }
        TextInputDialog dialog = new TextInputDialog(
                Optional.ofNullable(presetBox.getValue()).map(Preset::name).orElse(state.role().strip()));
        styleDialog(dialog, "Save preset");
        dialog.setHeaderText("Name this preset");
        dialog.setContentText("Name:");
        dialog.showAndWait().map(String::strip).filter(s -> !s.isEmpty()).ifPresent(name -> {
            if (name.length() > Preset.MAX_NAME) {
                toast.show("Preset names can be at most " + Preset.MAX_NAME + " characters", Toast.Tone.ERROR);
                return;
            }
            try {
                List<Preset> list = presets.save(name, state);
                reloadPresets(list.isEmpty() ? null : list.getFirst().id(), list);
                toast.show("Saved preset \"" + name + "\"", Toast.Tone.SUCCESS);
            } catch (IOException e) {
                error("Could not save preset", e.getMessage());
            }
        });
    }

    private void deleteSelectedPreset() {
        Preset p = presetBox.getValue();
        if (p == null || !confirm("Delete preset \"" + p.name() + "\"?", "This cannot be undone.")) return;
        try {
            reloadPresets(null, presets.delete(p.id()));
            toast.show("Deleted \"" + p.name() + "\"", Toast.Tone.INFO);
        } catch (IOException e) {
            error("Could not delete preset", e.getMessage());
        }
    }

    private void reloadPresets(String selectId) {
        try {
            reloadPresets(selectId, presets.list());
        } catch (IOException e) {
            toast.show("Could not read presets: " + e.getMessage(), Toast.Tone.ERROR);
        }
    }

    private void reloadPresets(String selectId, List<Preset> list) {
        applyingPreset = true;
        try {
            presetBox.getItems().setAll(list);
            list.stream().filter(p -> p.id().equals(selectId)).findFirst()
                    .ifPresentOrElse(presetBox::setValue, () -> presetBox.getSelectionModel().clearSelection());
        } finally {
            applyingPreset = false;
        }
        deletePreset.setDisable(presetBox.getValue() == null);
    }

    private void showEngineInfo() {
        engine.ping().whenComplete((version, err) -> Platform.runLater(() -> {
            Alert a = new Alert(Alert.AlertType.INFORMATION);
            styleDialog(a, "About Prompt Forger");
            a.setHeaderText(err == null ? "Prompt Forger 1.2 · engine v" + version : "Engine is not responding");
            Path logs = AppLog.folder();
            a.setContentText(engine.describe() + "\n\nLogs: " + (logs == null ? "disabled" : logs));
            a.showAndWait();
        }));
    }

    /** Persists theme, AI settings and draft. Called on a debounce and when the window closes. */
    public void persistSettings() {
        try {
            settingsStore.save(new Settings(theme, form.read(), ai));
        } catch (IOException e) {
            AppLog.get().log(Level.WARNING, "could not save settings", e);
        }
    }

    // ------------------------------------------------------------------ helpers

    private void installShortcuts() {
        var acc = getScene().getAccelerators();
        acc.put(new KeyCodeCombination(KeyCode.C, KeyCombination.SHORTCUT_DOWN, KeyCombination.SHIFT_DOWN),
                () -> output.selected().ifPresent(this::copyToClipboard));
        acc.put(new KeyCodeCombination(KeyCode.S, KeyCombination.SHORTCUT_DOWN),
                () -> output.selected().ifPresent(this::saveFile));
        acc.put(new KeyCodeCombination(KeyCode.S, KeyCombination.SHORTCUT_DOWN, KeyCombination.SHIFT_DOWN), () -> {
            if (!output.files().isEmpty()) saveFiles(output.files());
        });
    }

    private Window window() {
        return getScene() == null ? null : getScene().getWindow();
    }

    private boolean confirm(String header, String detail) {
        Alert a = new Alert(Alert.AlertType.CONFIRMATION, detail, ButtonType.OK, ButtonType.CANCEL);
        styleDialog(a, "Confirm");
        a.setHeaderText(header);
        return a.showAndWait().filter(b -> b == ButtonType.OK).isPresent();
    }

    private void error(String header, String detail) {
        AppLog.get().warning(header + ": " + detail);
        Alert a = new Alert(Alert.AlertType.ERROR, detail == null ? "Unknown error" : detail, ButtonType.OK);
        styleDialog(a, "Error");
        a.setHeaderText(header);
        a.showAndWait();
    }

    private void styleDialog(Dialog<?> dialog, String title) {
        Dialogs.style(dialog, getScene(), title);
    }

    /** Used by the startup screen to show a failure in the same style. */
    public static StackPane errorScreen(String title, Throwable error, String details, Runnable retry) {
        Throwable cause = error instanceof CompletionException && error.getCause() != null ? error.getCause() : error;
        Label t = new Label(title);
        t.getStyleClass().add("empty-title");
        t.setWrapText(true);
        Label msg = new Label(cause instanceof EngineException ? cause.getMessage() : String.valueOf(cause));
        msg.getStyleClass().add("empty-body");
        msg.setWrapText(true);
        msg.setMaxWidth(560);
        Label d = new Label(details);
        d.getStyleClass().add("hint");
        d.setWrapText(true);
        d.setMaxWidth(560);
        Button retryButton = new Button("Retry");
        retryButton.getStyleClass().add("primary");
        retryButton.setOnAction(e -> retry.run());
        var box = new javafx.scene.layout.VBox(12, t, msg, d, retryButton);
        box.setAlignment(Pos.CENTER);
        box.getStyleClass().addAll("empty-state", "error-state");
        return new StackPane(box);
    }
}
