/** Prompt Forger desktop UI. The prompt engine runs as a separate Python process. */
module com.panwarstudio.promptforger {
    requires transitive javafx.controls;
    requires java.logging;

    exports com.panwarstudio.promptforger;
}
