/**
 * Unit tests for the Home page component (app/page.tsx).
 *
 * Covers the auth gate, the signed-in layout (history sidebar + topic picker),
 * past-session viewing, token requests, logout, and level derivation.
 *
 * External fetch calls are mocked with jest.fn().
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Mock all child components that use LiveKit or browser-only APIs
// ---------------------------------------------------------------------------
jest.mock("@/components/VoiceRoom", () => {
  const React = require("react");
  return function MockVoiceRoom({ onDisconnect }: { onDisconnect: () => void }) {
    return (
      <div data-testid="voice-room">
        <button onClick={onDisconnect}>Disconnect</button>
      </div>
    );
  };
});

jest.mock("@/components/AgentVisualizer", () => {
  const React = require("react");
  return function MockAgentVisualizer() {
    return <div data-testid="agent-visualizer" />;
  };
});

// ---------------------------------------------------------------------------
// Mock global fetch
// ---------------------------------------------------------------------------
const mockFetch = jest.fn();
global.fetch = mockFetch;

// ---------------------------------------------------------------------------
// localStorage stub
// ---------------------------------------------------------------------------
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeOkResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  } as Response);
}

function makeErrorResponse(status = 500) {
  return Promise.resolve({
    ok: false,
    status,
    json: () => Promise.resolve({ detail: "Server error" }),
  } as Response);
}

const TOKEN_KEY = "eureka_auth_token";

/** Default fetch router: signed in as alice with empty history. */
function routeFetch(overrides: Record<string, () => Promise<Response>> = {}) {
  mockFetch.mockImplementation((url: string) => {
    const u = String(url);
    for (const [frag, fn] of Object.entries(overrides)) {
      if (u.includes(frag)) return fn();
    }
    if (u.includes("/auth/me")) return makeOkResponse({ username: "alice" });
    if (u.includes("/history")) return makeOkResponse({ identity: "alice", messages: [] });
    if (u.includes("/notes")) return makeOkResponse({ notes: [] });
    return makeOkResponse({
      token: "test-token",
      room_name: "room-abc",
      identity: "alice",
      livekit_url: "wss://test.livekit.io",
    });
  });
}

async function renderHome() {
  const Home = (await import("@/app/page")).default;
  await act(async () => {
    render(<Home />);
  });
}

function authHeader(call: unknown[]): string | null {
  const init = call[1] as RequestInit | undefined;
  return new Headers(init?.headers).get("Authorization");
}

beforeEach(() => {
  localStorageMock.clear();
  localStorageMock.setItem(TOKEN_KEY, "stored-jwt");
  mockFetch.mockReset();
  routeFetch();
});

describe("Home page — auth gate", () => {
  it("shows the sign-in form when no token is stored", async () => {
    localStorageMock.clear();
    await renderHome();
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("clears an invalid stored token and shows the sign-in form", async () => {
    routeFetch({ "/auth/me": () => makeErrorResponse(401) });
    await renderHome();
    await waitFor(() => expect(screen.getByText(/welcome back/i)).toBeInTheDocument());
    expect(localStorageMock.getItem(TOKEN_KEY)).toBeNull();
  });

  it("enters the app after signing in", async () => {
    localStorageMock.clear();
    routeFetch({ "/auth/login": () => makeOkResponse({ access_token: "new-jwt", username: "alice" }) });
    await renderHome();

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "alice" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    });

    await waitFor(() => expect(screen.getByText(/Assess My Level/i)).toBeInTheDocument());
    expect(localStorageMock.getItem(TOKEN_KEY)).toBe("new-jwt");
  });

  it("logs out back to the sign-in form", async () => {
    await renderHome();
    await act(async () => {
      fireEvent.click(screen.getByText("Log out"));
    });
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
    expect(localStorageMock.getItem(TOKEN_KEY)).toBeNull();
  });
});

describe("Home page — signed-in view", () => {
  it("renders brand, username, assess button, levels and topics", async () => {
    await renderHome();
    expect(screen.getAllByText("Eureka").length).toBeGreaterThan(0);
    expect(screen.getByText("alice")).toBeInTheDocument();
    expect(screen.getByText(/Assess My Level/i)).toBeInTheDocument();
    expect(screen.getByText("Spark")).toBeInTheDocument();
    expect(screen.getByText("Classical Mechanics")).toBeInTheDocument();
  });

  it("fetches history for the signed-in user with the Bearer token", async () => {
    await renderHome();
    const historyCall = mockFetch.mock.calls.find((c) => String(c[0]).includes("/history/alice"));
    expect(historyCall).toBeTruthy();
    expect(authHeader(historyCall!)).toBe("Bearer stored-jwt");
  });

  it("logs out when history returns 401", async () => {
    routeFetch({ "/history": () => makeErrorResponse(401) });
    await renderHome();
    await waitFor(() => expect(screen.getByText(/welcome back/i)).toBeInTheDocument());
  });
});

