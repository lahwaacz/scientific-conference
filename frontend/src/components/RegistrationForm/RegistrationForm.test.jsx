import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import RegistrationForm from "./RegistrationForm";

jest.mock("../hooks/useConferenceInfo", () => ({
  useConferenceInfo: () => ({
    registration_deadline: "2026-09-01",
    registration_fee_note: "Conference fee is free of charge",
  }),
}));

jest.mock("../ui/Modal/Modal", () => {
  return function MockModal({ isOpen, title, message }) {
    return isOpen ? (
      <div data-testid="modal">
        <div>{title}</div>
        <div>{message}</div>
      </div>
    ) : null;
  };
});

describe("RegistrationForm", () => {
  let consoleErrorSpy;

  beforeEach(() => {
    global.fetch = jest.fn();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy.mockRestore();
  });

  test("renders main form fields", () => {
    render(<RegistrationForm />);

    expect(screen.getByText(/Registration Form/i)).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/your.email@example.com/i)
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/University or Institution/i)
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Title of your presentation/i)
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Brief description of your contribution/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
  });

  test("shows error for invalid email", async () => {
    render(<RegistrationForm />);

    fireEvent.change(screen.getByPlaceholderText(/your.email@example.com/i), {
      target: { name: "email", value: "invalid-email" },
    });

    fireEvent.change(
      screen.getByPlaceholderText(/University or Institution/i),
      {
        target: { name: "affiliation", value: "CTU" },
      }
    );

    fireEvent.change(document.querySelector('input[name="arrival"]'), {
      target: { name: "arrival", value: "2026-09-10" },
    });

    fireEvent.change(document.querySelector('input[name="departure"]'), {
      target: { name: "departure", value: "2026-09-12" },
    });

    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(
      await screen.findByText(/Please enter a valid email/i)
    ).toBeInTheDocument();
  });

  test("shows error when departure date is not after arrival date", async () => {
    render(<RegistrationForm />);

    fireEvent.change(screen.getByPlaceholderText(/your.email@example.com/i), {
      target: { name: "email", value: "user@example.com" },
    });

    fireEvent.change(
      screen.getByPlaceholderText(/University or Institution/i),
      {
        target: { name: "affiliation", value: "CTU" },
      }
    );

    fireEvent.change(document.querySelector('input[name="arrival"]'), {
      target: { name: "arrival", value: "2026-09-12" },
    });

    fireEvent.change(document.querySelector('input[name="departure"]'), {
      target: { name: "departure", value: "2026-09-12" },
    });

    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(
      await screen.findByText(/Departure date must be after arrival date/i)
    ).toBeInTheDocument();
  });

  test("rejects non-image file upload", async () => {
    render(<RegistrationForm />);

    const fileInput = document.querySelector('input[type="file"]');
    const badFile = new File(["hello"], "document.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(fileInput, {
      target: { files: [badFile] },
    });

    expect(
      await screen.findByText(/Please select a valid image file/i)
    ).toBeInTheDocument();
  });

  test("rejects oversized image upload", async () => {
    render(<RegistrationForm />);

    const fileInput = document.querySelector('input[type="file"]');
    const bigFile = new File([new ArrayBuffer(6 * 1024 * 1024)], "big.jpg", {
      type: "image/jpeg",
    });

    fireEvent.change(fileInput, {
      target: { files: [bigFile] },
    });

    expect(
      await screen.findByText(/Photo size must not exceed 5MB/i)
    ).toBeInTheDocument();
  });

  test("submits valid form data successfully", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "ok" }),
    });

    render(<RegistrationForm />);

    fireEvent.change(document.querySelector('input[name="name"]'), {
      target: { name: "name", value: "Alice Smith" },
    });

    fireEvent.change(screen.getByPlaceholderText(/your.email@example.com/i), {
      target: { name: "email", value: "alice@example.com" },
    });

    fireEvent.change(
      screen.getByPlaceholderText(/University or Institution/i),
      {
        target: { name: "affiliation", value: "CTU Prague" },
      }
    );

    fireEvent.change(document.querySelector('input[name="arrival"]'), {
      target: { name: "arrival", value: "2026-09-10" },
    });

    fireEvent.change(document.querySelector('input[name="departure"]'), {
      target: { name: "departure", value: "2026-09-12" },
    });

    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/submit/",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      })
    );

    expect(await screen.findByTestId("modal")).toBeInTheDocument();
    expect(screen.getByText(/Registration successful!/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Your submission is pending review./i)
    ).toBeInTheDocument();
  });

  test("shows error modal when server returns error", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ email: ["Invalid"] }),
    });

    render(<RegistrationForm />);

    fireEvent.change(document.querySelector('input[name="name"]'), {
      target: { name: "name", value: "Alice Smith" },
    });

    fireEvent.change(screen.getByPlaceholderText(/your.email@example.com/i), {
      target: { name: "email", value: "alice@example.com" },
    });

    fireEvent.change(
      screen.getByPlaceholderText(/University or Institution/i),
      {
        target: { name: "affiliation", value: "CTU Prague" },
      }
    );

    fireEvent.change(document.querySelector('input[name="arrival"]'), {
      target: { name: "arrival", value: "2026-09-10" },
    });

    fireEvent.change(document.querySelector('input[name="departure"]'), {
      target: { name: "departure", value: "2026-09-12" },
    });

    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByTestId("modal")).toBeInTheDocument();
    expect(screen.getByText(/Error/i)).toBeInTheDocument();
    expect(screen.getByText(/Registration failed/i)).toBeInTheDocument();
  });

  test("shows connection error modal when fetch throws", async () => {
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    render(<RegistrationForm />);

    fireEvent.change(document.querySelector('input[name="name"]'), {
      target: { name: "name", value: "Alice Smith" },
    });

    fireEvent.change(screen.getByPlaceholderText(/your.email@example.com/i), {
      target: { name: "email", value: "alice@example.com" },
    });

    fireEvent.change(
      screen.getByPlaceholderText(/University or Institution/i),
      {
        target: { name: "affiliation", value: "CTU Prague" },
      }
    );

    fireEvent.change(document.querySelector('input[name="arrival"]'), {
      target: { name: "arrival", value: "2026-09-10" },
    });

    fireEvent.change(document.querySelector('input[name="departure"]'), {
      target: { name: "departure", value: "2026-09-12" },
    });

    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    expect(await screen.findByTestId("modal")).toBeInTheDocument();
    expect(
      screen.getByText(/Connection error. Please try again./i)
    ).toBeInTheDocument();
  });
});
