/**
 * Unit tests for the StudyPlan component.
 *
 * Author: Pritam
 * Date: 2026-10-21
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import StudyPlan from "@/components/StudyPlan";

const TOPICS = [
  { topic: "Spinning Tops", reason: "Builds on Newton's laws" },
  { topic: "Rainbows Up Close", reason: "Follows Light" },
  { topic: "Heat Engines", reason: "" },
];

describe("StudyPlan", () => {
  it("renders the topics as a list with their reasons", () => {
    render(<StudyPlan topics={TOPICS} loading={false} onPick={jest.fn()} onClose={jest.fn()} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByText("Spinning Tops")).toBeInTheDocument();
    expect(screen.getByText("Builds on Newton's laws")).toBeInTheDocument();
  });

  it("calls onPick with the chosen topic", () => {
    const onPick = jest.fn();
    render(<StudyPlan topics={TOPICS} loading={false} onPick={onPick} onClose={jest.fn()} />);
    fireEvent.click(screen.getByText("Rainbows Up Close"));
    expect(onPick).toHaveBeenCalledWith("Rainbows Up Close");
  });

  it("disables the rows while a session is starting", () => {
    render(<StudyPlan topics={TOPICS} loading onPick={jest.fn()} onClose={jest.fn()} />);
    expect(screen.getByText("Heat Engines").closest("button")).toBeDisabled();
  });

  it("shows a loading message while fetching", () => {
    render(<StudyPlan topics={null} loading={false} onPick={jest.fn()} onClose={jest.fn()} />);
    expect(screen.getByText(/Planning your next topics/)).toBeInTheDocument();
  });

  it("shows an empty state for a learner with no lessons", () => {
    render(<StudyPlan topics={[]} loading={false} onPick={jest.fn()} onClose={jest.fn()} />);
    expect(screen.getByText(/Finish a lesson first/)).toBeInTheDocument();
  });

  it("closes", () => {
    const onClose = jest.fn();
    render(<StudyPlan topics={[]} loading={false} onPick={jest.fn()} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("Close study plan"));
    expect(onClose).toHaveBeenCalled();
  });
});
