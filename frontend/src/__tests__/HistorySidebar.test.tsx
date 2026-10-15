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

  it("hides on desktop when collapsed and wires the hide button", () => {
    const onCollapse = jest.fn();
    renderSidebar({ collapsed: true, onCollapse });
    expect(screen.getByLabelText("Session history").className).toContain("md:hidden");
    fireEvent.click(screen.getByLabelText("Hide history"));
    expect(onCollapse).toHaveBeenCalled();
  });

  it("disables New session while connecting", () => {
    renderSidebar({ loading: true });
    expect(screen.getByText("Connecting…").closest("button")).toBeDisabled();
  });

  it("renames a session inline with Enter", () => {
    const onRename = jest.fn();
    renderSidebar({ onRename });
    fireEvent.click(screen.getByLabelText("Rename Light"));
    const input = screen.getByLabelText("Session name");
    expect(input).toHaveValue("Light");
    fireEvent.change(input, { target: { value: "Photons and me" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRename).toHaveBeenCalledWith(expect.objectContaining({ key: "room-1" }), "Photons and me");
    expect(screen.queryByLabelText("Session name")).not.toBeInTheDocument();
  });

  it("cancels a rename with Escape and skips unchanged names", () => {
    const onRename = jest.fn();
    renderSidebar({ onRename });
    fireEvent.click(screen.getByLabelText("Rename Light"));
    fireEvent.keyDown(screen.getByLabelText("Session name"), { key: "Escape" });
    fireEvent.click(screen.getByLabelText("Rename Light"));
    fireEvent.keyDown(screen.getByLabelText("Session name"), { key: "Enter" });
    expect(onRename).not.toHaveBeenCalled();
  });

  it("hides the rename button without an onRename handler", () => {
    renderSidebar();
    expect(screen.queryByLabelText("Rename Light")).not.toBeInTheDocument();
  });
});
