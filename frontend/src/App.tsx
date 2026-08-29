import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import type {
  AttemptResult,
  CourseSummary,
  CourseView,
  JudgeStatus,
  LearningPhase,
  PublicQuestion,
  PublicQuiz,
  TutorView,
  WorkspaceView,
} from "./types";

function scoreLabel(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function move<T>(items: T[], from: number, to: number): T[] {
  if (to < 0 || to >= items.length) return items;
  const copy = [...items];
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item);
  return copy;
}

function initialAnswers(quiz: PublicQuiz): Record<string, unknown> {
  return Object.fromEntries(
    quiz.questions
      .filter((question) => question.type === "ordering")
      .map((question) => [question.id, (question.options ?? []).map((option) => option.id)]),
  );
}

export function answersForRetry(
  quiz: PublicQuiz,
  currentAnswers: Record<string, unknown>,
  lastAttempt: AttemptResult | null,
): Record<string, unknown> {
  return {
    ...initialAnswers(quiz),
    ...(lastAttempt?.answers ?? {}),
    ...currentAnswers,
  };
}

export function nextLessonId(lessons: Array<{ id: string }>, currentLessonId: string): string | null {
  const currentIndex = lessons.findIndex((lesson) => lesson.id === currentLessonId);
  return currentIndex >= 0 ? lessons[currentIndex + 1]?.id ?? null : null;
}

