package com.panwarstudio.promptforger.ui;

import com.panwarstudio.promptforger.engine.EngineMeta;
import com.panwarstudio.promptforger.engine.EngineMeta.Option;
import com.panwarstudio.promptforger.model.FormState;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.UnaryOperator;
import javafx.geometry.Insets;
import javafx.scene.Node;
import javafx.scene.control.ComboBox;
import javafx.scene.control.ContentDisplay;
import javafx.scene.control.Label;
import javafx.scene.control.ScrollPane;
import javafx.scene.control.TextArea;
import javafx.scene.control.TextField;
import javafx.scene.control.TextFormatter;
import javafx.scene.control.TextInputControl;
import javafx.scene.control.TitledPane;
import javafx.scene.control.Toggle;
import javafx.scene.control.ToggleButton;
import javafx.scene.control.ToggleGroup;
import javafx.scene.layout.ColumnConstraints;
import javafx.scene.layout.GridPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.VBox;

/** The input form. Reads/writes {@link FormState}; shows engine validation errors on touched fields. */
final class FormPane extends ScrollPane {

    private static final int MAX_ROLE = 300;
    private static final int MAX_TASK = 8_000;
    private static final int MAX_CONTEXT = 50_000;
    private static final int MAX_LIST = 50;
    private static final double CARD_HEIGHT = 98;

    private final TextField role = new TextField();
    private final TextArea task = textArea(4);
    private final TextArea steps = textArea(4);
    private final TextArea context = textArea(3);
    private final TextArea constraints = textArea(3);
    private final TextArea successCriteria = textArea(3);
    private final TextArea examples = textArea(4);
    private final TextArea outputSchema = textArea(4);
    private final TextArea variables = textArea(2);
    private final TextField tools = new TextField();
    private final ToggleGroup formatGroup = new ToggleGroup();
    private final ComboBox<Option> model = new ComboBox<>();
    private final Label modelHint = new Label();
    private final ToggleGroup verbosityGroup = new ToggleGroup();
    private final TextField tokenBudget = numberField(7, "e.g. 2000");
    private final TextField maxIterations = numberField(3, "default");
    private final TitledPane moreDetail;

    private final Map<String, FieldBox> fields = new HashMap<>();
    private final Set<String> touched = new HashSet<>();
    private final FieldBox iterationsBox;
    private final FieldBox toolsBox;
    private Runnable onChange = () -> {};
    private boolean writing;

