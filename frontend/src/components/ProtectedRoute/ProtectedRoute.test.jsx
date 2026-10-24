import { render, screen } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import ProtectedRoute from "./ProtectedRoute";

vi.mock("../../utils/api", () => ({
  fetchWithAuth: vi.fn(),
}));

vi.mock("../../utils/conferenceSlug", () => ({
  getConferenceSlug: () => "wsc2026-test",
}));

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
  });

  test("redirects to the public page when the session probe is unauthorized", async () => {
    fetchWithAuth.mockResolvedValue({ ok: false, status: 401 });

    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    const marker = await screen.findByTestId("navigate");
    expect(marker.dataset.to).toBe("/");
    expect(screen.queryByText("Admin content")).not.toBeInTheDocument();
    expect(fetchWithAuth).toHaveBeenCalledWith("/api/auth/user/");
  });

  test("renders children for a superuser", async () => {
    fetchWithAuth.mockResolvedValue(
      jsonOf({ is_superuser: true, managed_conferences: [] })
    );

    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    expect(await screen.findByText("Admin content")).toBeInTheDocument();
    expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
  });

  test("renders children for a manager of the current conference", async () => {
    fetchWithAuth.mockResolvedValue(
      jsonOf({ is_superuser: false, managed_conferences: ["wsc2026-test"] })
    );

    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    expect(await screen.findByText("Admin content")).toBeInTheDocument();
  });

  test("shows a notice for an authenticated non-member", async () => {
    fetchWithAuth.mockResolvedValue(
      jsonOf({ is_superuser: false, managed_conferences: ["another-conf"] })
    );

    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    expect(
      await screen.findByText(/do not have access to this conference/i)
    ).toBeInTheDocument();
    expect(screen.queryByText("Admin content")).not.toBeInTheDocument();
    expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
  });

  test("redirects when the session probe fails", async () => {
    fetchWithAuth.mockRejectedValue(new Error("boom"));

    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    const marker = await screen.findByTestId("navigate");
    expect(marker.dataset.to).toBe("/");
  });
});
