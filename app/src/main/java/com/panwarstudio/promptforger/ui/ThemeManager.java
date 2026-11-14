package com.panwarstudio.promptforger.ui;

import com.panwarstudio.promptforger.storage.SettingsStore.Theme;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import javafx.scene.Parent;

/** Applies light/dark styling. "System" follows the Windows app theme setting. */
public final class ThemeManager {

    private static final String DARK = "dark";
    private static Boolean cachedSystemDark;

    private ThemeManager() {}

    public static void apply(Parent root, Theme theme) {
        boolean dark = switch (theme) {
            case DARK -> true;
            case LIGHT -> false;
            case SYSTEM -> systemPrefersDark();
        };
        root.getStyleClass().remove(DARK);
        if (dark) root.getStyleClass().add(DARK);
    }

    public static boolean isDark(Parent root) {
        return root.getStyleClass().contains(DARK);
    }

    static synchronized boolean systemPrefersDark() {
        if (cachedSystemDark != null) return cachedSystemDark;
        boolean dark = false;
        if (System.getProperty("os.name", "").toLowerCase(Locale.ROOT).contains("win")) {
            try {
                Process p = new ProcessBuilder(
                                "reg", "query", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                                "/v", "AppsUseLightTheme")
                        .redirectErrorStream(true)
                        .start();
                String out = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
                if (p.waitFor(2, TimeUnit.SECONDS)) dark = out.matches("(?s).*AppsUseLightTheme\\s+REG_DWORD\\s+0x0\\b.*");
                else p.destroyForcibly();
            } catch (IOException e) {
                dark = false;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        cachedSystemDark = dark;
        return dark;
    }
}
