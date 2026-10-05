import { fireEvent, render, screen } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import EditWebInfoHome from "./EditWebInfoHome";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

/**
 * The GET conference-info payload carries the merged logistics keys
 * (title/location/date_start/date_end plus short_description,
 * badge_title, photo, year). Logistics are editable here: the form
 * renders them and PATCHes them back as multipart FormData. `year` is
 * derived from date_start on the backend and must never be sent;
 * `photo` is sent only when a replacement file is selected.
 */
const mergedInfo = {
  id: 1,
  title: "Workshop on Scientific Computing 2026",
  year: 2026,
  location: "Děčín",
  date_start: "2026-05-29",
  date_end: "2026-05-30",
  short_description: "Annual scientific computing workshop.",
  badge_title: "WSC 2026",
  photo: "/media/conferences/wsc2026.jpg",
  description: "About the conference.",
  registration_fee_note: "Free of charge.",
  registration_instructions: "Fill the form.",
  registration_deadline: "2026-04-01",
};

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

function mockInitialFetch() {
  fetchWithAuth
    .mockResolvedValueOnce(jsonOf(mergedInfo))
    .mockResolvedValueOnce(jsonOf([]))
    .mockResolvedValueOnce(jsonOf([]));
}

async function renderLoaded() {
  mockInitialFetch();
  const view = render(<EditWebInfoHome />);
  await screen.findByDisplayValue("About the conference.");
  return view;
}

function editCall() {
  const call = fetchWithAuth.mock.calls.find(
    ([url]) => url === "/api/conference-info/edit/"
  );
  expect(call).toBeDefined();
  return call;
}

async function submitForm() {
  const { container } = await renderLoaded();
  fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
  fireEvent.submit(container.querySelector("form"));
  expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();
  return editCall();
}

describe("EditWebInfoHome logistics editing", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
  });

  test("renders logistics inputs without year or Django-admin hint", async () => {
    const { container } = await renderLoaded();

    for (const value of [
      "Workshop on Scientific Computing 2026",
      "Děčín",
      "2026-05-29",
      "2026-05-30",
      "Annual scientific computing workshop.",
      "WSC 2026",
    ]) {
      expect(screen.getByDisplayValue(value)).toBeInTheDocument();
    }

    for (const label of [
      "Conference Title",
      "Short Description",
      "Location",
      "Badge Title",
      "Date Start",
      "Date End",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }

    expect(container.querySelector('input[name="year"]')).toBeNull();
    expect(container.querySelector('input[type="file"]')).not.toBeNull();
    expect(screen.queryByText(/Django admin/)).not.toBeInTheDocument();
  });

  test("save PATCHes logistics and web fields as FormData", async () => {
    const call = await submitForm();

    expect(call[1].method).toBe("PATCH");
    const body = call[1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("title")).toBe("Workshop on Scientific Computing 2026");
    expect(body.get("location")).toBe("Děčín");
    expect(body.get("date_start")).toBe("2026-05-29");
    expect(body.get("date_end")).toBe("2026-05-30");
    expect(body.get("short_description")).toBe(
      "Annual scientific computing workshop."
    );
    expect(body.get("badge_title")).toBe("WSC 2026");
    expect(body.get("description")).toBe("About the conference.");
    expect(body.get("registration_fee_note")).toBe("Free of charge.");
    expect(body.has("year")).toBe(false);
  });

  test("save omits photo from FormData when no file is selected", async () => {
    const call = await submitForm();

    expect(call[1].body).toBeInstanceOf(FormData);
    expect(call[1].body.get("photo")).toBeNull();
  });

  test("save appends the selected photo file to FormData", async () => {
    const { container } = await renderLoaded();

    const file = new File(["fake"], "conference.png", {
      type: "image/png",
    });
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [file] },
    });

    fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
    fireEvent.submit(container.querySelector("form"));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const body = editCall()[1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("photo")).toBe(file);
    expect(body.get("title")).toBe("Workshop on Scientific Computing 2026");
  });
});
