/**
 * Session helpers: turn the flat conversation history into chat-style
 * sessions for the history sidebar and session detail view.
 *
 * @author Pritam
 * @date 2026-10-12
 */

/** A single message record from the persistent conversation history. */
export interface HistoryMessage {
  role: string;
  content: string;
  room_name?: string;
  timestamp: string;
}

/** A single notes record returned by GET /notes/{identity}. */
export interface NotesEntry {
  room_name: string;
  content: string;
  updated_at: string;
}

/** A past session derived from `session_start` records. */
export interface Session {
  /** Stable React key (room name, or a positional fallback). */
  key: string;
  roomName: string | null;
  /** Display title, e.g. "Light", "Open Session", "Level Assessment". */
  topic: string;
  /** Raw topic key as sent to /token, used to resume the topic. */
  rawTopic: string;
  startedAt: string;
  /** User and assistant turns in chronological order. */
  messages: HistoryMessage[];
  checkpoints: string[];
  level: string | null;
}

/** A labelled bucket of sessions for the sidebar, e.g. "Today". */
export interface SessionGroup {
  label: string;
  sessions: Session[];
}

/**
 * Parse a `session_start` content JSON string to extract the room and topic.
 *
 * @param content - Raw content of a `session_start` message.
 * @returns The room (or null), display topic, and raw topic key.
 */
export function parseSessionStart(content: string): {
  room: string | null;
  topic: string;
  rawTopic: string;
} {
  try {
    const obj = JSON.parse(content);
    const raw: string = obj.topic ?? "__open__";
    return {
      room: obj.room ?? null,
      topic:
        raw === "__assess__" ? "Level Assessment" : raw === "__open__" ? "Open Session" : raw,
      rawTopic: raw,
    };
  } catch {
    return { room: null, topic: "Session", rawTopic: "__open__" };
  }
}

/**
 * Parse a checkpoint content string of the form "[Understood] topic: insight".
 *
 * @param content - Raw checkpoint content.
 * @returns An object with `topic` and `insight` strings.
 */
export function parseCheckpoint(content: string): { topic: string; insight: string } {
  const stripped = content.replace(/^\[Understood\]\s*/i, "");
  const colonIdx = stripped.indexOf(":");
  if (colonIdx === -1) return { topic: stripped.trim(), insight: "" };
  return {
    topic: stripped.slice(0, colonIdx).trim(),
    insight: stripped.slice(colonIdx + 1).trim(),
  };
}

/**
 * Group a flat list of messages into sessions.
 *
 * Every `session_start` record begins a new session; messages before the
 * first `session_start` are ignored.
 *
 * @param messages - All history messages for the user, oldest first.
 * @returns Sessions, most recent first.
 */
export function buildSessions(messages: HistoryMessage[]): Session[] {
  const sessions: Session[] = [];
  let current: Session | null = null;

  for (const msg of messages) {
    if (msg.role === "session_start") {
      if (current) sessions.push(current);
      const { room, topic, rawTopic } = parseSessionStart(msg.content);
      current = {
        key: room ?? `session-${sessions.length}`,
        roomName: room,
        topic,
        rawTopic,
        startedAt: msg.timestamp,
        messages: [],
        checkpoints: [],
        level: null,
      };
    } else if (current) {
      if (msg.role === "user" || msg.role === "assistant") {
        current.messages.push(msg);
      } else if (msg.role === "checkpoint") {
        current.checkpoints.push(parseCheckpoint(msg.content).topic);
      } else if (msg.role === "level") {
        current.level = msg.content.trim();
      }
    }
  }
  if (current) sessions.push(current);

  return sessions.reverse();
}

/**
 * Bucket sessions by recency like a chat app sidebar.
 *
 * @param sessions - Sessions, most recent first.
 * @param now - Reference time (injectable for tests).
 * @returns Non-empty groups in order: Today, Yesterday, Previous 7 days, Older.
 */
export function groupSessionsByDate(sessions: Session[], now: Date = new Date()): SessionGroup[] {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = 24 * 60 * 60 * 1000;
  const buckets: SessionGroup[] = [
    { label: "Today", sessions: [] },
    { label: "Yesterday", sessions: [] },
    { label: "Previous 7 days", sessions: [] },
    { label: "Older", sessions: [] },
  ];
  for (const s of sessions) {
    const t = new Date(s.startedAt).getTime();
    if (t >= startOfToday) buckets[0].sessions.push(s);
    else if (t >= startOfToday - day) buckets[1].sessions.push(s);
    else if (t >= startOfToday - 7 * day) buckets[2].sessions.push(s);
    else buckets[3].sessions.push(s);
  }
  return buckets.filter((b) => b.sessions.length > 0);
}

/**
 * Human-readable level name from the level key.
 *
 * @param key - Level key such as "spark" or "momentum".
 * @returns Display name string.
 */
export function levelLabel(key: string): string {
  const map: Record<string, string> = {
    spark: "Spark",
    current: "Current",
    momentum: "Momentum",
    field: "Field",
    singularity: "Singularity",
  };
  return map[key] ?? key;
}

/**
 * Format an ISO timestamp as a short date, e.g. "Oct 12, 2026".
 *
 * @param iso - ISO 8601 timestamp.
 * @returns Formatted date string.
 */
export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format an ISO timestamp as a short time, e.g. "3:42 PM".
 *
 * @param iso - ISO 8601 timestamp.
 * @returns Formatted time string.
 */
export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}
