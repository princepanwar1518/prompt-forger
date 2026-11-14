package com.panwarstudio.promptforger.ui;

import com.panwarstudio.promptforger.engine.ForgeFile;
import com.panwarstudio.promptforger.engine.ForgeResult;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.stream.IntStream;
import javafx.animation.FadeTransition;
import javafx.geometry.Pos;
import javafx.scene.Cursor;
import javafx.scene.Node;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.Tab;
import javafx.scene.control.TabPane;
import javafx.scene.control.TextArea;
import javafx.scene.control.ToggleButton;
import javafx.scene.control.Tooltip;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.StackPane;
import javafx.scene.layout.VBox;
import javafx.util.Duration;

/** Generated files as tabs, plus the quality report, a plain-English explanation and actions. */
final class OutputPane extends BorderPane {

    interface Actions {
        void copy(ForgeFile file);

        void save(ForgeFile file);

        void saveAll(List<ForgeFile> files);

        void test(ForgeFile file);

        void focusField(String field);

        void enhance();
    }

    private static final int MAX_FINDINGS_SHOWN = 4;

    private final Actions actions;
    private final TabPane tabs = new TabPane();
    private final Label stats = new Label();
    private final Label description = new Label();
    private final VBox warnings = new VBox(6);
    private final Button copy = new Button("Copy");
    private final Button save = new Button("Save");
    private final Button saveAll = new Button("Save all");
    private final Button test = new Button("Test it");
    private final ToggleButton explainToggle = new ToggleButton("Plain English");
    private final Label scoreNumber = new Label();
    private final Label grade = new Label();
    private final VBox findingsBox = new VBox(7);
    private final VBox dimensionsBox = new VBox(6);
    private final Button enhance = new Button("✦ Enhance");
    private final HBox qualityCard;
    private final Label explanation = new Label();
    private final VBox explanationCard;
    private final Label emptyTitle = new Label();
    private final Label emptyBody = new Label();
    private final VBox emptyState;
    private final VBox top;
    private HBox actionsRow;
    private List<ForgeFile> files = List.of();

    OutputPane(Actions actions) {
        this.actions = actions;
        getStyleClass().add("output");

        Label eyebrow = new Label("04");
        eyebrow.getStyleClass().add("eyebrow");
        Label heading = new Label("Your prompt");
        heading.getStyleClass().add("section-title");
        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);

        copy.getStyleClass().add("primary");
        test.getStyleClass().add("violet");
        copy.setTooltip(new Tooltip("Copy this file (Ctrl+Shift+C)"));
        save.setTooltip(new Tooltip("Save this file (Ctrl+S)"));
        saveAll.setTooltip(new Tooltip("Save every file into a folder (Ctrl+Shift+S)"));
        test.setTooltip(new Tooltip("Send this prompt to your AI provider and see the reply"));
        explainToggle.setTooltip(new Tooltip("What this prompt makes the AI do, in plain words"));
        copy.setOnAction(e -> selected().ifPresent(actions::copy));
        save.setOnAction(e -> selected().ifPresent(actions::save));
        saveAll.setOnAction(e -> {
            if (!files.isEmpty()) actions.saveAll(files);
        });
        test.setOnAction(e -> selected().ifPresent(actions::test));

        for (javafx.scene.control.ButtonBase b : List.of(explainToggle, test, saveAll, save, copy)) {
            b.setMinWidth(Region.USE_PREF_SIZE);
        }
        heading.setMinWidth(Region.USE_PREF_SIZE);
        HBox titleRow = new HBox(10, eyebrow, heading, spacer, stats);
        titleRow.setAlignment(Pos.BASELINE_LEFT);
        Region actionsSpacer = new Region();
        HBox.setHgrow(actionsSpacer, Priority.ALWAYS);
        actionsRow = new HBox(10, explainToggle, actionsSpacer, test, saveAll, save, copy);
        actionsRow.setAlignment(Pos.CENTER_LEFT);

        // Quality card: big score + grade pill + top findings.
        Label scoreOf = new Label("/ 100");
        scoreOf.getStyleClass().add("score-of");
        scoreNumber.getStyleClass().add("score-number");
        grade.getStyleClass().add("grade-pill");
        Label qualityEyebrow = new Label("PROMPT SCORE");
        qualityEyebrow.getStyleClass().add("eyebrow");
        HBox scoreRow = new HBox(6, scoreNumber, scoreOf);
        scoreRow.setAlignment(Pos.BASELINE_LEFT);
        enhance.getStyleClass().add("ink");
        enhance.setMinWidth(Region.USE_PREF_SIZE);
        enhance.setTooltip(new Tooltip("Fix what the checker found. With an AI provider, it also rewrites the prompt. You review before applying."));
        enhance.setOnAction(e -> actions.enhance());
        VBox scoreBox = new VBox(4, qualityEyebrow, scoreRow, grade, new Region(), enhance);
        scoreBox.setMinWidth(140);
        dimensionsBox.setMinWidth(170);
        dimensionsBox.setPrefWidth(190);
        findingsBox.setFillWidth(true);
        HBox.setHgrow(findingsBox, Priority.ALWAYS);
        qualityCard = new HBox(20, scoreBox, dimensionsBox, findingsBox);
        qualityCard.getStyleClass().add("card");
        qualityCard.setAlignment(Pos.TOP_LEFT);

