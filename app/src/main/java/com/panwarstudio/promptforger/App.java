package com.panwarstudio.promptforger;

import com.panwarstudio.promptforger.engine.EngineClient;
import com.panwarstudio.promptforger.storage.AppLog;
import com.panwarstudio.promptforger.storage.AppPaths;
import com.panwarstudio.promptforger.storage.PresetStore;
import com.panwarstudio.promptforger.storage.SettingsStore;
import com.panwarstudio.promptforger.ui.MainView;
import com.panwarstudio.promptforger.ui.ThemeManager;
import com.panwarstudio.promptforger.ui.Toast;
import java.nio.file.Path;
import java.util.Objects;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.geometry.Pos;
import javafx.scene.Node;
import javafx.scene.Scene;
import javafx.scene.control.Label;
import javafx.scene.control.ProgressIndicator;
import javafx.scene.image.Image;
import javafx.scene.layout.StackPane;
import javafx.scene.layout.VBox;
import javafx.scene.text.Font;
import javafx.stage.Stage;

/** Prompt Forger: JavaFX front end over a Python prompt engine. */
public final class App extends Application {

    private final EngineClient engine = new EngineClient();
    private final StackPane content = new StackPane();
    private final Toast toast = new Toast();
    private SettingsStore settingsStore;
    private PresetStore presetStore;
    private MainView mainView;

    public App() {
        // created by Application.launch
    }

    public static void main(String[] args) {
        launch(args);
    }

    private static final String[] FONTS = {
        "BricolageGrotesque-Display.ttf", "BricolageGrotesque-Bold.ttf", "SpaceGrotesk-Regular.ttf",
        "SpaceGrotesk-SemiBold.ttf", "SpaceGrotesk-Bold.ttf", "DMMono-Regular.ttf", "DMMono-Medium.ttf"
    };

    /**
     * Registers the bundled fonts so CSS can refer to them by family name. Fonts are copied once into the
     * data folder and loaded by file URL: Font.loadFont(InputStream) would create a temp file on every launch.
     */
    private static void loadFonts(Path dataDir) {
        Path dir = dataDir.resolve("fonts");
        for (String name : FONTS) {
            try (var in = App.class.getResourceAsStream("fonts/" + name)) {
                if (in == null) {
                    AppLog.get().warning("font missing from app: " + name);
                    continue;
                }
                byte[] bytes = in.readAllBytes();
                Path target = dir.resolve(name);
                if (!java.nio.file.Files.isRegularFile(target) || java.nio.file.Files.size(target) != bytes.length) {
                    java.nio.file.Files.createDirectories(dir);
                    java.nio.file.Files.write(target, bytes);
                }
                if (Font.loadFont(target.toUri().toString(), 13) == null) AppLog.get().warning("font not loaded: " + name);
            } catch (java.io.IOException | RuntimeException e) {
                AppLog.get().warning("font not loaded: " + name + " (" + e.getMessage() + ")");
            }
        }
    }

    @Override
    public void start(Stage stage) {
        Path dataDir = AppPaths.dataDir();
        AppLog.init(dataDir);
        AppLog.get().info("Prompt Forger starting (Java " + System.getProperty("java.version") + ")");
        loadFonts(dataDir);
        settingsStore = new SettingsStore(dataDir);
        presetStore = new PresetStore(dataDir);
        SettingsStore.Settings settings = settingsStore.load();

        StackPane root = new StackPane(content, toast);
        root.getStyleClass().add("app-root");
        Scene scene = new Scene(root, 1280, 820);
        scene.getStylesheets().add(Objects.requireNonNull(App.class.getResource("app.css")).toExternalForm());
        ThemeManager.apply(root, settings.theme());

        stage.setTitle("Prompt Forger");
        stage.setMinWidth(900);
        stage.setMinHeight(600);
        var icon = App.class.getResourceAsStream("icon.png");
        if (icon != null) stage.getIcons().add(new Image(icon));
        stage.setScene(scene);
        stage.setOnCloseRequest(e -> {
            if (mainView != null) mainView.persistSettings();
        });
        stage.show();

        connect(settings);
    }

    private void connect(SettingsStore.Settings settings) {
        content.getChildren().setAll(loading());
        engine.meta().whenComplete((meta, error) -> Platform.runLater(() -> {
            if (error != null) {
                AppLog.get().severe("engine failed to start: " + error + " | " + engine.stderrTail());
                Node screen = MainView.errorScreen(
                        "The prompt engine could not start", error, engine.describe() + "\n" + engine.stderrTail(),
                        () -> connect(settingsStore.load()));
                content.getChildren().setAll(screen);
                return;
            }
            mainView = new MainView(engine, meta, presetStore, settingsStore, settings, toast);
            content.getChildren().setAll(mainView);
        }));
    }

    private static Node loading() {
        ProgressIndicator spinner = new ProgressIndicator();
        spinner.setMaxSize(36, 36);
        Label label = new Label("Warming up the forge…");
        label.getStyleClass().add("display");
        VBox box = new VBox(12, spinner, label);
        box.setAlignment(Pos.CENTER);
        return box;
    }

    @Override
    public void stop() {
        engine.close();
    }
}