describe("Home page — history sidebar", () => {
  const history = [
    { role: "session_start", content: JSON.stringify({ room: "room-1", topic: "Light" }), timestamp: new Date().toISOString() },
    { role: "assistant", content: "Light is a wave and a particle.", timestamp: new Date().toISOString() },
    { role: "user", content: "How can it be both?", timestamp: new Date().toISOString() },
  ];

  it("opens a past session's transcript and notes when clicked", async () => {
    routeFetch({
      "/history": () => makeOkResponse({ messages: history }),
      "/notes": () => makeOkResponse({ notes: [{ room_name: "room-1", content: "wave-particle duality", updated_at: "" }] }),
    });
    await renderHome();

    await act(async () => {
      fireEvent.click(await screen.findByText("Light"));
    });

    expect(screen.getByText("Light is a wave and a particle.")).toBeInTheDocument();
    expect(screen.getByText("How can it be both?")).toBeInTheDocument();
    expect(screen.getByText("wave-particle duality")).toBeInTheDocument();
  });

  it("continues a past topic via /token", async () => {
    routeFetch({ "/history": () => makeOkResponse({ messages: history }) });
    await renderHome();
    await act(async () => {
      fireEvent.click(await screen.findByText("Light"));
    });
    await act(async () => {
      fireEvent.click(screen.getByText("Continue this topic"));
    });

    await waitFor(() => expect(screen.getByTestId("voice-room")).toBeInTheDocument());
    const tokenCall = mockFetch.mock.calls.find((c) => String(c[0]).includes("/token"));
    expect(JSON.parse(tokenCall![1].body).topic).toBe("Light");
  });

  it("returns to the topic picker on New session", async () => {
    routeFetch({ "/history": () => makeOkResponse({ messages: history }) });
    await renderHome();
    await act(async () => {
      fireEvent.click(await screen.findByText("Light"));
    });
    fireEvent.click(screen.getByText("New session"));
    expect(screen.getByText("Classical Mechanics")).toBeInTheDocument();
  });
});

describe("Home page — token request", () => {
  it("enters VoiceRoom after a successful token fetch, authenticated and without a client identity", async () => {
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByText("Why do things fall?"));
    });

    await waitFor(() => expect(screen.getByTestId("voice-room")).toBeInTheDocument());
    const tokenCall = mockFetch.mock.calls.find((c) => String(c[0]).includes("/token"));
    expect(authHeader(tokenCall!)).toBe("Bearer stored-jwt");
    expect(JSON.parse(tokenCall![1].body)).toEqual({ topic: "Why do things fall?" });
  });

  it("shows an error message when the token request fails", async () => {
    routeFetch({ "/token": () => makeErrorResponse(503) });
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByText("Why do things fall?"));
    });

    await waitFor(() => expect(screen.getByText(/API error/i)).toBeInTheDocument());
  });

  it("shows a friendly message when rate-limited", async () => {
    routeFetch({ "/token": () => makeErrorResponse(429) });
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByText("Why do things fall?"));
    });

    await waitFor(() => expect(screen.getByText(/starting sessions too quickly/i)).toBeInTheDocument());
  });

  it("calls /token with __assess__ when Assess My Level is clicked", async () => {
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByText(/Assess My Level/i));
    });

    await waitFor(() => {
      const tokenCall = mockFetch.mock.calls.find((c) => String(c[0]).includes("/token"));
      expect(JSON.parse(tokenCall![1].body).topic).toBe("__assess__");
    });
  });
});

describe("Home page — disconnect", () => {
  it("returns to landing page after disconnect", async () => {
    await renderHome();

    await act(async () => {
      fireEvent.click(screen.getByText("Why do things fall?"));
    });
    await waitFor(() => expect(screen.getByTestId("voice-room")).toBeInTheDocument());

    await act(async () => {
      fireEvent.click(screen.getByText("Disconnect"));
    });

    await waitFor(() => {
      expect(screen.queryByTestId("voice-room")).not.toBeInTheDocument();
      expect(screen.getByText(/Assess My Level/i)).toBeInTheDocument();
    });
  });
});

describe("defaultLevelFromHistory logic", () => {
  it("derives 'momentum' level when history has more than 20 messages", async () => {
    const messages = Array.from({ length: 25 }, (_, i) => ({
      role: "user",
      content: `msg ${i}`,
      timestamp: "2026-10-12T10:00:00.000Z",
    }));
    routeFetch({ "/history": () => makeOkResponse({ messages }) });
    await renderHome();
    await waitFor(() => expect(screen.getByText("Momentum")).toBeInTheDocument());
  });

  it("uses the most recent 'level' record from history", async () => {
    const messages = [
      { role: "level", content: "spark", timestamp: "2026-10-12T09:00:00.000Z" },
      { role: "level", content: "field", timestamp: "2026-10-12T10:00:00.000Z" },
    ];
    routeFetch({ "/history": () => makeOkResponse({ messages }) });
    await renderHome();
    await waitFor(() => expect(screen.getByText("Field")).toBeInTheDocument());
  });
});
