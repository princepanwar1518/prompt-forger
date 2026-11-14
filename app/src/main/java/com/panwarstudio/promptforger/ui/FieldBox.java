package com.panwarstudio.promptforger.ui;

import javafx.scene.Node;
import javafx.scene.control.Label;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.VBox;

/** Label + optional badge + counter, the control, then a hint that is replaced by an error when invalid. */
final class FieldBox extends VBox {

    private final Label hint = new Label();
    private final Label error = new Label();
    private final Label counter = new Label();
    private final Node control;
    private final String hintText;

    FieldBox(String labelText, boolean optional, String hintText, Node control) {
        this.control = control;
        this.hintText = hintText;
        getStyleClass().add("field");

        Label label = new Label(labelText);
        label.getStyleClass().add("field-label");
        label.setLabelFor(control);
        HBox head = new HBox(6, label);
        head.getStyleClass().add("field-head");
        if (optional) {
            Label badge = new Label("optional");
            badge.getStyleClass().add("badge");
            head.getChildren().add(badge);
        }
        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);
        counter.getStyleClass().add("counter");
        head.getChildren().addAll(spacer, counter);

        hint.getStyleClass().add("hint");
        hint.setWrapText(true);
        error.getStyleClass().add("error-text");
        error.setWrapText(true);
        hint.setText(hintText == null ? "" : hintText);
        setVisible(error, false);
        setVisible(hint, hintText != null && !hintText.isBlank());

        getChildren().addAll(head, control, hint, error);
        if (control instanceof javafx.scene.control.Control c && hintText != null) c.setAccessibleHelp(hintText);
    }

    void setCount(int value, int max) {
        counter.setText(String.format("%,d / %,d", value, max));
        counter.getStyleClass().remove("counter-over");
        if (value > max) counter.getStyleClass().add("counter-over");
    }

    void setError(String message) {
        boolean has = message != null && !message.isBlank();
        error.setText(has ? message : "");
        setVisible(error, has);
        setVisible(hint, !has && hintText != null && !hintText.isBlank());
        control.getStyleClass().remove("invalid");
        if (has) control.getStyleClass().add("invalid");
        if (control instanceof javafx.scene.control.Control c) c.setAccessibleHelp(has ? message : hintText);
    }

    private static void setVisible(Node node, boolean visible) {
        node.setVisible(visible);
        node.setManaged(visible);
    }
}