        Label explainEyebrow = new Label("IN PLAIN ENGLISH");
        explainEyebrow.getStyleClass().add("eyebrow");
        explanation.getStyleClass().add("explanation");
        explanation.setWrapText(true);
        explanationCard = new VBox(6, explainEyebrow, explanation);
        explanationCard.getStyleClass().addAll("card", "flat");
        explainToggle.selectedProperty().addListener((obs, o, on) -> show(explanationCard, on && !files.isEmpty()));

        description.getStyleClass().add("file-description");
        description.setWrapText(true);
        warnings.getStyleClass().add("warnings");

        tabs.setTabClosingPolicy(TabPane.TabClosingPolicy.UNAVAILABLE);
        tabs.getSelectionModel().selectedItemProperty().addListener((obs, o, n) -> refreshSelection());

        emptyTitle.getStyleClass().add("empty-title");
        emptyTitle.setWrapText(true);
        emptyBody.getStyleClass().add("empty-body");
        emptyBody.setWrapText(true);
        emptyBody.setMaxWidth(440);
        emptyState = new VBox(10, emptyTitle, emptyBody);
        emptyState.setAlignment(Pos.CENTER);
        emptyState.getStyleClass().add("empty-state");

        top = new VBox(14, titleRow, actionsRow, qualityCard, explanationCard, warnings, description);
        top.setPadding(new javafx.geometry.Insets(0, 6, 14, 0));
        setTop(top);
        StackPane body = new StackPane(tabs, emptyState);
        body.setPadding(new javafx.geometry.Insets(0, 6, 6, 0));
        setCenter(body);

