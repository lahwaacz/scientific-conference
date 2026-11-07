import { fireEvent, render, screen, within } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import EditWebInfoRegistration from "./EditWebInfoRegistration";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

const loadedInfo = {
  id: 1,
  registration_fee_note: "Free of charge.",
  registration_instructions: "Fill the form.",
  registration_opening: "2026-03-01",
  registration_deadline: "2026-04-01",
  submission_edit_deadline: "2026-04-15",
  registration_allow_talk: true,
  registration_allow_poster: true,
  registration_allow_attend: true,
  registration_collect_dates: true,
};

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

async function renderLoaded() {
  fetchWithAuth.mockResolvedValueOnce(jsonOf(loadedInfo));
  const view = render(<EditWebInfoRegistration />);
  await screen.findByDisplayValue("Free of charge.");
  return view;
}

function editCall() {
  const call = fetchWithAuth.mock.calls.find(
    ([url]) => url === "/api/conference-info/edit/"
  );
  expect(call).toBeDefined();
  return call;
}

describe("EditWebInfoRegistration", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
  });

  test("renders the submission editing deadline input with the loaded value", async () => {
    const { container } = await renderLoaded();

    expect(screen.getByText("Submission Editing Deadline")).toBeInTheDocument();
    const input = container.querySelector(
      'input[name="submission_edit_deadline"]'
    );
    expect(input).not.toBeNull();
    expect(input).toHaveValue("2026-04-15");
  });

  test("save PATCHes JSON including submission_edit_deadline", async () => {
    const { container } = await renderLoaded();

    fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
    fireEvent.submit(container.querySelector("form"));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const call = editCall();
    expect(call[1].method).toBe("PATCH");
    expect(JSON.parse(call[1].body)).toEqual({
      registration_fee_note: "Free of charge.",
      registration_opening: "2026-03-01",
      registration_deadline: "2026-04-01",
      submission_edit_deadline: "2026-04-15",
      registration_allow_talk: true,
      registration_allow_poster: true,
      registration_allow_attend: true,
      registration_collect_dates: true,
    });
  });

  test("live preview reacts to unsaved contribution and date settings", async () => {
    await renderLoaded();

    const preview = screen.getByRole("list", {
      name: "Required registration data preview",
    });
    expect(
      within(preview).getByText("Title and abstract of your talk or poster")
    ).toBeInTheDocument();
    expect(
      within(preview).getByText("Arrival and departure dates")
    ).toBeInTheDocument();
    expect(
      document.querySelector('textarea[name="registration_instructions"]')
    ).toBeNull();

    fireEvent.click(screen.getByRole("checkbox", { name: "Talk" }));
    expect(
      within(preview).getByText("Title and abstract of your poster")
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Collect arrival and departure dates",
      })
    );
    expect(
      within(preview).queryByText("Arrival and departure dates")
    ).not.toBeInTheDocument();
  });

  test("saves an unchecked collect-dates flag without registration instructions", async () => {
    const { container } = await renderLoaded();

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Collect arrival and departure dates",
      })
    );
    fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
    fireEvent.submit(container.querySelector("form"));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const payload = JSON.parse(editCall()[1].body);
    expect(payload.registration_collect_dates).toBe(false);
    expect(payload).not.toHaveProperty("registration_instructions");
  });

  test("shows field-specific 400 responses and allows a corrected retry", async () => {
    const { container } = await renderLoaded();

    fetchWithAuth.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({
        registration_collect_dates: [
          "Single-day conferences cannot collect arrival and departure dates.",
        ],
        non_field_errors: [
          "Disable date collection before setting equal Home dates.",
        ],
      }),
    });
    fireEvent.submit(container.querySelector("form"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "registration_collect_dates: Single-day conferences cannot collect arrival and departure dates."
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Disable date collection before setting equal Home dates."
    );
    expect(
      screen.queryByText("Failed to save. Please try again.")
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Collect arrival and departure dates",
      })
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
    fireEvent.submit(container.querySelector("form"));

    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();
    const editCalls = fetchWithAuth.mock.calls.filter(
      ([url]) => url === "/api/conference-info/edit/"
    );
    expect(editCalls).toHaveLength(2);
    expect(
      JSON.parse(editCalls.at(-1)[1].body).registration_collect_dates
    ).toBe(false);
  });

  test("rejects disabling every contribution type", async () => {
    await renderLoaded();

    fireEvent.click(screen.getByRole("checkbox", { name: "Talk" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Poster" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Just attend" }));
    fireEvent.submit(document.querySelector("form"));

    expect(
      await screen.findByText("Select at least one contribution type.")
    ).toBeInTheDocument();
    expect(fetchWithAuth).not.toHaveBeenCalledWith(
      "/api/conference-info/edit/",
      expect.anything()
    );
  });
});