    FormPane(EngineMeta meta, Node describeCard) {
        getStyleClass().add("form-scroll");
        setFitToWidth(true);
        setHbarPolicy(ScrollBarPolicy.NEVER);

        role.setPromptText("e.g. senior backend engineer");
        task.setPromptText("What needs to be done? Be specific about the goal and constraints.");
        steps.setPromptText("One step per line, e.g. Design the schema");
        context.setPromptText("Background, audience, existing code, inputs...");
        constraints.setPromptText("One rule per line, e.g. Never store plain-text passwords");
        successCriteria.setPromptText("One per line, e.g. All tests pass");
        examples.setPromptText("Input: ...  Output: ...   (separate examples with a line of ---)");
        outputSchema.setPromptText("The exact shape of the answer: sections, a template or JSON");
        variables.setPromptText("name = value   (use {{name}} anywhere in the form)");
        tools.setPromptText("Read, Grep, Bash(git:*)");
        outputSchema.getStyleClass().add("mono");

        FieldBox roleBox = field("role", "Role", false, "Who the model should act as.", role);
        FieldBox taskBox = field("task", "Task", false, null, task);
        FieldBox stepsBox = field("steps", "Steps", true, "One per line. List markers like 1. or - are removed.", steps);
        FieldBox contextBox = field("context", "Context", true, null, context);

        FieldBox constraintsBox = field("constraints", "Constraints", true, "Rules the model must not break.", constraints);
        FieldBox successBox = field("successCriteria", "Success criteria", true, "How the model knows it's done. Loops need these.", successCriteria);
        FieldBox examplesBox = field("examples", "Examples", true, "1-3 sample answers. Separate them with a line of ---.", examples);
        FieldBox schemaBox = field("outputSchema", "Output schema", true, "Sections, a template or JSON. JSON is checked.", outputSchema);
        FieldBox variablesBox = field("variables", "Variables", true, "Fill {{placeholders}} used anywhere above.", variables);
        toolsBox = field("tools", "Tools", true, "Agent profiles only: the tools the agent may use.", tools);
        VBox detail = new VBox(14, constraintsBox, successBox, examplesBox, schemaBox, variablesBox, toolsBox);
        moreDetail = new TitledPane("More detail: constraints, success criteria, examples, schema", detail);
        moreDetail.setExpanded(false);
        moreDetail.setAnimated(true);

        GridPane formatCards = new GridPane(10, 10);
        for (int c = 0; c < 2; c++) {
            ColumnConstraints col = new ColumnConstraints();
            col.setPercentWidth(50);
            col.setFillWidth(true);
            formatCards.getColumnConstraints().add(col);
        }
        List<Option> formats = meta.formats();
        for (int i = 0; i < formats.size(); i++) formatCards.add(formatCard(i + 1, formats.get(i)), i % 2, i / 2);
        keepOneSelected(formatGroup);
        FieldBox formatBox = field("format", "Output format", false, null, formatCards);

        model.getItems().setAll(meta.models());
        model.setMaxWidth(Double.MAX_VALUE);
        model.setAccessibleText("Target model");
        modelHint.getStyleClass().add("hint");
        model.valueProperty().addListener((obs, o, n) -> {
            modelHint.setText(n == null ? "" : n.hint());
            changed("model");
        });
        FieldBox modelBox = field("model", "Target model", false, null, new VBox(5, model, modelHint));

        HBox verbosity = new HBox();
        verbosity.getStyleClass().add("segmented");
        for (Option opt : meta.verbosity()) {
            ToggleButton b = new ToggleButton(opt.label());
            b.setUserData(opt.id());
            b.setToggleGroup(verbosityGroup);
            b.setMaxWidth(Double.MAX_VALUE);
            HBox.setHgrow(b, Priority.ALWAYS);
            verbosity.getChildren().add(b);
        }
        keepOneSelected(verbosityGroup);
        verbosityGroup.selectedToggleProperty().addListener((obs, o, n) -> changed("verbosity"));
        FieldBox verbosityBox = field("verbosity", "Verbosity", false, null, verbosity);

        FieldBox budgetBox = field("tokenBudget", "Token budget", true, "Response length cap, in tokens.", tokenBudget);
        iterationsBox = field("maxIterations", "Max iterations", true, "Loop safety stop.", maxIterations);
        GridPane numbers = new GridPane(12, 0);
        numbers.add(budgetBox, 0, 0);
        numbers.add(iterationsBox, 1, 0);
        GridPane.setHgrow(budgetBox, Priority.ALWAYS);
        GridPane.setHgrow(iterationsBox, Priority.ALWAYS);
        budgetBox.setMaxWidth(Double.MAX_VALUE);
        iterationsBox.setMaxWidth(Double.MAX_VALUE);

        VBox content = new VBox(16,
                describeCard,
                heading("02", "The prompt"), roleBox, taskBox, stepsBox, contextBox, moreDetail,
                heading("03", "Settings"), formatBox, modelBox, verbosityBox, numbers);
        content.getStyleClass().add("form");
        content.setPadding(new Insets(22, 26, 32, 22));
        setContent(content);

        bindText("role", role, MAX_ROLE, roleBox);
        bindText("task", task, MAX_TASK, taskBox);
        bindText("context", context, MAX_CONTEXT, contextBox);
        bindText("outputSchema", outputSchema, -1, schemaBox);
        bindText("examples", examples, -1, examplesBox);
        bindText("variables", variables, -1, variablesBox);
        bindText("tools", tools, -1, toolsBox);
        bindText("tokenBudget", tokenBudget, -1, budgetBox);
        bindText("maxIterations", maxIterations, -1, iterationsBox);
        bindLines("steps", steps, stepsBox);
        bindLines("constraints", constraints, constraintsBox);
        bindLines("successCriteria", successCriteria, successBox);
        formatGroup.selectedToggleProperty().addListener((obs, o, n) -> {
            updateFormatDependentFields();
            changed("format");
        });
    }

    // ------------------------------------------------------------------ state

    void setOnChange(Runnable onChange) {
        this.onChange = onChange;
    }

