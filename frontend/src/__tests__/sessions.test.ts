/**
 * Unit tests for the session-building helpers in lib/sessions.
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

import {
  buildSessions,
  groupSessionsByDate,
  levelLabel,
  parseCheckpoint,
  parseSessionStart,
  type HistoryMessage,
} from "@/lib/sessions";

const msg = (role: string, content: string, timestamp = "2026-10-12T10:00:00.000Z"): HistoryMessage => ({
  role,
  content,
  timestamp,
});
const start = (room: string, topic: string, ts?: string) =>
  msg("session_start", JSON.stringify({ room, topic }), ts);

describe("parseSessionStart", () => {
  it("maps special topic keys to display names and keeps the raw key", () => {
    expect(parseSessionStart(JSON.stringify({ room: "r", topic: "__assess__" }))).toEqual({
      room: "r",
      topic: "Level Assessment",
      rawTopic: "__assess__",
    });
    expect(parseSessionStart(JSON.stringify({ room: "r", topic: "__open__" })).topic).toBe("Open Session");
  });

  it("defaults a missing topic to an open session", () => {
    expect(parseSessionStart(JSON.stringify({ room: "r" }))).toMatchObject({
      topic: "Open Session",
      rawTopic: "__open__",
    });
  });

  it("falls back gracefully on invalid JSON", () => {
    expect(parseSessionStart("not json")).toEqual({ room: null, topic: "Session", rawTopic: "__open__" });
  });
});

describe("parseCheckpoint", () => {
  it("splits topic and insight", () => {
    expect(parseCheckpoint("[Understood] Inertia: things keep moving")).toEqual({
      topic: "Inertia",
      insight: "things keep moving",
    });
  });

  it("handles content with no colon", () => {
    expect(parseCheckpoint("[Understood] Gravity")).toEqual({ topic: "Gravity", insight: "" });
  });
});

describe("buildSessions", () => {
  it("returns an empty list for no messages", () => {
    expect(buildSessions([])).toEqual([]);
  });

  it("uses a custom title for a renamed session but keeps the raw topic for resuming", () => {
    const ts = new Date().toISOString();
    const [s] = buildSessions(
      [{ role: "session_start", content: JSON.stringify({ room: "room-1", topic: "Light" }), timestamp: ts }],
      { "room-1": "Light, take two" },
    );
    expect(s.topic).toBe("Light, take two");
    expect(s.rawTopic).toBe("Light");
  });

  it("ignores messages before the first session_start", () => {
    expect(buildSessions([msg("user", "orphan")])).toEqual([]);
  });

  it("groups transcript, checkpoints and level into sessions, most recent first", () => {
    const sessions = buildSessions([
      start("room-1", "Light"),
      msg("assistant", "Hi!"),
      msg("user", "What is light?"),
      msg("checkpoint", "[Understood] Photons: light is quantised"),
      start("room-2", "__assess__"),
      msg("level", " field "),
    ]);
    expect(sessions.map((s) => s.key)).toEqual(["room-2", "room-1"]);
    expect(sessions[0].level).toBe("field");
    expect(sessions[1].messages.map((m) => m.content)).toEqual(["Hi!", "What is light?"]);
    expect(sessions[1].checkpoints).toEqual(["Photons"]);
    expect(sessions[1].rawTopic).toBe("Light");
  });

  it("gives sessions without a room a unique fallback key", () => {
    const sessions = buildSessions([msg("session_start", "bad"), msg("session_start", "bad")]);
    expect(new Set(sessions.map((s) => s.key)).size).toBe(2);
  });
});

describe("groupSessionsByDate", () => {
  const now = new Date(2026, 9, 12, 15, 0, 0);
  const at = (d: Date) => buildSessions([start(`room-${d.getTime()}`, "T", d.toISOString())])[0];

  it("buckets into Today / Yesterday / Previous 7 days / Older and drops empty groups", () => {
    const groups = groupSessionsByDate(
      [
        at(new Date(2026, 9, 12, 9)),
        at(new Date(2026, 9, 11, 23)),
        at(new Date(2026, 9, 8, 12)),
        at(new Date(2026, 8, 1, 12)),
      ],
      now,
    );
    expect(groups.map((g) => g.label)).toEqual(["Today", "Yesterday", "Previous 7 days", "Older"]);
    expect(groupSessionsByDate([at(new Date(2026, 9, 12, 0, 0))], now).map((g) => g.label)).toEqual(["Today"]);
  });

  it("returns no groups for no sessions", () => {
    expect(groupSessionsByDate([], now)).toEqual([]);
  });
});

describe("levelLabel", () => {
  it("maps known keys and passes unknown ones through", () => {
    expect(levelLabel("singularity")).toBe("Singularity");
    expect(levelLabel("mystery")).toBe("mystery");
  });
});
