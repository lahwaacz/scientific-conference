import { fireEvent, render, screen } from "@testing-library/react";
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
      registration_instructions: "Fill the form.",
      registration_opening: "2026-03-01",
      registration_deadline: "2026-04-01",
      submission_edit_deadline: "2026-04-15",
    });
  });
});
