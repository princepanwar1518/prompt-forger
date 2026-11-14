package com.panwarstudio.promptforger.engine;

/** Engine failed to start, crashed, timed out, or answered with an error. */
public final class EngineException extends RuntimeException {

    private static final long serialVersionUID = 1L;
    private final String code;

    public EngineException(String code, String message) {
        super(message);
        this.code = code;
    }

    public EngineException(String code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
    }

    public String code() {
        return code;
    }
}
