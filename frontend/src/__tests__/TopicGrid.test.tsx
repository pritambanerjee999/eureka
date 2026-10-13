/**
 * Unit tests for the TopicGrid component.
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import TopicGrid from "@/components/TopicGrid";
import { BRANCHES } from "@/data/topics";

describe("TopicGrid", () => {
  it("renders a card for each branch", () => {
    render(<TopicGrid level="spark" onTopicClick={jest.fn()} />);
    for (const branch of BRANCHES) {
      expect(screen.getByText(branch.name)).toBeInTheDocument();
    }
  });

  it("renders topic pills for the selected level", () => {
    render(<TopicGrid level="spark" onTopicClick={jest.fn()} />);
    // All spark-level topics should be visible
    for (const branch of BRANCHES) {
      for (const topic of branch.topics["spark"]) {
        expect(screen.getByText(topic)).toBeInTheDocument();
      }
    }
  });

  it("calls onTopicClick with the correct topic string when a pill is clicked", () => {
    const onClick = jest.fn();
    render(<TopicGrid level="spark" onTopicClick={onClick} />);
    // Click the first topic pill of the first branch
    const firstTopic = BRANCHES[0].topics["spark"][0];
    fireEvent.click(screen.getByText(firstTopic));
    expect(onClick).toHaveBeenCalledWith(firstTopic);
  });

  it("shows correct topics when level changes to momentum", () => {
    render(<TopicGrid level="momentum" onTopicClick={jest.fn()} />);
    for (const branch of BRANCHES) {
      for (const topic of branch.topics["momentum"]) {
        expect(screen.getByText(topic)).toBeInTheDocument();
      }
    }
  });

  it("disables all pills when loading=true", () => {
    render(<TopicGrid level="spark" loading={true} onTopicClick={jest.fn()} />);
    const allButtons = screen.getAllByRole("button");
    for (const btn of allButtons) {
      expect(btn).toBeDisabled();
    }
  });

  it("does not call onTopicClick when loading=true and a pill is clicked", () => {
    const onClick = jest.fn();
    render(<TopicGrid level="spark" loading={true} onTopicClick={onClick} />);
    const firstTopic = BRANCHES[0].topics["spark"][0];
    fireEvent.click(screen.getByText(firstTopic));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("pills are enabled by default (loading defaults to false)", () => {
    render(<TopicGrid level="current" onTopicClick={jest.fn()} />);
    const buttons = screen.getAllByRole("button");
    // At least some buttons should be enabled
    const enabledButtons = buttons.filter((b) => !b.hasAttribute("disabled"));
    expect(enabledButtons.length).toBeGreaterThan(0);
  });

  it("renders branch icons", () => {
    render(<TopicGrid level="spark" onTopicClick={jest.fn()} />);
    // At least the first branch icon should be present
    expect(screen.getByText(BRANCHES[0].icon)).toBeInTheDocument();
  });
});
