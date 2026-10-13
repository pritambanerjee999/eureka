/**
 * Unit tests for the AuthForm component (login / register).
 *
 * Author: Pritam
 * Date: 2026-10-12
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AuthForm from "@/components/AuthForm";

const mockFetch = jest.fn();
global.fetch = mockFetch;

const respond = (ok: boolean, body: unknown, status = ok ? 200 : 400) =>
  Promise.resolve({ ok, status, json: () => Promise.resolve(body) } as Response);

function fillAndSubmit(username: string, password: string, submitLabel: RegExp) {
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: username } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: submitLabel }));
}

beforeEach(() => mockFetch.mockReset());

describe("AuthForm", () => {
  it("signs in and reports the token and username", async () => {
    mockFetch.mockReturnValue(respond(true, { access_token: "jwt", username: "alice" }));
    const onAuth = jest.fn();
    render(<AuthForm onAuthenticated={onAuth} />);

    fillAndSubmit("alice", "password123", /^sign in$/i);

    await waitFor(() => expect(onAuth).toHaveBeenCalledWith("jwt", "alice"));
    expect(String(mockFetch.mock.calls[0][0])).toMatch(/\/auth\/login$/);
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({ username: "alice", password: "password123" });
  });

  it("switches to register mode and calls /auth/register", async () => {
    mockFetch.mockReturnValue(respond(true, { access_token: "jwt", username: "bob" }, 201));
    const onAuth = jest.fn();
    render(<AuthForm onAuthenticated={onAuth} />);

    fireEvent.click(screen.getByRole("button", { name: /create an account/i }));
    expect(screen.getByText(/create your account/i)).toBeInTheDocument();
    fillAndSubmit("bob", "password123", /^create account$/i);

    await waitFor(() => expect(onAuth).toHaveBeenCalledWith("jwt", "bob"));
    expect(String(mockFetch.mock.calls[0][0])).toMatch(/\/auth\/register$/);
  });

  it("shows the server's string error detail", async () => {
    mockFetch.mockReturnValue(respond(false, { detail: "Invalid username or password" }, 401));
    const onAuth = jest.fn();
    render(<AuthForm onAuthenticated={onAuth} />);

    fillAndSubmit("alice", "wrong", /^sign in$/i);

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username or password");
    expect(onAuth).not.toHaveBeenCalled();
  });

  it("shows the first validation message from a 422 response", async () => {
    mockFetch.mockReturnValue(
      respond(false, { detail: [{ msg: "Value error, Usernames starting with 'user-' are reserved" }] }, 422),
    );
    render(<AuthForm onAuthenticated={jest.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /create an account/i }));

    fillAndSubmit("user-x", "password123", /^create account$/i);

    expect(await screen.findByRole("alert")).toHaveTextContent("Usernames starting with 'user-' are reserved");
  });

  it("shows a connection error when fetch rejects", async () => {
    mockFetch.mockRejectedValue(new Error("network"));
    render(<AuthForm onAuthenticated={jest.fn()} />);

    fillAndSubmit("alice", "password123", /^sign in$/i);

    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot reach the server/i);
  });
});
