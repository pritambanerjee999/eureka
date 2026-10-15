/**
 * Unit tests for the HistorySidebar component.
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import HistorySidebar from "@/components/HistorySidebar";
import { buildSessions } from "@/lib/sessions";

const now = new Date().toISOString();
const sessions = buildSessions([
  { role: "session_start", content: JSON.stringify({ room: "room-1", topic: "Light" }), timestamp: now },
  { role: "user", content: "hi", timestamp: now },
  { role: "checkpoint", content: "[Understood] Photons: x", timestamp: now },
  { role: "session_start", content: JSON.stringify({ room: "room-2", topic: "__open__" }), timestamp: now },
]);

function renderSidebar(overrides: Partial<React.ComponentProps<typeof HistorySidebar>> = {}) {
  const props = {
    sessions,
    selectedKey: null,
    username: "alice",
    open: false,
    onSelect: jest.fn(),
    onNewSession: jest.fn(),
    onHome: jest.fn(),
    onLogout: jest.fn(),
    onClose: jest.fn(),
    ...overrides,
  };
  render(<HistorySidebar {...props} />);
  return props;
}

describe("HistorySidebar", () => {
  it("lists sessions under a date group", () => {
    renderSidebar();
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Light")).toBeInTheDocument();
    expect(screen.getByText("Open Session")).toBeInTheDocument();
    expect(screen.getByText(/1 msg$/)).toBeInTheDocument();
  });

  it("shows an empty state with no sessions", () => {
    renderSidebar({ sessions: [] });
    expect(screen.getByText(/past sessions will show up here/i)).toBeInTheDocument();
  });

  it("calls onSelect with the clicked session and marks the selected one", () => {
    const props = renderSidebar({ selectedKey: "room-1" });
    fireEvent.click(screen.getByText("Open Session"));
    expect(props.onSelect).toHaveBeenCalledWith(expect.objectContaining({ key: "room-2" }));
    expect(screen.getByText("Light").closest("button")).toHaveAttribute("aria-current", "true");
  });

  it("shows the username and wires New session / Log out", () => {
    const props = renderSidebar();
    expect(screen.getByText("alice")).toBeInTheDocument();
    fireEvent.click(screen.getByText("New session"));
    fireEvent.click(screen.getByText("Log out"));
    expect(props.onNewSession).toHaveBeenCalled();
    expect(props.onLogout).toHaveBeenCalled();
  });

  it("goes home when the brand is clicked", () => {
    const props = renderSidebar();
    fireEvent.click(screen.getByLabelText(/home/i));
    expect(props.onHome).toHaveBeenCalled();
  });

  it("disables New session while connecting", () => {
    renderSidebar({ loading: true });
    expect(screen.getByText("Connecting…").closest("button")).toBeDisabled();
  });
});
