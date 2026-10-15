/**
 * Tests for SessionControls (mute and pause).
 *
 * @author Pritam
 * @date 2026-10-14
 */

import { act, fireEvent, render, screen } from "@testing-library/react";
import SessionControls from "@/components/SessionControls";

const setMicrophoneEnabled = jest.fn().mockResolvedValue(undefined);
const setAttributes = jest.fn().mockResolvedValue(undefined);
let micEnabled = true;

jest.mock("@livekit/components-react", () => ({
  useLocalParticipant: () => ({
    localParticipant: { setMicrophoneEnabled, setAttributes },
    isMicrophoneEnabled: micEnabled,
  }),
}));

beforeEach(() => {
  jest.clearAllMocks();
  micEnabled = true;
});

describe("SessionControls", () => {
  it("mutes the microphone", async () => {
    render(<SessionControls paused={false} onPausedChange={jest.fn()} />);
    await act(async () => {
      fireEvent.click(screen.getByText("Mute"));
    });
    expect(setMicrophoneEnabled).toHaveBeenCalledWith(false);
  });

  it("unmutes when the mic is off", async () => {
    micEnabled = false;
    render(<SessionControls paused={false} onPausedChange={jest.fn()} />);
    await act(async () => {
      fireEvent.click(screen.getByText("Unmute"));
    });
    expect(setMicrophoneEnabled).toHaveBeenCalledWith(true);
  });

  it("pause mutes the mic and tells the agent", async () => {
    const onPausedChange = jest.fn();
    render(<SessionControls paused={false} onPausedChange={onPausedChange} />);
    await act(async () => {
      fireEvent.click(screen.getByText("Pause"));
    });
    expect(setMicrophoneEnabled).toHaveBeenCalledWith(false);
    expect(setAttributes).toHaveBeenCalledWith({ paused: "1" });
    expect(onPausedChange).toHaveBeenCalledWith(true);
  });

  it("resume clears the flag and unmutes; mute is disabled while paused", async () => {
    const onPausedChange = jest.fn();
    render(<SessionControls paused={true} onPausedChange={onPausedChange} />);
    expect(screen.getByText("Mute").closest("button")).toBeDisabled();
    await act(async () => {
      fireEvent.click(screen.getByText("Resume"));
    });
    expect(setAttributes).toHaveBeenCalledWith({ paused: "0" });
    expect(setMicrophoneEnabled).toHaveBeenCalledWith(true);
    expect(onPausedChange).toHaveBeenCalledWith(false);
  });

  it("leaves state unchanged if LiveKit fails", async () => {
    setAttributes.mockRejectedValueOnce(new Error("offline"));
    const onPausedChange = jest.fn();
    render(<SessionControls paused={false} onPausedChange={onPausedChange} />);
    await act(async () => {
      fireEvent.click(screen.getByText("Pause"));
    });
    expect(onPausedChange).not.toHaveBeenCalled();
  });
});
