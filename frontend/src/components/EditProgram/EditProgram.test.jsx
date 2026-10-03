import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { buildApiUrl, fetchWithAuth } from "../../utils/api";
import {
  clearProgramDirty,
  markProgramDirty,
} from "../../utils/programRefresh";
import EditProgram from "./EditProgram";

jest.mock("../../utils/api", () => ({
  ...jest.requireActual("../../utils/api"),
  fetchWithAuth: jest.fn(),
}));

function protect(items) {
  return { ok: true, json: async () => items };
}

function mockInitialFetch(dayItems = []) {
  fetchWithAuth
    .mockResolvedValueOnce(protect([]))
    .mockResolvedValueOnce(protect([]));
  global.fetch.mockResolvedValueOnce(protect(dayItems));
}

describe("EditProgram data lifecycle", () => {
  let consoleError;

  beforeEach(() => {
    localStorage.clear();
    clearProgramDirty();
    fetchWithAuth.mockReset();
    global.fetch = jest.fn();
    consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleError.mockRestore();
  });

  test("issues the three initial requests and renders the schedule", async () => {
    mockInitialFetch([{ id: 1, date: "2026-09-10", timeline: [] }]);

    render(<EditProgram />);

    expect(await screen.findByText("Conference Schedule")).toBeInTheDocument();
    expect(buildApiUrl).toBeDefined();
    expect(fetchWithAuth).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test("focus refetches only while the dirty flag is set, and clears it", async () => {
    mockInitialFetch([]);
    render(<EditProgram />);
    expect(await screen.findByText("Conference Schedule")).toBeInTheDocument();
    expect(fetchWithAuth).toHaveBeenCalledTimes(2);

    mockInitialFetch([]);
    markProgramDirty();
    fireEvent(window, new Event("focus"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(4));
    expect(global.fetch).toHaveBeenCalledTimes(2);

    mockInitialFetch([]);
    fireEvent(window, new Event("focus"));

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(fetchWithAuth).toHaveBeenCalledTimes(4);
  });

  test("tolerates non-array program payloads without crashing", async () => {
    fetchWithAuth
      .mockResolvedValueOnce(protect([]))
      .mockResolvedValueOnce(protect([]));
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });

    render(<EditProgram />);

    expect(await screen.findByText("+ Add Day")).toBeInTheDocument();
  });
});
