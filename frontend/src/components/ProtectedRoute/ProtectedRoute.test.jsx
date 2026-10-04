import { render, screen } from "@testing-library/react";
import ProtectedRoute from "./ProtectedRoute";

describe("ProtectedRoute", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("renders Navigate to the public page when there is no token", () => {
    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    const marker = screen.getByTestId("navigate");
    expect(marker.dataset.to).toBe("/");
    expect(screen.queryByText("Admin content")).not.toBeInTheDocument();
  });

  test("renders children when an access token exists", () => {
    localStorage.setItem("access_token", "tok");

    render(
      <ProtectedRoute>
        <div>Admin content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText("Admin content")).toBeInTheDocument();
    expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
  });
});
