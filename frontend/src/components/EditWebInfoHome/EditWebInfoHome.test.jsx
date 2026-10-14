import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import EditWebInfoHome from "./EditWebInfoHome";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

/**
 * The GET conference-info payload carries the merged logistics keys
 * (title/location/date_start/date_end plus short_description,
 * badge_title, card_photo, hero_photo, year). Logistics are editable
 * here: the form renders them and PATCHes them back as multipart
 * FormData. `year` is derived from date_start on the backend and must
 * never be sent; the photos are sent only when a replacement file is
 * selected. The registration_* keys stay in the fixture because the
 * API returns them, but they are owned by the Registration subsection
 * editor, so the Home editor neither renders nor PATCHes them.
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
  card_photo: "/media/conferences/wsc2026.jpg",
  hero_photo: "/media/conferences/wsc2026-hero.jpg",
  venue_photo: "/media/conferences/wsc2026-venue.jpg",
  description: "About the conference.",
  registration_fee_note: "Free of charge.",
  registration_instructions: "Fill the form.",
  registration_deadline: "2026-04-01",
  submission_edit_deadline: "2026-04-15",
};

const peopleFixture = [
  {
    id: 7,
    name: "Jane Doe",
    affiliation: "FNSPE",
    email: "jane@example.com",
    photo: "/media/people/jane.jpg",
    roles: ["organizer", "committee"],
    user: null,
    user_username: null,
  },
];

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

function textOf(payload) {
  return { ok: true, text: async () => JSON.stringify(payload) };
}

function mockInitialFetch(people = []) {
  fetchWithAuth
    .mockResolvedValueOnce(jsonOf(mergedInfo))
    .mockResolvedValueOnce(jsonOf(people));
}

async function renderLoaded(people = []) {
  mockInitialFetch(people);
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
    // jsdom lacks URL.createObjectURL; the hero image preview needs it.
    URL.createObjectURL = vi.fn(() => "blob:preview");
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
      "Card photo",
      "Hero photo",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }

    expect(
      screen.getByRole("img", { name: "Conference hero" })
    ).toHaveAttribute(
      "src",
      "http://localhost:8000/media/conferences/wsc2026-hero.jpg"
    );

    expect(
      screen.getByRole("img", { name: "Conference card" })
    ).toHaveAttribute(
      "src",
      "http://localhost:8000/media/conferences/wsc2026.jpg"
    );

    expect(container.querySelector('input[name="year"]')).toBeNull();
    expect(container.querySelector('input[type="file"]')).not.toBeNull();
    expect(screen.queryByText(/Django admin/)).not.toBeInTheDocument();
    expect(screen.queryByText("Registration Deadline")).not.toBeInTheDocument();
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
    expect(body.has("registration_fee_note")).toBe(false);
    expect(body.has("registration_deadline")).toBe(false);
    expect(body.has("submission_edit_deadline")).toBe(false);
    expect(body.has("year")).toBe(false);
  });

  test("save omits every photo from FormData when no file is selected", async () => {
    const call = await submitForm();

    expect(call[1].body).toBeInstanceOf(FormData);
    expect(call[1].body.get("card_photo")).toBeNull();
    expect(call[1].body.get("hero_photo")).toBeNull();
    // venue_photo is owned by the Venue editor; sending its URL string
    // here would make DRF's ImageField reject the whole PATCH (400).
    expect(call[1].body.has("venue_photo")).toBe(false);
  });

  test("save appends the selected card photo file to FormData", async () => {
    const { container } = await renderLoaded();

    const file = new File(["fake"], "conference.png", {
      type: "image/png",
    });
    fireEvent.change(container.querySelector('input[name="card_photo"]'), {
      target: { files: [file] },
    });

    fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
    fireEvent.submit(container.querySelector("form"));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const body = editCall()[1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("card_photo")).toBe(file);
    expect(body.get("hero_photo")).toBeNull();
    expect(body.get("title")).toBe("Workshop on Scientific Computing 2026");
  });

  test("selecting a card photo swaps the stored image for a blob preview", async () => {
    const { container } = await renderLoaded();

    expect(
      screen.getByRole("img", { name: "Conference card" })
    ).toBeInTheDocument();

    const file = new File(["fake"], "conference.png", {
      type: "image/png",
    });
    fireEvent.change(container.querySelector('input[name="card_photo"]'), {
      target: { files: [file] },
    });

    expect(
      screen.queryByRole("img", { name: "Conference card" })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "New card preview" })
    ).toHaveAttribute("src", "blob:preview");
  });

  test("save appends the selected hero photo file to FormData", async () => {
    const { container } = await renderLoaded();

    const file = new File(["fake"], "hero.png", {
      type: "image/png",
    });
    fireEvent.change(container.querySelector('input[name="hero_photo"]'), {
      target: { files: [file] },
    });

    fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
    fireEvent.submit(container.querySelector("form"));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const body = editCall()[1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("hero_photo")).toBe(file);
    expect(body.get("card_photo")).toBeNull();
  });
});

describe("EditWebInfoHome people management", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
    URL.createObjectURL = vi.fn(() => "blob:preview");
  });

  test("loads people in the same fetch round as conference-info", async () => {
    await renderLoaded(peopleFixture);

    expect(fetchWithAuth).toHaveBeenCalledTimes(2);
    expect(fetchWithAuth.mock.calls[0][0]).toBe("/api/conference-info/");
    expect(fetchWithAuth.mock.calls[1][0]).toBe("/api/people/");
  });

  test("renders role checkboxes reflecting each person's roles", async () => {
    await renderLoaded(peopleFixture);

    expect(await screen.findByDisplayValue("Jane Doe")).toBeInTheDocument();
    expect(screen.getByDisplayValue("FNSPE")).toBeInTheDocument();
    expect(screen.getByDisplayValue("jane@example.com")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Organiser" })).toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: "Organising Committee" })
    ).toBeChecked();
  });

  test("saving people PATCHes /api/people/<id>/ as JSON with an explicit roles array", async () => {
    await renderLoaded(peopleFixture);
    await screen.findByDisplayValue("Jane Doe");

    fireEvent.click(
      screen.getByRole("checkbox", { name: "Organising Committee" })
    );
    expect(
      screen.getByRole("checkbox", { name: "Organising Committee" })
    ).not.toBeChecked();

    fetchWithAuth.mockResolvedValueOnce(
      textOf({ ...peopleFixture[0], roles: ["organizer"] })
    );
    fireEvent.click(screen.getByRole("button", { name: "SAVE PEOPLE" }));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const call = fetchWithAuth.mock.calls.find(
      ([url]) => url === "/api/people/7/"
    );
    expect(call).toBeDefined();
    expect(call[1].method).toBe("PATCH");
    // JSON, not FormData: an explicit (possibly empty) roles array must
    // reach the server, which multipart cannot express.
    expect(typeof call[1].body).toBe("string");
    expect(JSON.parse(call[1].body)).toEqual({
      name: "Jane Doe",
      affiliation: "FNSPE",
      email: "jane@example.com",
      roles: ["organizer"],
    });
  });

  test("unchecking the last role saves an empty roles array", async () => {
    await renderLoaded([{ ...peopleFixture[0], roles: ["organizer"] }]);
    await screen.findByDisplayValue("Jane Doe");

    fireEvent.click(screen.getByRole("checkbox", { name: "Organiser" }));
    expect(
      screen.getByRole("checkbox", { name: "Organiser" })
    ).not.toBeChecked();

    fetchWithAuth.mockResolvedValueOnce(
      textOf({ ...peopleFixture[0], roles: [] })
    );
    fireEvent.click(screen.getByRole("button", { name: "SAVE PEOPLE" }));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const call = fetchWithAuth.mock.calls.find(
      ([url]) => url === "/api/people/7/"
    );
    expect(JSON.parse(call[1].body).roles).toEqual([]);
  });

  test("saving with a photo selected PATCHes the photo as multipart after the JSON save", async () => {
    await renderLoaded(peopleFixture);
    await screen.findByDisplayValue("Jane Doe");

    const file = new File(["fake"], "person.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("Change photo"), {
      target: { files: [file] },
    });

    fetchWithAuth
      .mockResolvedValueOnce(textOf(peopleFixture[0]))
      .mockResolvedValueOnce(textOf(peopleFixture[0]));
    fireEvent.click(screen.getByRole("button", { name: "SAVE PEOPLE" }));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const calls = fetchWithAuth.mock.calls.filter(
      ([url]) => url === "/api/people/7/"
    );
    expect(calls).toHaveLength(2);
    const [jsonCall, photoCall] = calls;
    expect(jsonCall[1].method).toBe("PATCH");
    expect(JSON.parse(jsonCall[1].body).roles).toEqual([
      "organizer",
      "committee",
    ]);
    expect(photoCall[1].method).toBe("PATCH");
    expect(photoCall[1].body).toBeInstanceOf(FormData);
    expect(photoCall[1].body.get("photo")).toBe(file);
  });

  test("a newly added person POSTs to /api/people/ as JSON with no roles by default", async () => {
    await renderLoaded(peopleFixture);
    await screen.findByDisplayValue("Jane Doe");

    fireEvent.click(screen.getByRole("button", { name: "+ ADD PERSON" }));

    fetchWithAuth
      .mockResolvedValueOnce(textOf(peopleFixture[0]))
      .mockResolvedValueOnce(
        textOf({
          id: 8,
          name: "",
          affiliation: "",
          email: "",
          photo: null,
          roles: [],
        })
      );
    fireEvent.click(screen.getByRole("button", { name: "SAVE PEOPLE" }));
    expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();

    const postCall = fetchWithAuth.mock.calls.find(
      ([url, options]) => url === "/api/people/" && options?.method === "POST"
    );
    expect(postCall).toBeDefined();
    expect(JSON.parse(postCall[1].body)).toEqual({
      name: "",
      affiliation: "",
      email: "",
      roles: [],
    });
  });

  test("deleting a person sends DELETE /api/people/<id>/", async () => {
    await renderLoaded(peopleFixture);
    await screen.findByDisplayValue("Jane Doe");

    fetchWithAuth.mockResolvedValueOnce({ ok: true, text: async () => "" });
    fireEvent.click(screen.getByRole("button", { name: "✕" }));

    await waitFor(() =>
      expect(screen.queryByDisplayValue("Jane Doe")).not.toBeInTheDocument()
    );
    expect(fetchWithAuth).toHaveBeenCalledWith("/api/people/7/", {
      method: "DELETE",
    });
  });
});
