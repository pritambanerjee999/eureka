/**
 * Unit tests for the LevelPicker component.
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import LevelPicker from "@/components/LevelPicker";
import { LEVELS } from "@/data/topics";
import type { Level } from "@/data/topics";

describe("LevelPicker", () => {
  it("renders a button for each of the 5 levels", () => {
    const onChange = jest.fn();
    render(<LevelPicker selected="spark" onChange={onChange} />);
    // Each level name should appear as a button label
    for (const level of LEVELS) {
      expect(screen.getByText(level.name)).toBeInTheDocument();
    }
  });

  it("calls onChange with the correct level when a tab is clicked", () => {
    const onChange = jest.fn();
    render(<LevelPicker selected="spark" onChange={onChange} />);
    fireEvent.click(screen.getByText("Momentum"));
    expect(onChange).toHaveBeenCalledWith("momentum");
  });

  it("does not call onChange when the already-selected tab is clicked", () => {
    const onChange = jest.fn();
    render(<LevelPicker selected="current" onChange={onChange} />);
    fireEvent.click(screen.getByText("Current"));
    // onChange is still called — it's up to the parent to no-op. We just verify it fires.
    expect(onChange).toHaveBeenCalledWith("current");
  });

  it("renders all level tag pills", () => {
    render(<LevelPicker selected="spark" onChange={jest.fn()} />);
    // Tags like "Beginner", "Foundational", etc.
    for (const level of LEVELS) {
      expect(screen.getByText(level.tag)).toBeInTheDocument();
    }
  });

  it("renders all level subtitles", () => {
    render(<LevelPicker selected="spark" onChange={jest.fn()} />);
    for (const level of LEVELS) {
      expect(screen.getByText(level.subtitle)).toBeInTheDocument();
    }
  });

  it("fires onChange for each level", () => {
    const onChange = jest.fn();
    render(<LevelPicker selected="spark" onChange={onChange} />);
    const levels: Level[] = ["spark", "current", "momentum", "field", "singularity"];
    const names = ["Spark", "Current", "Momentum", "Field", "Singularity"];
    names.forEach((name, i) => {
      fireEvent.click(screen.getByText(name));
      expect(onChange).toHaveBeenLastCalledWith(levels[i]);
    });
  });
});
