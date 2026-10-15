/**
 * Unit tests for the topics data module.
 *
 * Validates the shape and content of LEVELS and BRANCHES exports.
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

import { LEVELS, BRANCHES } from "@/data/topics";
import type { Level } from "@/data/topics";

const LEVEL_IDS: Level[] = ["spark", "current", "momentum", "field", "singularity"];

describe("LEVELS", () => {
  it("exports exactly 5 levels", () => {
    expect(LEVELS).toHaveLength(5);
  });

  it("has all required level ids", () => {
    const ids = LEVELS.map((l) => l.id);
    expect(ids).toEqual(LEVEL_IDS);
  });

  it("every level has a non-empty name, subtitle, tag, and gradient", () => {
    for (const level of LEVELS) {
      expect(level.name.length).toBeGreaterThan(0);
      expect(level.subtitle.length).toBeGreaterThan(0);
      expect(level.tag.length).toBeGreaterThan(0);
      expect(level.gradient.length).toBeGreaterThan(0);
    }
  });

  it("every level has border and text class strings", () => {
    for (const level of LEVELS) {
      expect(level.border).toMatch(/^border-/);
      expect(level.text).toMatch(/^text-/);
    }
  });
});

describe("BRANCHES", () => {
  it("exports exactly 6 branches", () => {
    expect(BRANCHES).toHaveLength(6);
  });

  it("every branch has a non-empty id, name, and icon", () => {
    for (const branch of BRANCHES) {
      expect(branch.id.length).toBeGreaterThan(0);
      expect(branch.name.length).toBeGreaterThan(0);
      expect(branch.icon.length).toBeGreaterThan(0);
    }
  });

  it("every branch has topics for all 5 levels", () => {
    for (const branch of BRANCHES) {
      for (const levelId of LEVEL_IDS) {
        expect(Array.isArray(branch.topics[levelId])).toBe(true);
        expect(branch.topics[levelId].length).toBeGreaterThan(0);
      }
    }
  });

  it("all branch ids are unique", () => {
    const ids = BRANCHES.map((b) => b.id);
    const unique = new Set(ids);
    expect(unique.size).toBe(ids.length);
  });

  it("includes classical-mechanics and electromagnetism branches", () => {
    const ids = BRANCHES.map((b) => b.id);
    expect(ids).toContain("classical-mechanics");
    expect(ids).toContain("electromagnetism");
  });
});
