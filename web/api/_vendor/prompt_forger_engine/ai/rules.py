"""Offline "Describe it": turns a plain-language request into form fields with keyword rules.

Deliberately simple and predictable. It covers common requests (emails, code, content, summaries,
reports...) and asks clarifying questions when it can't tell what is wanted. Basic Hinglish works.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Hinglish/Hindi-in-Latin words mapped to English so intent detection works on mixed input.
_HINGLISH = {
    "likho": "write", "likhna": "write", "likh": "write", "likhdo": "write", "banao": "make", "banana": "make",
    "bana": "make", "banado": "make", "chahiye": "need", "mujhe": "i", "mera": "my", "meri": "my", "mere": "my",
    "ke liye": "for", "ki liye": "for", "karo": "do", "kar do": "do", "samjhao": "explain", "samjha do": "explain",
    "batao": "tell", "bata do": "tell", "aur": "and", "fir": "then", "phir": "then", "uske baad": "then",
    "mat": "don't", "nahi": "not", "chota": "short", "chhota": "short", "lamba": "detailed", "achha": "good",
    "accha": "good", "hindi mein": "in hindi", "english mein": "in english", "grahak": "customer",
}


@dataclass(frozen=True)
class Intent:
    name: str
    keywords: tuple[str, ...]
    role: str
    output_schema: str = ""
    constraints: tuple[str, ...] = ()
    success: tuple[str, ...] = ()
    steps: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    # Phrases that decide the intent on their own (worth 3 ordinary keyword hits).
    strong: tuple[str, ...] = ()


INTENTS: tuple[Intent, ...] = (
    Intent("email", ("email", "e-mail", "mail", "reply to", "follow up", "follow-up", "cold outreach"),
           "professional business writer",
           "Subject: <subject line>\n\n<greeting>\n\n<body: 3 short paragraphs at most>\n\n<sign-off>",
           ("Keep the email under 200 words.",),
           ("The reader knows exactly what to do next.", "It can be sent without edits."),
           questions=("Who is the email to, and what do you want them to do after reading it?",)),
    Intent("code", ("api", "code", "function", "script", "bug", "debug", "backend", "frontend", "react", "python",
                    "java", "typescript", "sql", "database", "endpoint", "app", "website", "refactor", "deploy",
                    "pull request", "codebase", "compile", "compiles", "repo", "unit test"),
           "senior software engineer", "",
           ("Write production-ready code with no placeholders.", "State any assumption before relying on it."),
           ("The code runs without errors.", "All tests pass."),
           ("Clarify the requirements and edge cases", "Design the solution", "Implement it",
            "Write tests", "Review for security and performance"),
           ("Which language, framework and versions should it use?",)),
    Intent("social", ("linkedin", "instagram", "tweet", "twitter", "caption", "facebook", "reel", "youtube", "hashtag"),
           "social media copywriter",
           "<hook line>\n\n<2-4 short lines>\n\n<call to action>\n\n<3-5 hashtags>",
           ("Lead with a hook in the first line.",),
           ("A reader would stop scrolling at the first line.",),
           questions=("Which platform is it for, and who is the audience?",)),
    Intent("content", ("blog", "article", "post", "newsletter", "content", "essay", "story", "script for"),
           "content writer and editor",
           "# <title>\n\n<intro: 2-3 sentences>\n\n## <section heading>\n<body>\n\n## Conclusion\n<takeaway>",
           ("Use plain language and short paragraphs.",),
           ("Every section supports the title's promise.",),
           ("Outline the main points", "Write the draft", "Edit for clarity and length"),
           ("Who will read it, and roughly how long should it be?",)),
    Intent("summary", ("summarize", "summarise", "summary", "tl;dr", "tldr", "key points", "short version"),
           "analyst who writes clear, faithful summaries",
           "## Key points\n- <5 bullets at most>\n\n## One-line takeaway\n<one sentence>",
           ("Do not add facts that are not in the source.",),
           ("Someone who skips the source still gets the main decisions and numbers.",),
           questions=("Paste the text to summarise into Context. Who is the summary for?",)),
    Intent("translate", ("translate", "translation", "in hindi", "in english", "into hindi", "into english"),
           "professional translator",
           "",
           ("Keep names, numbers and formatting unchanged.", "Translate meaning, not word for word."),
           ("Names, numbers and formatting match the source exactly.", "A native speaker would find every sentence natural."),
           questions=("Which language should it be translated into, and how formal should it be?",)),
    Intent("analysis", ("analyze", "analyse", "analysis", "data", "report", "excel", "spreadsheet", "sales", "numbers",
                        "trend", "metrics", "dashboard"),
           "data analyst",
           "## Answer\n<one-paragraph answer with the key number>\n\n## Evidence\n<table or bullets>\n\n## Caveats\n<bullets>",
           ("Show the numbers behind every claim.", "Say clearly when the data can't answer the question."),
           ("The main question is answered in the first paragraph.",),
           ("Understand the question and the data", "Clean and check the data", "Analyse", "Summarise findings"),
           ("What decision will this analysis support?",)),
    Intent("career", ("resume", "cv", "cover letter", "interview", "job", "linkedin profile", "hiring"),
           "career coach and experienced recruiter",
           "",
           ("Keep every claim true to the details provided.",),
           ("A recruiter could shortlist the candidate from it in 30 seconds.",),
           questions=("Which role and company is this for? Paste your experience into Context.",),
           strong=("interview", "cover letter", "resume")),
    Intent("teach", ("explain", "teach", "learn", "understand", "notes", "exam", "study", "tutorial", "concept"),
           "patient teacher who explains with simple examples",
           "",
           ("Start simple, then add detail.", "Use one real-world example per idea."),
           ("A beginner can explain the idea back in 2-3 sentences.",),
           questions=("What does the learner already know?",)),
    Intent("marketing", ("marketing", "campaign", "strategy", "launch", "business plan", "pitch", "brand", "ads",
                         "seo", "sales pitch"),
           "marketing strategist",
           "## Goal\n<goal>\n\n## Audience\n<audience>\n\n## Plan\n<steps with owners and dates>\n\n## Metrics\n<how success is measured>",
           ("Tie every recommendation to the audience and the goal.",),
           ("The plan has measurable targets and a timeline.",),
           questions=("What is the product, who is it for, and what's the budget?",),
           strong=("pitch", "campaign", "marketing plan", "go-to-market")),
    Intent("support", ("customer", "complaint", "support", "refund", "angry", "ticket"),
           "calm, empathetic customer support lead",
           "",
           ("Acknowledge the problem before offering a solution.", "Never blame the customer."),
           ("The customer knows what will happen next and when.",)),
)

_LOOP_HINTS = ("keep going", "until done", "until finished", "until it works", "autonomous", "autonomously",
               "loop", "iterate until", "keep trying", "overnight")
_GRAPH_HINTS = ("review and revise", "draft then review", "then review", "multi-stage", "stages", "pipeline",
                "workflow with checks", "quality check")
_AGENT_HINTS = ("subagent", "an agent", "agent that", "assistant that always", "whenever i", "every time i",
                "reusable assistant")
_TONES = ("formal", "casual", "friendly", "professional", "funny", "polite", "firm", "warm", "confident", "playful")
_NEGATIVE = re.compile(r"\b(?:don't|dont|do not|never|avoid|without|must not|no)\b[^.,;!?\n]*", re.IGNORECASE)
_LENGTH = re.compile(r"\b(?:under|max(?:imum)?|less than|at most|within)?\s*(\d{2,5})\s*(words|characters|chars|lines)\b",
                     re.IGNORECASE)
_PEOPLE = ("client", "customer", "beginner", "student", "team", "manager", "boss", "investor", "kid", "child",
           "user", "reader", "developer", "engineer", "audience", "follower", "parent", "recruiter", "teacher",
           "employee", "colleague", "founder", "executive", "patient", "buyer", "subscriber", "owner")
# Audience = "for/aimed at/targeting [my|our|the] [up to 2 describing words] <people word>", or "explain X to <people>".
_AUDIENCE = re.compile(r"\b(?:for|aimed at|targeting|to) (my |our |the )?((?:[a-z\-]+ ){0,2}?(?:%s)(?:s|es)?)\b"
                       % "|".join(_PEOPLE), re.IGNORECASE)
_VERBS_NOT_AUDIENCE = {"chase", "email", "remind", "reply", "send", "write", "contact", "call", "help", "ask", "tell", "pay", "bill", "invoice", "message"}
_UNTIL = re.compile(r"\buntil ([^.,;!?\n]{4,80})", re.IGNORECASE)
_STEP_SPLIT = re.compile(r"\b(?:and then|after that|then|next|finally|second|third|lastly)\b,?|;", re.IGNORECASE)
_STEP_NOISE = re.compile(r"\b(?:keep going|keep trying|iterate)\b.*$|\b(?:don't|dont|do not|never|avoid)\b.*$", re.IGNORECASE)


def normalise(text: str) -> str:
    out = f" {text.lower()} "
    for src in sorted(_HINGLISH, key=len, reverse=True):
        out = re.sub(rf"(?<![a-z]){re.escape(src)}(?![a-z])", _HINGLISH[src], out)
    return " ".join(out.split())


def _match(norm: str) -> list[tuple[Intent, int]]:
    scored = []
    for intent in INTENTS:
        def has(k: str) -> bool:
            return re.search(rf"(?<![a-z]){re.escape(k)}(?:s|es)?(?![a-z])", norm) is not None

        hits = sum(1 for k in intent.keywords if has(k)) + sum(3 for k in intent.strong if has(k))
        if hits:
            scored.append((intent, hits))
    return sorted(scored, key=lambda x: -x[1])


def _sentence_case(s: str) -> str:
    s = s.strip(" ,.;")
    return s[:1].upper() + s[1:] if s else s


@dataclass
class RulesResult:
    form: dict[str, str] = field(default_factory=dict)
    questions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


def describe_with_rules(text: str) -> RulesResult:
    raw = " ".join(text.split())
    norm = normalise(raw)
    res = RulesResult()
    words = norm.split()
    matches = _match(norm)
    intent = matches[0][0] if matches else None

    task = _sentence_case(raw)
    if not task.endswith((".", "?", "!")):
        task += "."
    res.form["task"] = task

    if intent:
        res.form["role"] = intent.role
        if intent.output_schema:
            res.form["outputSchema"] = intent.output_schema
        res.notes.append(f"Recognised a {intent.name} request.")
    else:
        res.form["role"] = "experienced specialist in this field"

    # Steps the user wrote ("first..., then..., finally...") beat the intent's template.
    step_text = raw
    first = re.search(r"\bfirst\b,?", raw, re.IGNORECASE)
    if first:
        step_text = raw[first.end():]  # what comes before "first" is the goal, not a step
    parts = []
    for p in _STEP_SPLIT.split(step_text):
        p = _STEP_NOISE.sub("", p or "").strip(" ,.")
        if len(p.split()) >= 2:
            parts.append(p)
    if len(parts) >= 2:
        res.form["steps"] = "\n".join(_sentence_case(p) for p in parts)
    elif intent and intent.steps:
        res.form["steps"] = "\n".join(intent.steps)

    constraints = list(intent.constraints) if intent else []
    for m in _NEGATIVE.finditer(raw):
        c = _sentence_case(re.sub(r"^dont\b", "don't", m.group(0), flags=re.IGNORECASE))
        if len(c.split()) >= 2:
            constraints.append(c + ".")
    length = _LENGTH.search(raw)
    if length:
        constraints = [c for c in constraints if not re.search(r"\bunder \d+ words\b", c, re.IGNORECASE)]
        constraints.append(f"Keep it under {length.group(1)} {length.group(2).lower()}.")
    tones = [t for t in _TONES if re.search(rf"\b{t}\b", norm)]
    if tones:
        constraints.append(f"Use a {' and '.join(tones)} tone.")
    if constraints:
        res.form["constraints"] = "\n".join(dict.fromkeys(constraints))
    success = [_sentence_case(m.group(1)) + "." for m in _UNTIL.finditer(raw)]
    if intent:
        success += list(intent.success)
    if success:
        res.form["successCriteria"] = "\n".join(dict.fromkeys(success))

    audience = next((m for m in _AUDIENCE.finditer(raw)
                     if m.group(2).split()[0].lower() not in _VERBS_NOT_AUDIENCE), None)
    if audience:
        res.form["context"] = f"Audience: {(audience.group(1) or '').strip()} {audience.group(2).strip()}.".replace(":  ", ": ").replace(":  ", ": ")

    if any(h in norm for h in _LOOP_HINTS):
        res.form["format"] = "ralph"
    elif any(h in norm for h in _GRAPH_HINTS):
        res.form["format"] = "graph"
    elif any(h in norm for h in _AGENT_HINTS):
        res.form["format"] = "agent"

    if re.search(r"\b(short|brief|quick|concise)\b", norm):
        res.form["verbosity"] = "concise"
    elif re.search(r"\b(detailed|in depth|in-depth|thorough|comprehensive)\b", norm):
        res.form["verbosity"] = "detailed"

    # Confidence: matched intent, enough words, and some specifics.
    conf = 0.25 + (0.35 if intent else 0) + min(len(words), 20) / 20 * 0.25 + (0.15 if constraints or audience else 0)
    res.confidence = round(min(conf, 1.0), 2)

    if not intent:
        res.questions.append("What exactly should the result be (an email, code, a plan, a post...)?")
    if (len(words) < 6 or not intent) and not audience:
        res.questions.append("Who is it for?")
    if intent and intent.questions and res.confidence < 0.85:
        res.questions.extend(q for q in intent.questions if q not in res.questions)
    if "successCriteria" not in res.form:
        res.questions.append("How will you know the result is good?")
    res.questions = res.questions[:3]
    return res
