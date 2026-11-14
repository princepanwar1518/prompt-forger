package com.panwarstudio.promptforger.ui;

import com.panwarstudio.promptforger.engine.EngineMeta.Option;
import java.util.List;
import java.util.function.BiConsumer;
import javafx.geometry.Pos;
import javafx.scene.control.Button;
import javafx.scene.control.ComboBox;
import javafx.scene.control.Label;
import javafx.scene.control.ProgressIndicator;
import javafx.scene.control.TextArea;
import javafx.scene.control.Tooltip;
import javafx.scene.input.KeyCode;
import javafx.scene.input.KeyEvent;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.VBox;

/** "Describe it": plain-language request in, filled form out. Lime card at the top of the form. */
final class DescribeCard extends VBox {

    private final TextArea input = new TextArea();
    private final ComboBox<Option> provider = new ComboBox<>();
    private final Button fill = new Button("Fill the form  →");
    private final ProgressIndicator spinner = new ProgressIndicator();
    private final Label status = new Label();

    /** onFill receives (description, providerId). */
    DescribeCard(List<Option> providers, String selectedProvider, BiConsumer<String, String> onFill,
                 java.util.function.Consumer<String> onProviderChanged) {
        getStyleClass().addAll("card", "lime");
        setSpacing(12);

        Label eyebrow = new Label("01  ·  START HERE");
        eyebrow.getStyleClass().add("eyebrow");
        Label title = new Label("Describe it in plain words");
        title.getStyleClass().add("describe-title");
        title.setWrapText(true);
        Label sub = new Label("Hindi, Hinglish or English. The form fills itself, and you stay in control.");
        sub.getStyleClass().add("hint");
        sub.setWrapText(true);

        input.setWrapText(true);
        input.setPrefRowCount(3);
        input.setPromptText("e.g. I need emails for clients who haven't paid, polite but firm, under 120 words");
        input.setAccessibleText("Describe what you need in plain words");
        input.addEventFilter(KeyEvent.KEY_PRESSED, e -> {
            if (e.getCode() == KeyCode.ENTER && e.isShortcutDown()) {
                e.consume();
                fire(onFill);
            }
        });

        provider.getItems().setAll(providers);
        providers.stream().filter(p -> p.id().equals(selectedProvider)).findFirst()
                .ifPresentOrElse(provider::setValue, () -> provider.getSelectionModel().selectFirst());
        provider.setAccessibleText("Which engine fills the form");
        provider.valueProperty().addListener((obs, o, n) -> {
            if (n != null) {
                provider.setTooltip(new Tooltip(n.hint()));
                onProviderChanged.accept(n.id());
            }
        });
        if (provider.getValue() != null) provider.setTooltip(new Tooltip(provider.getValue().hint()));

        fill.getStyleClass().add("ink");
        fill.setDefaultButton(false);
        fill.setTooltip(new Tooltip("Fill the form from your description (Ctrl+Enter)"));
        fill.setOnAction(e -> fire(onFill));
        spinner.setMaxSize(22, 22);
        spinner.setVisible(false);
        spinner.setManaged(false);
        status.getStyleClass().add("describe-status");
        status.setWrapText(true);

        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);
        HBox actions = new HBox(10, provider, spacer, spinner, fill);
        actions.setAlignment(Pos.CENTER_LEFT);

        getChildren().addAll(eyebrow, title, sub, input, actions, status);
        status.setVisible(false);
        status.setManaged(false);
    }

    private void fire(BiConsumer<String, String> onFill) {
        String text = input.getText().strip();
        if (text.isEmpty()) {
            setStatus("Type a sentence or two first.");
            input.requestFocus();
            return;
        }
        onFill.accept(text, provider.getValue() == null ? "rules" : provider.getValue().id());
    }

    void setBusy(boolean busy) {
        fill.setDisable(busy);
        input.setDisable(busy);
        provider.setDisable(busy);
        spinner.setVisible(busy);
        spinner.setManaged(busy);
        if (busy) setStatus("Thinking…");
    }

    void setStatus(String text) {
        boolean has = text != null && !text.isBlank();
        status.setText(has ? text : "");
        status.setVisible(has);
        status.setManaged(has);
    }

    void focusInput() {
        input.requestFocus();
    }

    String text() {
        return input.getText();
    }
}
