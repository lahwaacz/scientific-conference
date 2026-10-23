import { render, screen } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import ProtectedRoute from "./ProtectedRoute";

vi.mock("../../utils/api", () => ({
  fetchWithAuth: vi.fn(),
}));

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

  test("renders children when the session probe succeeds", async () => {
    fetchWithAuth.mockResolvedValue({ ok: true, status: 200 });

    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    expect(await screen.findByText("Admin content")).toBeInTheDocument();
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