    FormState read() {
        return new FormState(
                role.getText(), task.getText(), steps.getText(), context.getText(),
                constraints.getText(), successCriteria.getText(), examples.getText(), outputSchema.getText(),
                variables.getText(), tools.getText(),
                selectedId(formatGroup, "standard"),
                model.getValue() == null ? "claude-sonnet" : model.getValue().id(),
                selectedId(verbosityGroup, "balanced"),
                tokenBudget.getText(), maxIterations.getText());
    }

    void write(FormState s) {
        writing = true;
        try {
            role.setText(s.role());
            task.setText(s.task());
            steps.setText(s.steps());
            context.setText(s.context());
            constraints.setText(s.constraints());
            successCriteria.setText(s.successCriteria());
            examples.setText(s.examples());
            outputSchema.setText(s.outputSchema());
            variables.setText(s.variables());
            tools.setText(s.tools());
            select(formatGroup, s.format());
            model.getItems().stream().filter(o -> o.id().equals(s.model())).findFirst()
                    .ifPresentOrElse(model::setValue, () -> model.getSelectionModel().selectFirst());
            select(verbosityGroup, s.verbosity());
            tokenBudget.setText(digitsOnly(s.tokenBudget(), 7));
            maxIterations.setText(digitsOnly(s.maxIterations(), 3));
            touched.clear();
            if (!s.role().isBlank()) touched.add("role");
            if (!s.task().isBlank()) touched.add("task");
            boolean hasDetail = !(s.constraints() + s.successCriteria() + s.examples() + s.outputSchema()
                    + s.variables() + s.tools()).isBlank();
            if (hasDetail) moreDetail.setExpanded(true);
            updateFormatDependentFields();
        } finally {
            writing = false;
        }
        onChange.run();
    }

    /** Shows engine errors only for fields the user has interacted with. */
    void showErrors(Map<String, String> errors) {
        fields.forEach((key, box) -> box.setError(touched.contains(key) ? errors.get(key) : null));
        boolean detailError = errors.keySet().stream().anyMatch(k ->
                List.of("constraints", "successCriteria", "examples", "outputSchema", "variables", "tools").contains(k));
        if (detailError) moreDetail.setExpanded(true);
    }

    void focusFirst() {
        role.requestFocus();
        role.end();
    }

    boolean isBlank() {
        FormState s = read();
        return s.role().isBlank() && s.task().isBlank();
    }

    /** Opens "More detail" and focuses the field a checker finding points at. */
    void focusField(String key) {
        if (List.of("constraints", "successCriteria", "examples", "outputSchema", "variables", "tools").contains(key)) {
            moreDetail.setExpanded(true);
        }
        Node target = switch (key) {
            case "role" -> role;
            case "task" -> task;
            case "steps" -> steps;
            case "context" -> context;
            case "constraints" -> constraints;
            case "successCriteria" -> successCriteria;
            case "examples" -> examples;
            case "outputSchema" -> outputSchema;
            case "variables" -> variables;
            case "tools" -> tools;
            case "tokenBudget" -> tokenBudget;
            case "maxIterations" -> maxIterations;
            default -> null;
        };
        if (target != null) {
            target.requestFocus();
            // Scroll so the field is visible.
            javafx.application.Platform.runLater(() -> {
                double contentHeight = getContent().getBoundsInLocal().getHeight();
                double y = target.localToScene(0, 0).getY() - getContent().localToScene(0, 0).getY();
                setVvalue(Math.max(0, Math.min(1, (y - 80) / Math.max(1, contentHeight - getViewportBounds().getHeight()))));
            });
        }
    }

    // ------------------------------------------------------------------ builders

    private FieldBox field(String key, String label, boolean optional, String hint, Node control) {
        FieldBox box = new FieldBox(label, optional, hint, control);
        fields.put(key, box);
        return box;
    }

