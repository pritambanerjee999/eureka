/**
 * Jest configuration for the Eureka frontend (Next.js + TypeScript).
 *
 * Uses next/jest to handle Next.js-specific transforms (SWC, CSS, etc.).
 * External services (LiveKit, fetch) are mocked per-test via jest.fn() or
 * module mocks.
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

const nextJest = require("next/jest");

const createJestConfig = nextJest({ dir: "./" });

/** @type {import('jest').Config} */
const customConfig = {
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  testEnvironment: "jest-environment-jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  testMatch: [
    "**/__tests__/**/*.[jt]s?(x)",
    "**/?(*.)+(spec|test).[jt]s?(x)",
  ],
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}",
    "!src/**/*.d.ts",
    "!src/app/globals.css",
  ],
};

module.exports = createJestConfig(customConfig);