        showEmpty("Nothing forged yet.", "Describe what you need on the left, or fill in Role and Task. The prompt builds live as you type.");
    }

    void showResult(ForgeResult.Success result) {
        List<ForgeFile> next = result.files();
        boolean samePaths = next.size() == files.size()
                && IntStream.range(0, next.size()).allMatch(i -> next.get(i).path().equals(files.get(i).path()));
        String selectedPath = selected().map(ForgeFile::path).orElse(null);
        boolean wasEmpty = emptyState.isVisible();
        files = List.copyOf(next);

        if (samePaths) {
            // Update in place so scroll position and selected tab survive live edits.
            for (int i = 0; i < files.size(); i++) {
                TextArea area = (TextArea) tabs.getTabs().get(i).getContent();
                String content = files.get(i).content();
                if (!area.getText().equals(content)) {
                    double scroll = area.getScrollTop();
                    area.setText(content);
                    area.setScrollTop(scroll);
                }
            }
        } else {
            tabs.getTabs().clear();
            for (ForgeFile f : files) tabs.getTabs().add(tabFor(f));
            int keep = 0;
            for (int i = 0; i < files.size(); i++) if (files.get(i).path().equals(selectedPath)) keep = i;
            tabs.getSelectionModel().select(keep);
        }

        renderQuality(result.quality());
        explanation.setText(result.explanation());
        show(explanationCard, explainToggle.isSelected());
        warnings.getChildren().setAll(result.warnings().stream().map(w -> {
            Label l = new Label(w);
            l.getStyleClass().add("warning");
            l.setWrapText(true);
            return (Node) l;
        }).toList());
        show(warnings, !result.warnings().isEmpty());

        setEmptyVisible(false);
        if (wasEmpty) fadeIn(tabs);
        refreshSelection();
    }

    void showEmpty(String title, String message) {
        files = List.of();
        tabs.getTabs().clear();
        warnings.getChildren().clear();
        show(warnings, false);
        show(qualityCard, false);
        show(explanationCard, false);
        emptyTitle.setText(title);
        emptyBody.setText(message);
        emptyState.getStyleClass().remove("error-state");
        setEmptyVisible(true);
        refreshSelection();
    }

    void showError(String title, String message) {
        showEmpty(title, message);
        emptyState.getStyleClass().add("error-state");
    }

    Optional<ForgeFile> selected() {
        int i = tabs.getSelectionModel().getSelectedIndex();
        return i >= 0 && i < files.size() ? Optional.of(files.get(i)) : Optional.empty();
    }

    List<ForgeFile> files() {
        return files;
    }

    private void renderQuality(ForgeResult.Quality q) {
        scoreNumber.setText(String.valueOf(q.score()));
        grade.setText(q.grade());
        grade.getStyleClass().removeIf(c -> c.startsWith("grade-") && !c.equals("grade-pill"));
        grade.getStyleClass().add("grade-" + q.grade().toLowerCase(Locale.ROOT).replace(' ', '-'));

        dimensionsBox.getChildren().clear();
        for (ForgeResult.Dimension d : q.dimensions()) dimensionsBox.getChildren().add(dimensionRow(d));
        show(dimensionsBox, !q.dimensions().isEmpty());

        findingsBox.getChildren().clear();
        if (q.findings().isEmpty()) {
            Label ok = new Label("Nothing to fix. This prompt is specific, checkable and well-shaped.");
            ok.getStyleClass().add("finding");
            ok.setWrapText(true);
            findingsBox.getChildren().add(ok);
        } else {
            // Warnings first, then tips.
            List<ForgeResult.Finding> ordered = q.findings().stream()
                    .sorted((a, b) -> Boolean.compare(b.isWarning(), a.isWarning())).toList();
            ordered.stream().limit(MAX_FINDINGS_SHOWN).forEach(f -> findingsBox.getChildren().add(findingRow(f)));
            if (ordered.size() > MAX_FINDINGS_SHOWN) {
                Label more = new Label("+ " + (ordered.size() - MAX_FINDINGS_SHOWN) + " more suggestions");
                more.getStyleClass().add("hint");
                Tooltip.install(more, new Tooltip(String.join("\n", ordered.stream().skip(MAX_FINDINGS_SHOWN)
                        .map(ForgeResult.Finding::message).toList())));
                findingsBox.getChildren().add(more);
            }
        }
        show(qualityCard, true);
    }

    private static Node dimensionRow(ForgeResult.Dimension d) {
        Label name = new Label(d.name());
        name.getStyleClass().add("dim-name");
        Label value = new Label(String.valueOf(d.score()));
        value.getStyleClass().add("dim-value");
        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);
        HBox head = new HBox(name, spacer, value);
        javafx.scene.control.ProgressBar bar = new javafx.scene.control.ProgressBar(d.score() / 100.0);
        bar.setMaxWidth(Double.MAX_VALUE);
        bar.getStyleClass().addAll("dim-bar", d.score() >= 85 ? "dim-high" : d.score() >= 60 ? "dim-mid" : "dim-low");
        bar.setAccessibleText(d.name() + " " + d.score() + " out of 100");
        VBox row = new VBox(2, head, bar);
        Tooltip.install(row, new Tooltip(d.hint()));
        return row;
    }

    private Node findingRow(ForgeResult.Finding f) {
        Region dot = new Region();
        dot.getStyleClass().addAll("finding-dot", f.isWarning() ? "finding-warning" : "finding-tip");
        Label text = new Label(f.message());
        text.getStyleClass().add("finding");
        text.setWrapText(true);
        HBox.setHgrow(text, Priority.ALWAYS);
        HBox row = new HBox(10, dot, text);
        row.setAlignment(Pos.TOP_LEFT);
        dot.setTranslateY(4);
        if (!f.field().isBlank()) {
            row.setCursor(Cursor.HAND);
            Tooltip.install(row, new Tooltip((f.isWarning() ? "Warning" : "Tip") + ": click to jump to the field"));
            row.setOnMouseClicked(e -> actions.focusField(f.field()));
        }
        return row;
    }

    private Tab tabFor(ForgeFile f) {
        TextArea area = new TextArea(f.content());
        area.setEditable(false);
        area.setWrapText(true);
        area.getStyleClass().add("code");
        area.setAccessibleText("Generated " + f.path());
        Tab tab = new Tab(f.path(), area);
        tab.setTooltip(new Tooltip(f.description()));
        return tab;
    }

    private void refreshSelection() {
        Optional<ForgeFile> f = selected();
        boolean has = f.isPresent();
        copy.setDisable(!has);
        save.setDisable(!has);
        test.setDisable(!has);
        explainToggle.setDisable(!has);
        show(saveAll, files.size() > 1);
        if (actionsRow != null) show(actionsRow, has);
        description.setText(f.map(ForgeFile::description).orElse(""));
        show(description, has);
        stats.setText(f.map(x -> String.format("≈ %,d tokens · %,d chars", x.estimatedTokens(), x.content().length())).orElse(""));
    }

    private void setEmptyVisible(boolean empty) {
        emptyState.setVisible(empty);
        emptyState.setManaged(empty);
        tabs.setVisible(!empty);
    }

    private static void show(Node node, boolean visible) {
        node.setVisible(visible);
        node.setManaged(visible);
    }

    private static void fadeIn(Node node) {
        FadeTransition ft = new FadeTransition(Duration.millis(220), node);
        ft.setFromValue(0.15);
        ft.setToValue(1);
        ft.play();
    }
}