    private ToggleButton formatCard(int number, Option opt) {
        Label num = new Label(String.format("%02d", number));
        num.getStyleClass().add("format-num");
        Label title = new Label(opt.label());
        title.getStyleClass().add("format-title");
        Label hint = new Label(opt.hint());
        hint.getStyleClass().add("card-hint");
        hint.setWrapText(true);
        hint.setMinHeight(0);
        VBox graphic = new VBox(3, num, title, hint);
        graphic.setMinWidth(0);
        ToggleButton card = new ToggleButton();
        card.setGraphic(graphic);
        card.setContentDisplay(ContentDisplay.GRAPHIC_ONLY);
        card.setUserData(opt.id());
        card.setToggleGroup(formatGroup);
        card.getStyleClass().add("format-card");
        // Labeled controls mis-measure wrapped graphics, so cards get a fixed height that fits two hint lines.
        card.setMaxWidth(Double.MAX_VALUE);
        card.setMinWidth(0);
        card.setPrefWidth(220);
        card.setMinHeight(CARD_HEIGHT);
        card.setPrefHeight(CARD_HEIGHT);
        card.setMaxHeight(CARD_HEIGHT);
        card.setAccessibleText(opt.label() + ". " + opt.hint());
        return card;
    }

    private static Node heading(String number, String text) {
        Label num = new Label(number);
        num.getStyleClass().add("eyebrow");
        Label title = new Label(text);
        title.getStyleClass().add("section-title");
        HBox row = new HBox(10, num, title);
        row.setAlignment(javafx.geometry.Pos.BASELINE_LEFT);
        row.setPadding(new Insets(8, 0, 0, 0));
        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);
        row.getChildren().add(spacer);
        return row;
    }

    private static TextArea textArea(int rows) {
        TextArea a = new TextArea();
        a.setWrapText(true);
        a.setPrefRowCount(rows);
        return a;
    }

    private static TextField numberField(int maxDigits, String prompt) {
        TextField f = new TextField();
        f.setPromptText(prompt);
        UnaryOperator<TextFormatter.Change> filter = c -> {
            String next = c.getControlNewText();
            return next.length() <= maxDigits && next.chars().allMatch(Character::isDigit) ? c : null;
        };
        f.setTextFormatter(new TextFormatter<>(filter));
        return f;
    }

    private void bindText(String key, TextInputControl input, int max, FieldBox box) {
        input.textProperty().addListener((obs, o, n) -> {
            if (max > 0) box.setCount(n.length(), max);
            changed(key);
        });
        if (max > 0) box.setCount(0, max);
        markTouchedOnBlur(key, input);
    }

    private void bindLines(String key, TextInputControl input, FieldBox box) {
        input.textProperty().addListener((obs, o, n) -> {
            box.setCount((int) n.lines().filter(l -> !l.isBlank()).count(), MAX_LIST);
            changed(key);
        });
        markTouchedOnBlur(key, input);
    }

    private void markTouchedOnBlur(String key, TextInputControl input) {
        input.focusedProperty().addListener((obs, was, is) -> {
            // Leaving an empty field you never typed in is not "touching" it (e.g. tabbing past it).
            if (was && !is && !touched.contains(key) && !input.getText().isBlank()) {
                touched.add(key);
                onChange.run();
            }
        });
    }

    private void changed(String key) {
        if (writing) return;
        touched.add(key);
        onChange.run();
    }

    private void updateFormatDependentFields() {
        String fmt = selectedId(formatGroup, "standard");
        boolean loop = "ralph".equals(fmt) || "graph".equals(fmt);
        iterationsBox.setDisable(!loop);
        maxIterations.setPromptText(loop ? ("graph".equals(fmt) ? "default 3" : "default 20") : "loops only");
        boolean agent = "agent".equals(fmt);
        toolsBox.setVisible(agent);
        toolsBox.setManaged(agent);
    }

    private static void keepOneSelected(ToggleGroup group) {
        group.selectedToggleProperty().addListener((obs, old, now) -> {
            if (now == null && old != null) group.selectToggle(old);
        });
    }

    private static String selectedId(ToggleGroup group, String fallback) {
        Toggle t = group.getSelectedToggle();
        return t == null ? fallback : String.valueOf(t.getUserData());
    }

    private static void select(ToggleGroup group, String id) {
        group.getToggles().stream().filter(t -> id.equals(t.getUserData())).findFirst()
                .or(() -> group.getToggles().stream().findFirst())
                .ifPresent(group::selectToggle);
    }

    private static String digitsOnly(String s, int max) {
        String d = s.chars().filter(Character::isDigit)
                .collect(StringBuilder::new, StringBuilder::appendCodePoint, StringBuilder::append).toString();
        return d.length() > max ? d.substring(0, max) : d;
    }
}
