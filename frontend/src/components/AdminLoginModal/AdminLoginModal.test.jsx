import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { fetchWithAuth } from "../../utils/api";
import AdminLoginModal from "./AdminLoginModal";

jest.mock("../../utils/api", () => ({
  fetchWithAuth: jest.fn(),
}));

describe("AdminLoginModal", () => {
  let onSuccess;
  let onClose;

  const fillPassword = (value) => {
    fireEvent.change(screen.getByPlaceholderText(/enter password/i), {
      target: { value },
    });
  };

  const submit = () => {
    fireEvent.click(screen.getByRole("button", { name: /^login$/i }));
  };

  beforeEach(() => {
    localStorage.clear();
    onSuccess = jest.fn();
    onClose = jest.fn();
    fetchWithAuth.mockReset();
  });

  test("posts to the login endpoint with the hardcoded admin username", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access: "A", refresh: "R" }),
    });
    render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
    fillPassword("s3cret");
    submit();

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const [url, opts] = fetchWithAuth.mock.calls[0];
    expect(url).toBe("/api/auth/login/");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({
      username: "admin",
      password: "s3cret",
    });
  });

  test("persists tokens and calls onSuccess on a 200", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access: "ACC", refresh: "REF" }),
    });
    render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
    fillPassword("pw");
    submit();

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(localStorage.getItem("access_token")).toBe("ACC");
    expect(localStorage.getItem("refresh_token")).toBe("REF");
  });

  test("shows the wrong-password message and does not persist on non-OK", async () => {
    fetchWithAuth.mockResolvedValueOnce({ ok: false });
    render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
    fillPassword("bad");
    submit();

    expect(await screen.findByText(/wrong password/i)).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(localStorage.getItem("access_token")).toBeNull();
  });

  test("shows the connection-error message when fetchWithAuth rejects", async () => {
    fetchWithAuth.mockRejectedValueOnce(new Error("boom"));
    render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
    fillPassword("pw");
    submit();

    expect(await screen.findByText(/connection error/i)).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
  });
});