function courseIdFromHash(): string | null {
  const match = window.location.hash.match(/^#\/lesson\/([a-z0-9-]+)$/);
  return match?.[1] ?? null;
}

function draftCacheKey(courseId: string, lessonId: string): string {
  return `socraites-draft:${courseId}:${lessonId}`;
}

function readDraftCache(courseId: string, lessonId: string): Record<string, unknown> | null {
  try {
    const value = window.localStorage.getItem(draftCacheKey(courseId, lessonId));
    if (!value) return null;
    const parsed = JSON.parse(value) as { answers?: unknown };
    return parsed.answers && typeof parsed.answers === "object"
      ? (parsed.answers as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function writeDraftCache(courseId: string, lessonId: string, answers: Record<string, unknown>) {
  try {
    window.localStorage.setItem(
      draftCacheKey(courseId, lessonId),
      JSON.stringify({ answers, updated_at: new Date().toISOString() }),
    );
  } catch {
    // The server remains authoritative; this cache only closes the debounce window on refresh.
  }
}

function FillParagraphInput({
  question,
  value,
  disabled,
  onChange,
}: {
  question: PublicQuestion;
  value: unknown;
  disabled: boolean;
  onChange: (value: unknown) => void;
}) {
  const [activeBlank, setActiveBlank] = useState<string | null>(null);
  const [closingBlank, setClosingBlank] = useState<string | null>(null);
  const closingBlankRef = useRef<string | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fadeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const selections = value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, string>)
    : {};
  const blanks = new Map((question.blanks ?? []).map((blank) => [blank.id, blank]));

  function cancelTimers() {
    if (closeTimer.current !== null) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
    if (fadeTimer.current !== null) {
      clearTimeout(fadeTimer.current);
      fadeTimer.current = null;
    }
  }

  function openBlank(blankId: string) {
    if (disabled) return;
    cancelTimers();
    closingBlankRef.current = null;
    setClosingBlank(null);
    setActiveBlank(blankId);
  }

  function beginClose(blankId: string) {
    cancelTimers();
    closingBlankRef.current = blankId;
    setActiveBlank(null);
    setClosingBlank(blankId);
    fadeTimer.current = setTimeout(() => {
      if (closingBlankRef.current === blankId) closingBlankRef.current = null;
      setClosingBlank((current) => current === blankId ? null : current);
      fadeTimer.current = null;
    }, 210);
  }

  function scheduleClose(blankId: string) {
    if (closingBlankRef.current === blankId) return;
    if (closeTimer.current !== null) clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => {
      closeTimer.current = null;
      beginClose(blankId);
    }, 750);
  }

  useEffect(() => () => cancelTimers(), []);

  const parts: ReactNode[] = [];
  const placeholder = /\{\{([a-z0-9][a-z0-9-]*)\}\}/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = placeholder.exec(question.prompt)) !== null) {
    if (match.index > cursor) parts.push(question.prompt.slice(cursor, match.index));
    const blank = blanks.get(match[1]);
    if (blank) {
      const selected = blank.options.find((option) => option.id === selections[blank.id]);
      const isOpen = activeBlank === blank.id;
      const isClosing = closingBlank === blank.id;
      const isVisible = isOpen || isClosing;
      parts.push(
        <span
          className={`fill-blank ${isOpen ? "open" : ""} ${isClosing ? "closing" : ""}`}
          key={`${blank.id}-${match.index}`}
          onMouseEnter={() => openBlank(blank.id)}
          onMouseLeave={() => scheduleClose(blank.id)}
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) scheduleClose(blank.id);
          }}
        >
          <button
            type="button"
            className={`fill-blank-trigger ${selected ? "answered" : ""}`}
            disabled={disabled}
            aria-expanded={isOpen}
            aria-haspopup="listbox"
            aria-label={selected ? `Change ${blank.id}, currently ${selected.label}` : `Fill ${blank.id}`}
            onFocus={() => openBlank(blank.id)}
            onClick={() => openBlank(blank.id)}
          >
            {selected?.label ?? "Choose"}
          </button>
          {isVisible && (
            <span className="fill-blank-popover" onMouseEnter={() => openBlank(blank.id)} onMouseLeave={() => scheduleClose(blank.id)}>
              <span className="fill-blank-choice-grid" role="listbox" aria-label={`Choices for ${blank.id}`}>
                {blank.options.map((option) => (
                  <button
                    type="button"
                    role="option"
                    aria-selected={selected?.id === option.id}
                    className={selected?.id === option.id ? "selected" : ""}
                    disabled={disabled}
                    key={option.id}
                    onClick={() => {
                      onChange({...selections, [blank.id]: option.id});
                      beginClose(blank.id);
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </span>
            </span>
          )}
        </span>,
      );
    }
    cursor = match.index + match[0].length;
  }
  if (cursor < question.prompt.length) parts.push(question.prompt.slice(cursor));

  return (
    <div className="fill-paragraph-wrap">
      <p className="fill-paragraph">{parts}</p>
      <p className="field-hint">Hover, focus, or tap a blank to choose an answer.</p>
    </div>
  );
}

function QuestionInput({
  question,
  value,
  disabled,
  onChange,
}: {
  question: PublicQuestion;
  value: unknown;
  disabled: boolean;
  onChange: (value: unknown) => void;
}) {
  const options = question.options ?? [];

  if (question.type === "single_choice") {
    return (
      <div className="choice-list">
        {options.map((option) => (
          <label className={`choice ${value === option.id ? "selected" : ""}`} key={option.id}>
            <input
              type="radio"
              name={question.id}
              checked={value === option.id}
              disabled={disabled}
              onChange={() => onChange(option.id)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    );
  }

  if (question.type === "multiple_choice") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="choice-list">
        {options.map((option) => (
          <label className={`choice ${selected.includes(option.id) ? "selected" : ""}`} key={option.id}>
            <input
              type="checkbox"
              checked={selected.includes(option.id)}
              disabled={disabled}
              onChange={() =>
                onChange(
                  selected.includes(option.id)
                    ? selected.filter((id) => id !== option.id)
                    : [...selected, option.id],
                )
              }
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    );
  }

  if (question.type === "ordering") {
    const optionMap = new Map(options.map((option) => [option.id, option]));
    const orderedIds =
      Array.isArray(value) && value.every((item) => typeof item === "string")
        ? (value as string[])
        : options.map((option) => option.id);
    return (
      <ol className="ordering-list">
        {orderedIds.map((optionId, index) => {
          const option = optionMap.get(optionId);
          if (!option) return null;
          return (
            <li key={option.id}>
              <span>{option.label}</span>
              <span className="order-controls">
                <button
                  type="button"
                  aria-label={`Move ${option.label} up`}
                  disabled={disabled || index === 0}
                  onClick={() => onChange(move(orderedIds, index, index - 1))}
                >
                  ↑
                </button>
                <button
                  type="button"
                  aria-label={`Move ${option.label} down`}
                  disabled={disabled || index === orderedIds.length - 1}
                  onClick={() => onChange(move(orderedIds, index, index + 1))}
                >
                  ↓
                </button>
              </span>
            </li>
          );
        })}
      </ol>
    );
  }

  if (question.type === "fill_paragraph") {
    return <FillParagraphInput question={question} value={value} disabled={disabled} onChange={onChange} />;
  }

  return (
    <div>
      <textarea
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        placeholder="Explain it in your own words. The judge rewards reasoning, not matching phrases."
        rows={6}
        maxLength={6000}
        onChange={(event) => onChange(event.target.value)}
      />
      <p className="field-hint">Your draft is saved locally. Codex judges only when you submit.</p>
    </div>
  );
}

function Brand({ onHome }: { onHome: () => void }) {
  return (
    <button className="brand brand-button" type="button" onClick={onHome} aria-label="Socraites lesson library">
      <span className="brand-mark">S</span>
      <span>Socr<span className="brand-ai">ai</span>tes</span>
    </button>
  );
}

function ThemeToggle({ theme, onToggle }: { theme: "light" | "dark"; onToggle: () => void }) {
  return (
    <button
      className="theme-toggle"
      type="button"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      onClick={onToggle}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}

function TutorPanel({
  view,
  lessonTitle,
  loading,
  sending,
  enabled,
  pendingMessage,
  error,
  onSend,
  onNewChat,
  onActivate,
  onClose,
}: {
  view: TutorView | null;
  lessonTitle: string;
  loading: boolean;
  sending: boolean;
  enabled: boolean;
  pendingMessage: string | null;
  error: string | null;
  onSend: (message: string) => Promise<boolean>;
  onNewChat: () => Promise<void>;
  onActivate: (conversationId: string) => Promise<void>;
  onClose: () => void;
}) {
  const [message, setMessage] = useState("");
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const turns = view?.conversation?.turns ?? [];

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [turns.length, pendingMessage]);

  async function submit() {
    const next = message.trim();
    if (!next || sending || !enabled) return;
    setMessage("");
    const sent = await onSend(next);
    if (!sent) setMessage(next);
  }

  return (
    <aside className="tutor-panel" aria-label="ACP lesson tutor">
      <header className="panel-header">
        <div><span className="panel-kicker">Assistant</span><strong>Socraites Tutor</strong></div>
        <button type="button" className="panel-close" aria-label="Close lesson tutor" onClick={onClose}>×</button>
      </header>
      <div className="tutor-toolbar">
        <div><strong>{enabled ? "Codex ACP" : "Tutor unavailable"}</strong><span>{lessonTitle}</span></div>
        <button type="button" disabled={sending} onClick={onNewChat}>New chat</button>
      </div>
      {view && view.conversations.length > 1 && (
        <details className="tutor-history">
          <summary>Past conversations <span>{view.conversations.length}</span></summary>
          <nav aria-label="Past tutor conversations">
            {view.conversations.map((conversation) => (
              <button
                type="button"
                className={conversation.conversation_id === view.active_conversation_id ? "active" : ""}
                disabled={sending}
                key={conversation.conversation_id}
                onClick={() => onActivate(conversation.conversation_id)}
              >
                <span>{conversation.title}</span><small>{conversation.turn_count} {conversation.turn_count === 1 ? "turn" : "turns"}</small>
              </button>
            ))}
          </nav>
        </details>
      )}
      <div className="tutor-transcript" ref={transcriptRef} aria-live="polite">
        {loading ? (
          <div className="tutor-empty"><p>Loading your conversation…</p></div>
        ) : turns.length === 0 && !pendingMessage ? (
          <div className="tutor-empty"><span aria-hidden="true">✦</span><strong>Reason it through together</strong><p>I’ll ask focused questions, offer small hints, or edit this lesson when you explicitly ask.</p></div>
        ) : (
          <>
            {turns.map((turn) => (
              <article className="tutor-turn" key={turn.turn_id}>
                <section className="tutor-message learner-message"><span>You</span><p>{turn.user_text}</p></section>
                <section className="tutor-message agent-message"><span>Tutor</span>
                  {turn.assistant_text && <p>{turn.assistant_text}</p>}
                  {turn.status === "generating" && <p className="thinking">Thinking…</p>}
                  {turn.error && <p className="tutor-turn-error">{turn.error}</p>}
                </section>
              </article>
            ))}
            {pendingMessage && (
              <article className="tutor-turn pending">
                <section className="tutor-message learner-message"><span>You</span><p>{pendingMessage}</p></section>
                <section className="tutor-message agent-message"><span>Tutor</span><p className="thinking">Thinking through the chapter…</p></section>
              </article>
            )}
          </>
        )}
      </div>
      {error && <div className="tutor-error" role="alert">{error}</div>}
      <div className="tutor-composer">
        <div className="context-chip">Context · {lessonTitle}</div>
        <textarea
          aria-label="Message the lesson tutor"
          disabled={!enabled || sending}
          maxLength={6000}
          placeholder={enabled ? "Ask a question or request a lesson edit…" : "Codex ACP is required for the tutor."}
          rows={4}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <div className="tutor-composer-actions"><small>⌘ Enter to send</small><button type="button" disabled={!enabled || sending || !message.trim()} onClick={submit}>{sending ? "Thinking…" : "Send"}</button></div>
      </div>
    </aside>
  );
}

function Dashboard({
  courses,
  theme,
  onOpen,
  onThemeToggle,
}: {
  courses: CourseSummary[];
  theme: "light" | "dark";
  onOpen: (courseId: string) => void;
  onThemeToggle: () => void;
}) {
  return (
    <div className="dashboard-shell">
      <header className="dashboard-topbar">
        <Brand onHome={() => window.scrollTo({ top: 0, behavior: "smooth" })} />
        <div className="dashboard-tools">
          <ThemeToggle theme={theme} onToggle={onThemeToggle} />
        </div>
      </header>
      <main className="dashboard-main">
        <div className="dashboard-heading">
          <p className="kicker">Lesson library</p>
          <h1>Learn one idea at a time.</h1>
          <p>Short, structured lessons with saved drafts, retrieval practice, and feedback that waits for you.</p>
        </div>
        <div className="library-summary">
          <span>{courses.length} {courses.length === 1 ? "lesson" : "lessons"} ready</span>
          <span>Everything stored as local files</span>
        </div>
        <section className="course-grid" aria-label="Available lessons">
          {courses.length === 0 && (
            <div className="empty-library">
              <span aria-hidden="true">＋</span>
              <div>
                <h2>Create your first course</h2>
                <p>Ask your coding agent to read <code>skills/create-socraites-course/SKILL.md</code> and add a course under <code>data/courses/</code>.</p>
              </div>
            </div>
          )}
          {courses.map((course, index) => {
            const percent = Math.round(course.progress * 100);
            return (
              <article className="course-card" key={course.id}>
                <div className="course-card-top">
                  <span className="course-index">{String(index + 1).padStart(2, "0")}</span>
                  <span className="course-status">{percent ? `${percent}% complete` : "Ready to begin"}</span>
                </div>
                <p className="kicker">{course.category}</p>
                <h2>{course.title}</h2>
                <p>{course.description}</p>
                <div className="course-meta">
                  <span>{course.section_count} sections</span>
                  <span>{course.estimated_minutes} minutes</span>
                </div>
                <div className="course-card-progress" aria-label={`${percent}% complete`}>
                  <i style={{ width: `${percent}%` }} />
                </div>
                <button className="primary-button course-open" type="button" onClick={() => onOpen(course.id)}>
                  {percent ? "Continue lesson" : "Open lesson"} <span aria-hidden="true">→</span>
                </button>
              </article>
            );
          })}
        </section>
      </main>
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = window.localStorage.getItem("socraites-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const [routeCourseId, setRouteCourseId] = useState<string | null>(courseIdFromHash);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [courseView, setCourseView] = useState<CourseView | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceView | null>(null);
  const [lessonId, setLessonId] = useState("");
  const [phase, setPhaseState] = useState<LearningPhase>("lesson");
  const [quiz, setQuiz] = useState<PublicQuiz | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [previousAttempt, setPreviousAttempt] = useState<AttemptResult | null>(null);
  const [judge, setJudge] = useState<JudgeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [courseLoading, setCourseLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [generatingQuestions, setGeneratingQuestions] = useState(false);
  const [generationNotice, setGenerationNotice] = useState<string | null>(null);
  const [draftRevision, setDraftRevision] = useState(0);
  const [draftState, setDraftState] = useState<"saved" | "saving" | "unsaved">("saved");
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(() => window.localStorage.getItem("socraites-left-panel") === "collapsed");
  const [rightCollapsed, setRightCollapsed] = useState(() => {
    const saved = window.localStorage.getItem("socraites-right-panel");
    if (saved === "open" || saved === "collapsed") return saved === "collapsed";
    return window.innerWidth <= 1100;
  });
  const [tutorView, setTutorView] = useState<TutorView | null>(null);
  const [tutorLoading, setTutorLoading] = useState(false);
  const [tutorSending, setTutorSending] = useState(false);
  const [pendingTutorMessage, setPendingTutorMessage] = useState<string | null>(null);
  const [tutorError, setTutorError] = useState<string | null>(null);
  const [lessonContentRevision, setLessonContentRevision] = useState(0);

  async function refreshLibrary() {
    const next = await api.courses();
    setCourses(next);
  }

  async function refreshCourse(courseId: string) {
    const [nextCourse, nextWorkspace] = await Promise.all([api.course(courseId), api.workspace(courseId)]);
    setCourseView(nextCourse);
    setWorkspace(nextWorkspace);
    setLessonId(nextWorkspace.active_lesson_id);
    setPhaseState(nextWorkspace.active_phase);
  }

  useEffect(() => {
    const onHashChange = () => setRouteCourseId(courseIdFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => {
      window.removeEventListener("hashchange", onHashChange);
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("socraites-theme", theme);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem("socraites-left-panel", leftCollapsed ? "collapsed" : "open");
  }, [leftCollapsed]);

  useEffect(() => {
    window.localStorage.setItem("socraites-right-panel", rightCollapsed ? "collapsed" : "open");
  }, [rightCollapsed]);

  useEffect(() => {
    Promise.all([refreshLibrary(), api.judgeStatus().then(setJudge)])
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load Socraites."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!routeCourseId) {
      setCourseView(null);
      setWorkspace(null);
      return;
    }
    setCourseLoading(true);
    setError(null);
    refreshCourse(routeCourseId)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load this lesson."))
      .finally(() => setCourseLoading(false));
  }, [routeCourseId]);

  useEffect(() => {
    if (!routeCourseId || !lessonId) return;
    setQuiz(null);
    setPreviousAttempt(null);
    setGenerationNotice(null);
    setDraftRevision(0);
    setDraftState("saved");
    setError(null);
    Promise.all([api.quiz(routeCourseId, lessonId), api.workspace(routeCourseId)])
      .then(([nextQuiz, nextWorkspace]) => {
        const work = nextWorkspace.lessons[lessonId];
        const cachedAnswers = readDraftCache(routeCourseId, lessonId);
        setQuiz(nextQuiz);
        setWorkspace(nextWorkspace);
        setAnswers(cachedAnswers ?? work?.answers ?? initialAnswers(nextQuiz));
        setResult(cachedAnswers ? null : work?.status === "graded" ? work.latest_attempt : null);
        setPreviousAttempt(
          cachedAnswers || work?.status === "editing" ? work?.latest_attempt ?? null : null,
        );
        setSubmitting(work?.status === "grading");
        setDraftRevision(cachedAnswers ? 1 : 0);
        if (work?.error) setError(work.error);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load this section."));
  }, [routeCourseId, lessonId]);

  useEffect(() => {
    if (!routeCourseId || !lessonId) return;
    setTutorLoading(true);
    setTutorError(null);
    setPendingTutorMessage(null);
    api.tutor(routeCourseId, lessonId)
      .then(setTutorView)
      .catch((reason: unknown) => setTutorError(reason instanceof Error ? reason.message : "The tutor conversation could not be loaded."))
      .finally(() => setTutorLoading(false));
  }, [routeCourseId, lessonId]);

  useEffect(() => {
    if (!routeCourseId || !lessonId || !quiz || draftRevision === 0 || submitting || result) return;
    setDraftState("unsaved");
    const timer = window.setTimeout(() => {
      setDraftState("saving");
      const savedSnapshot = JSON.stringify(answers);
      api.saveDraft(routeCourseId, lessonId, answers)
        .then((nextWorkspace) => {
          setWorkspace(nextWorkspace);
          const cached = readDraftCache(routeCourseId, lessonId);
          if (!cached || JSON.stringify(cached) === savedSnapshot) {
            window.localStorage.removeItem(draftCacheKey(routeCourseId, lessonId));
            setDraftState("saved");
          }
        })
        .catch((reason: unknown) => {
          setDraftState("unsaved");
          setError(reason instanceof Error ? reason.message : "Your draft could not be saved.");
        });
    }, 600);
    return () => window.clearTimeout(timer);
  }, [answers, draftRevision, lessonId, quiz, result, routeCourseId, submitting]);

  useEffect(() => {
    if (!routeCourseId || !lessonId || !submitting) return;
    const timer = window.setInterval(() => {
      api.workspace(routeCourseId)
        .then((nextWorkspace) => {
          const work = nextWorkspace.lessons[lessonId];
          setWorkspace(nextWorkspace);
          if (work?.status === "graded" && work.latest_attempt) {
            setResult(work.latest_attempt);
            setPreviousAttempt(null);
            setSubmitting(false);
            setDraftState("saved");
          } else if (work?.status === "editing") {
            setSubmitting(false);
            if (work.error) setError(work.error);
          }
        })
        .catch(() => undefined);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [lessonId, routeCourseId, submitting]);

  const currentLesson = useMemo(
    () => courseView?.course.lessons.find((lesson) => lesson.id === lessonId) ?? null,
    [courseView, lessonId],
  );
  const completedCount = courseView
    ? Object.values(courseView.progress.lessons).filter((item) => item.passed).length
    : 0;
  const totalSections = courseView?.course.lessons.length ?? 0;
  const progressPercent = totalSections ? (completedCount / totalSections) * 100 : 0;
  const feedbackAttempt = result ?? previousAttempt;
  const nextSectionId = courseView ? nextLessonId(courseView.course.lessons, lessonId) : null;

  function openCourse(courseId: string) {
    window.location.hash = `#/lesson/${courseId}`;
  }

  function goHome() {
    window.location.hash = "#/";
  }

  async function navigate(nextLessonId: string, nextPhase: LearningPhase) {
    if (!routeCourseId) return;
    setLessonId(nextLessonId);
    setPhaseState(nextPhase);
    setSidebarOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      setWorkspace(await api.navigate(routeCourseId, nextLessonId, nextPhase));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Your location could not be saved.");
    }
  }

  function updateAnswer(questionId: string, value: unknown) {
    setResult(null);
    setAnswers((current) => {
      const next = { ...current, [questionId]: value };
      if (routeCourseId && lessonId) writeDraftCache(routeCourseId, lessonId, next);
      return next;
    });
    setDraftRevision((current) => current + 1);
  }

  async function submitQuiz() {
    if (!quiz || !lessonId || !routeCourseId) return;
    setSubmitting(true);
    setDraftState("saving");
    setError(null);
    try {
      await api.saveDraft(routeCourseId, lessonId, answers);
      window.localStorage.removeItem(draftCacheKey(routeCourseId, lessonId));
      setDraftState("saved");
      const attempt = await api.submit(routeCourseId, lessonId, answers);
      setResult(attempt);
      setPreviousAttempt(null);
      setWorkspace(await api.workspace(routeCourseId));
      const refreshed = await api.course(routeCourseId);
      setCourseView(refreshed);
      await refreshLibrary();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The attempt could not be graded.");
    } finally {
      setSubmitting(false);
    }
  }

  async function tryAgain() {
    if (!quiz || !routeCourseId || !lessonId) return;
    const nextAnswers = answersForRetry(quiz, answers, result);
    setPreviousAttempt(result);
    setResult(null);
    setAnswers(nextAnswers);
    writeDraftCache(routeCourseId, lessonId, nextAnswers);
    setDraftRevision((current) => current + 1);
    setDraftState("saving");
    try {
      setWorkspace(await api.saveDraft(routeCourseId, lessonId, nextAnswers));
      window.localStorage.removeItem(draftCacheKey(routeCourseId, lessonId));
      setDraftState("saved");
    } catch (reason) {
      setDraftState("unsaved");
      setError(reason instanceof Error ? reason.message : "The new draft could not be saved.");
    }
  }

  async function generateMoreQuestions() {
    if (!quiz || !routeCourseId || !lessonId || generatingQuestions || submitting) return;
    setGeneratingQuestions(true);
    setGenerationNotice(null);
    setError(null);
    try {
      const nextQuiz = await api.generateQuestions(routeCourseId, lessonId);
      const addedCount = nextQuiz.questions.length - quiz.questions.length;
      const nextAnswers = {
        ...initialAnswers(nextQuiz),
        ...answersForRetry(quiz, answers, result),
      };
      if (result) {
        setPreviousAttempt(result);
        setResult(null);
      }
      setQuiz(nextQuiz);
      setAnswers(nextAnswers);
      writeDraftCache(routeCourseId, lessonId, nextAnswers);
      setDraftRevision((current) => current + 1);
      setGenerationNotice(
        `Added ${addedCount} new ${addedCount === 1 ? "question" : "questions"}. This quiz now has ${nextQuiz.questions.length}.`,
      );
      setDraftState("saving");
      try {
        setWorkspace(await api.saveDraft(routeCourseId, lessonId, nextAnswers));
        window.localStorage.removeItem(draftCacheKey(routeCourseId, lessonId));
        setDraftState("saved");
      } catch (reason) {
        setDraftState("unsaved");
        setError(reason instanceof Error ? `Questions were added, but ${reason.message}` : "Questions were added, but the draft could not be saved.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "New questions could not be generated.");
    } finally {
      setGeneratingQuestions(false);
    }
  }

  async function sendTutorMessage(message: string): Promise<boolean> {
    if (!routeCourseId || !lessonId || tutorSending) return false;
    setTutorSending(true);
    setPendingTutorMessage(message);
    setTutorError(null);
    try {
      setTutorView(await api.sendTutorMessage(routeCourseId, lessonId, message));
      const [nextCourse, nextQuiz] = await Promise.all([
        api.course(routeCourseId),
        api.quiz(routeCourseId, lessonId),
      ]);
      setCourseView(nextCourse);
      setQuiz(nextQuiz);
      setLessonContentRevision((current) => current + 1);
      return true;
    } catch (reason) {
      setTutorError(reason instanceof Error ? reason.message : "The tutor could not answer.");
      try {
        setTutorView(await api.tutor(routeCourseId, lessonId));
      } catch {
        // Keep the last visible transcript if recovery also fails.
      }
      return false;
    } finally {
      setPendingTutorMessage(null);
      setTutorSending(false);
    }
  }

  async function newTutorConversation() {
    if (!routeCourseId || !lessonId || tutorSending) return;
    setTutorError(null);
    try {
      setTutorView(await api.newTutorConversation(routeCourseId, lessonId));
    } catch (reason) {
      setTutorError(reason instanceof Error ? reason.message : "A new tutor conversation could not be started.");
    }
  }

  async function activateTutorConversation(conversationId: string) {
    if (!routeCourseId || !lessonId || tutorSending) return;
    setTutorError(null);
    try {
      setTutorView(await api.activateTutorConversation(routeCourseId, lessonId, conversationId));
    } catch (reason) {
      setTutorError(reason instanceof Error ? reason.message : "That tutor conversation could not be opened.");
    }
  }

  if (loading) return <main className="loading-screen">Preparing your lesson library…</main>;

  if (!routeCourseId) {
    return (
      <Dashboard
        courses={courses}
        theme={theme}
        onOpen={openCourse}
        onThemeToggle={() => setTheme(theme === "dark" ? "light" : "dark")}
      />
    );
  }

  if (courseLoading || !courseView || !workspace || !currentLesson) {
    return <main className="loading-screen">{error ?? "Opening your lesson…"}</main>;
  }

  return (
    <div className={`app-shell ${leftCollapsed ? "left-collapsed" : ""} ${rightCollapsed ? "right-collapsed" : ""}`}>
      <button className="mobile-menu" type="button" onClick={() => { setLeftCollapsed(false); setSidebarOpen(!sidebarOpen); }}>
        Sections
      </button>

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-brand-row">
          <Brand onHome={goHome} />
          <button className="panel-close" type="button" aria-label="Collapse course navigation" onClick={() => { setLeftCollapsed(true); setSidebarOpen(false); }}>×</button>
        </div>
        <div className="sidebar-body">
        <div className="course-intro">
          <button className="back-library" type="button" onClick={goHome}>← Lesson library</button>
          <p className="kicker">Current lesson</p>
          <h1>{courseView.course.title}</h1>
          <p>{courseView.course.subtitle}</p>
        </div>

        <section className="sidebar-progress" aria-label={`${completedCount} of ${totalSections} sections passed`}>
          <div><strong>Course progress</strong><span>{completedCount}/{totalSections} passed</span></div>
          <div className="progress-track"><i style={{ width: `${progressPercent}%` }} /></div>
        </section>

        <p className="sidebar-nav-label">All sections</p>
        <nav aria-label="Lesson sections">
          {courseView.course.lessons.map((lesson, index) => {
            const progress = courseView.progress.lessons[lesson.id];
            if (lesson.id === lessonId) {
              return (
                <section className="section-focus" aria-label={`Section ${index + 1}: ${lesson.title}`} key={lesson.id}>
                  <p className="kicker">Section {index + 1} of {totalSections}</p>
                  <h2>{lesson.title}</h2>
                  <p>{lesson.summary}</p>
                  <div className="section-focus-meta">
                    <span>◷ {lesson.estimated_minutes} min</span>
                    <span className={progress?.passed ? "passed" : ""}>{progress?.passed ? "✓ Passed" : "In progress"}</span>
                  </div>
                  <div className="phase-switcher" aria-label="Lesson or quiz">
                    <button className={phase === "lesson" ? "active" : ""} type="button" onClick={() => navigate(lesson.id, "lesson")}>
                      <svg className="material-icon" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 21q-1.625-1.475-3.7-2.237Q6.225 18 4 18q-.525 0-.888-.363-.362-.362-.362-.887V5.1q0-.4.25-.725t.65-.4q2.175-.425 4.263.213Q9.75 4.825 12 6.5q2.25-1.675 4.338-2.312Q18.425 3.55 20.6 3.975q.4.075.65.4t.25.725v11.65q0 .525-.363.888Q20.775 18 20.25 18q-2.225 0-4.3.763Q13.875 19.525 12 21Zm1-3q1.525-.95 3.138-1.425Q17.75 16.1 19.5 16.05V5.825q-1.6-.2-3.3.413Q14.5 6.85 13 8v10Zm-2 0V8Q9.5 6.85 7.8 6.238 6.1 5.625 4.5 5.825V16.05q1.75.05 3.363.525Q9.475 17.05 11 18Z" />
                      </svg>
                      <strong>Lesson</strong>
                    </button>
                    <button className={phase === "quiz" ? "active" : ""} type="button" onClick={() => navigate(lesson.id, "quiz")}>
                      <svg className="material-icon" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M20 3H4q-.825 0-1.412.587Q2 4.175 2 5v14q0 .825.588 1.413Q3.175 21 4 21h16q.825 0 1.413-.587Q22 19.825 22 19V5q0-.825-.587-1.413Q20.825 3 20 3ZM10 17H5v-2h5v2Zm0-4H5v-2h5v2Zm0-4H5V7h5v2Zm4.82 8L12 14.16l1.41-1.41 1.41 1.42 3.54-3.54 1.41 1.41L14.82 17Z" />
                      </svg>
                      <strong>Quiz</strong>
                    </button>
                  </div>
                  {progress?.passed && nextSectionId && (
                    <button className="primary-button section-primary-action" type="button" onClick={() => navigate(nextSectionId, "lesson")}>Next section →</button>
                  )}
                </section>
              );
            }
            return (
              <button
                type="button"
                key={lesson.id}
                className="lesson-link"
                onClick={() => navigate(lesson.id, "lesson")}
              >
                <span className="lesson-number">{progress?.passed ? "✓" : String(index + 1).padStart(2, "0")}</span>
                <span><strong>{lesson.title}</strong><small>{lesson.estimated_minutes} min</small></span>
              </button>
            );
          })}
        </nav>
        </div>
        <footer className="sidebar-footer">
          <div><span>Drafts saved</span><span>·</span><span>Files stay local</span></div>
          <ThemeToggle theme={theme} onToggle={() => setTheme(theme === "dark" ? "light" : "dark")} />
        </footer>
      </aside>

      {leftCollapsed && (
        <button type="button" className="sidebar-launcher" aria-label="Open course navigation" onClick={() => setLeftCollapsed(false)}>Sections →</button>
      )}

      <TutorPanel
        view={tutorView}
        lessonTitle={currentLesson.title}
        loading={tutorLoading}
        sending={tutorSending}
        enabled={judge?.active_mode === "codex-acp"}
        pendingMessage={pendingTutorMessage}
        error={tutorError}
        onSend={sendTutorMessage}
        onNewChat={newTutorConversation}
        onActivate={activateTutorConversation}
        onClose={() => setRightCollapsed(true)}
      />

      {rightCollapsed && (
        <button type="button" className="tutor-launcher" aria-label="Open lesson tutor" title="Open lesson tutor" onClick={() => setRightCollapsed(false)}><span aria-hidden="true">✦</span></button>
      )}

      <main className={`workspace ${phase === "lesson" ? "lesson-mode" : ""}`} id="top">
        {phase === "lesson" ? (
          <section className="lesson-surface">
            <button
              className="lesson-quiz-fab"
              type="button"
              onClick={() => navigate(lessonId, "quiz")}
            >
              Take the quiz <span aria-hidden="true">→</span>
            </button>
            <iframe
              className="lesson-frame"
              key={`${lessonId}-${theme}-${lessonContentRevision}`}
              sandbox="allow-scripts allow-same-origin allow-presentation"
              allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
              scrolling="auto"
              title={`${currentLesson.title} lesson`}
              src={`/render/courses/${routeCourseId}/lessons/${lessonId}?theme=${theme}`}
            />
          </section>
        ) : (
          <section className="quiz-section quiz-only" aria-label={`${currentLesson.title} quiz`}>
            <button
              className="quiz-back-button"
              type="button"
              onClick={() => navigate(lessonId, "lesson")}
            >
              <span aria-hidden="true">←</span> Back to lesson
            </button>
            <div className="quiz-statusline">
              <p className="save-state" aria-live="polite">
                {generatingQuestions ? "Codex is writing three new questions…" : submitting ? "Grading in progress — you can refresh safely" : draftState === "saving" ? "Saving draft…" : draftState === "unsaved" ? "Draft has unsaved changes" : `${quiz?.questions.length ?? 0} questions · Draft saved locally`}
              </p>
              {result && <span className={`score-badge ${result.passed ? "passed" : "retry"}`}>{scoreLabel(result.score)}</span>}
            </div>

            {error && <div className="error-banner" role="alert">{error}</div>}
            {generationNotice && <div className="generation-banner" role="status">{generationNotice}</div>}

            {previousAttempt && !result && (
              <div className="previous-attempt-banner">
                <div>
                  <strong>Revising your previous attempt</strong>
                  <span>The verdicts and feedback below refer to the answers you last submitted.</span>
                </div>
                <b>{scoreLabel(previousAttempt.score)}</b>
              </div>
            )}

            <div className="question-stack">
              {quiz?.questions.map((question, index) => {
                const questionResult = feedbackAttempt?.results.find((item) => item.question_id === question.id);
                const isPreviousFeedback = Boolean(previousAttempt && !result);
                const answerChanged = isPreviousFeedback
                  && JSON.stringify(answers[question.id]) !== JSON.stringify(previousAttempt?.answers[question.id]);
                return (
                  <article className="question-card" key={question.id}>
                    <div className="question-meta"><span>Question {index + 1}</span><span>{question.points} points{quiz && index >= quiz.authored_question_count ? " · Generated practice" : ""}</span></div>
                    {question.type !== "fill_paragraph" && <h3>{question.prompt}</h3>}
                    <QuestionInput
                      question={question}
                      value={answers[question.id]}
                      disabled={submitting || generatingQuestions || Boolean(result)}
                      onChange={(value) => updateAnswer(question.id, value)}
                    />
                    {questionResult && (
                      <div className={`feedback ${questionResult.verdict} ${isPreviousFeedback ? "previous" : ""}`}>
                        <div className="feedback-title">
                          <strong>{questionResult.verdict === "correct" ? "Correct" : questionResult.verdict === "partial" ? "Partially correct" : "Incorrect"}</strong>
                          <span>{isPreviousFeedback ? "Previous answer · " : ""}{questionResult.judge}</span>
                        </div>
                        {answerChanged && <p className="feedback-context">You have changed this answer. This feedback still describes the previous submission.</p>}
                        <p>{questionResult.feedback}</p>
                        {questionResult.strengths.length > 0 && <p><b>What worked:</b> {questionResult.strengths.join(" ")}</p>}
                        {questionResult.improvements.length > 0 && <p><b>Improve:</b> {questionResult.improvements.join(" ")}</p>}
                        <details><summary>Show explanation</summary><p>{questionResult.explanation}</p></details>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>

            <div className="quiz-actions">
              <div>
                <strong>{generatingQuestions ? "Creating another practice set." : result ? result.passed ? "Section passed." : "Not quite yet." : submitting ? "The judge is thinking." : previousAttempt ? "Revise, then check again." : "Submit when your explanation is ready."}</strong>
                <span>{generatingQuestions ? "Three validated questions will be saved to this chapter." : result ? result.passed ? "Your answers and feedback are preserved." : "Review the feedback, then revise your answers." : submitting ? "This continues even if you refresh." : previousAttempt ? "Your previous verdicts remain visible while you edit." : "Every submitted answer and judge response is retained."}</span>
              </div>
              <div className="quiz-action-buttons">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={!quiz || submitting || generatingQuestions || judge?.active_mode !== "codex-acp"}
                  title={judge?.active_mode === "codex-acp" ? "Add three new questions to this chapter" : "The Codex judge is required to generate questions"}
                  onClick={generateMoreQuestions}
                >
                  {generatingQuestions ? "Generating…" : "Generate more questions"}
                </button>
                {result ? (
                  <>
                    <button type="button" className="secondary-button" disabled={generatingQuestions} onClick={tryAgain}>Try again</button>
                    {result.passed && nextSectionId && (
                      <button type="button" className="primary-button" disabled={generatingQuestions} onClick={() => navigate(nextSectionId, "lesson")}>Next section</button>
                    )}
                  </>
                ) : (
                  <button type="button" className="primary-button" disabled={!quiz || submitting || generatingQuestions} onClick={submitQuiz}>
                    {submitting ? "Asking the judge…" : "Check my answers"}
                  </button>
                )}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
