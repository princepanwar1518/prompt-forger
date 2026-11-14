package com.panwarstudio.promptforger.ui;

import javafx.animation.FadeTransition;
import javafx.animation.PauseTransition;
import javafx.animation.SequentialTransition;
import javafx.animation.TranslateTransition;
import javafx.animation.ParallelTransition;
import javafx.geometry.Pos;
import javafx.scene.AccessibleRole;
import javafx.scene.control.Label;
import javafx.scene.layout.StackPane;
import javafx.util.Duration;

/** Small transient message at the bottom of the window. */
public final class Toast extends StackPane {

    public enum Tone { INFO, SUCCESS, ERROR }

    private final Label label = new Label();
    private SequentialTransition running;

    public Toast() {
        getStyleClass().add("toast-layer");
        setPickOnBounds(false);
        setMouseTransparent(true);
        label.getStyleClass().add("toast");
        label.setAccessibleRole(AccessibleRole.TEXT);
        label.setWrapText(true);
        label.setMaxWidth(520);
        label.setOpacity(0);
        StackPane.setAlignment(label, Pos.BOTTOM_CENTER);
        getChildren().add(label);
    }

    public void show(String message, Tone tone) {
        if (running != null) running.stop();
        label.setText(message);
        label.setAccessibleText(message);
        label.getStyleClass().removeAll("toast-info", "toast-success", "toast-error");
        label.getStyleClass().add("toast-" + tone.name().toLowerCase());

        FadeTransition in = new FadeTransition(Duration.millis(160), label);
        in.setFromValue(0);
        in.setToValue(1);
        TranslateTransition rise = new TranslateTransition(Duration.millis(160), label);
        rise.setFromY(12);
        rise.setToY(0);
        PauseTransition hold = new PauseTransition(Duration.millis(tone == Tone.ERROR ? 5000 : 2600));
        FadeTransition out = new FadeTransition(Duration.millis(220), label);
        out.setToValue(0);
        running = new SequentialTransition(new ParallelTransition(in, rise), hold, out);
        running.play();
    }
}
