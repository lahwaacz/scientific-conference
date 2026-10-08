import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { mockNavigate } from "react-router-dom";
import RegistrationForm from "./RegistrationForm";

const { mockInfo, holder } = vi.hoisted(() => ({
  mockInfo: {
    registration_opening: null,
    registration_deadline: "2099-12-31",
    date_end: null,
    registration_fee_note: "Conference fee is free of charge",
  },
  holder: { info: null },
}));

vi.mock("../hooks/useConferenceInfo", () => ({
  useConferenceInfo: () => holder.info,
}));

vi.mock("../ui/Modal/Modal", () => ({
  default: function MockModal({ isOpen, title, message }) {
    return isOpen ? (
      <div data-testid="modal">
        <div>{title}</div>
        <div>{message}</div>
      </div>
    ) : null;
  },
}));

const successResponse = {
  ok: true,
  status: 201,
  json: async () => ({
    participant_reference: "wsc2026-0042",
    tracking_token: "abc123",
  }),
};

function submitValidForm() {
  fireEvent.change(document.querySelector('input[name="name"]'), {
    target: { name: "name", value: "Alice Smith" },
  });

  fireEvent.change(screen.getByPlaceholderText(/your.email@example.com/i), {
    target: { name: "email", value: "alice@example.com" },
  });

  fireEvent.change(screen.getByPlaceholderText(/University or Institution/i), {
    target: { name: "affiliation", value: "CTU Prague" },
  });

  fireEvent.change(document.querySelector('input[name="arrival"]'), {
    target: { name: "arrival", value: "2026-09-10" },
  });

  fireEvent.change(document.querySelector('input[name="departure"]'), {
    target: { name: "departure", value: "2026-09-12" },
  });

  fireEvent.click(screen.getByRole("button", { name: /^submit$/i }));
}

describe("RegistrationForm", () => {
  let consoleErrorSpy;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    Object.assign(mockInfo, {
      registration_opening: null,
      registration_deadline: "2099-12-31",
      date_end: null,
      registration_fee_note: "Conference fee is free of charge",
    });
    holder.info = mockInfo;
  });

  afterEach(() => {
    vi.clearAllMocks();
    consoleErrorSpy.mockRestore();
    Reflect.deleteProperty(window.navigator, "clipboard");
    delete document.execCommand;
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

  test("renders no form or notice until the conference info arrives", () => {
    holder.info = null;

    render(<RegistrationForm />);

    expect(screen.getByText(/Registration Form/i)).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/your.email@example.com/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /submit/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Registration is closed/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Registration is not open yet/i)
    ).not.toBeInTheDocument();
  });

  test("shows a closed notice instead of the form after the deadline", () => {
    mockInfo.registration_deadline = "2020-01-01";

    render(<RegistrationForm />);

    expect(screen.getByText(/Registration is closed/i)).toBeInTheDocument();
    expect(screen.getByText(/The deadline was/i)).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/your.email@example.com/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /submit/i })
    ).not.toBeInTheDocument();
  });

  test("shows a not-yet-open notice instead of the form before the opening date", () => {
    mockInfo.registration_opening = "2099-01-01";

    render(<RegistrationForm />);

    expect(
      screen.getByText(/Registration is not open yet/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/It opens on/i)).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/your.email@example.com/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /submit/i })
    ).not.toBeInTheDocument();
  });

  test("shows the conference-ended notice for a past conference without a deadline", () => {
    mockInfo.registration_deadline = null;
    mockInfo.date_end = "2020-01-01";

    render(<RegistrationForm />);

    expect(
      screen.getByText(/conference has already taken place/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /submit/i })
    ).not.toBeInTheDocument();
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

    // Submit the form directly: jsdom's HTML5 validation blocks the click
    // path before React's custom validate() runs (name here stays empty).
    fireEvent.submit(document.querySelector("form"));

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

    // See the email-validation test above: HTML5 validation blocks click
    // submit with an empty required name field in jsdom.
    fireEvent.submit(document.querySelector("form"));

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

  test("submits valid form data successfully and shows the tracking panel", async () => {
    globalThis.fetch.mockResolvedValueOnce(successResponse);

    render(<RegistrationForm />);

    submitValidForm();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/submit/",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      })
    );

    expect(await screen.findByText("wsc2026-0042")).toBeInTheDocument();
    expect(screen.getByText(/#\/track\/abc123/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Save this link — it is the only way to access and edit your submission/i
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/contact the organizers/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /copy link/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Open my submission/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Submit another registration/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/your.email@example.com/i)
    ).not.toBeInTheDocument();
  });

  test("Open my submission navigates to the tracking route", async () => {
    globalThis.fetch.mockResolvedValueOnce(successResponse);

    render(<RegistrationForm />);

    submitValidForm();

    fireEvent.click(
      await screen.findByRole("button", { name: /Open my submission/i })
    );

    expect(mockNavigate).toHaveBeenCalledWith("/track/abc123");
  });

  test("Submit another registration restores the empty form", async () => {
    globalThis.fetch.mockResolvedValueOnce(successResponse);

    render(<RegistrationForm />);

    submitValidForm();

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Submit another registration/i,
      })
    );

    expect(screen.getByPlaceholderText(/your.email@example.com/i)).toHaveValue(
      ""
    );
    expect(document.querySelector('input[name="name"]')).toHaveValue("");
    expect(screen.queryByText("wsc2026-0042")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^submit$/i })
    ).toBeInTheDocument();
  });

  test("copies the tracking link to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    globalThis.fetch.mockResolvedValueOnce(successResponse);

    render(<RegistrationForm />);

    submitValidForm();

    fireEvent.click(await screen.findByRole("button", { name: /copy link/i }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        expect.stringContaining("#/track/abc123")
      );
    });
    expect(await screen.findByText(/Copied!/i)).toBeInTheDocument();
  });

  test("shows the generic error alert when the success response lacks tracking fields", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "ok" }),
    });

    render(<RegistrationForm />);

    submitValidForm();

    expect(await screen.findByTestId("modal")).toBeInTheDocument();
    expect(
      screen.getByText(/Connection error. Please try again./i)
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/your.email@example.com/i)
    ).toBeInTheDocument();
  });

  test("falls back to execCommand when the clipboard API is unavailable", async () => {
    Object.defineProperty(window.navigator, "clipboard", {
      value: undefined,
      configurable: true,
    });
    document.execCommand = vi.fn(() => true);
    globalThis.fetch.mockResolvedValueOnce(successResponse);

    render(<RegistrationForm />);

    submitValidForm();

    fireEvent.click(await screen.findByRole("button", { name: /copy link/i }));

    expect(document.execCommand).toHaveBeenCalledWith("copy");
    expect(await screen.findByText(/Copied!/i)).toBeInTheDocument();
  });

  test("shows error modal when server returns error", async () => {
    globalThis.fetch.mockResolvedValueOnce({
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
    globalThis.fetch.mockRejectedValueOnce(new Error("Network error"));

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
