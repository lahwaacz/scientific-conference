import { fireEvent, render, screen } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import EditWebInfoVenue from "./EditWebInfoVenue";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

/**
 * The editor PATCHes /api/conference-info/edit/ as multipart FormData so a
 * replacement venue photo can be attached. venue_text and
 * venue_map_embed_url are always sent; venue_photo is appended only when a
 * new file is selected (an absent key keeps the existing photo).
 */
const mergedInfo = {
  venue_text: "The winter school takes place in Děčín.",
  venue_map_embed_url: "https://www.google.com/maps/embed?pb=fake",
  venue_photo: "/media/conferences/wsc2026-venue.jpg",
};

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

async function renderLoaded() {
  fetchWithAuth.mockResolvedValueOnce(jsonOf(mergedInfo));
  const view = render(<EditWebInfoVenue />);
  await screen.findByDisplayValue("The winter school takes place in Děčín.");
  return view;
}

function editCall() {
  const call = fetchWithAuth.mock.calls.find(
    ([url]) => url === "/api/conference-info/edit/"
  );
  expect(call).toBeDefined();
  return call;
}

async function submitForm(container) {
  fetchWithAuth.mockResolvedValueOnce(jsonOf({}));
  fireEvent.submit(container.querySelector("form"));
  expect(await screen.findByText("✓ Saved successfully")).toBeInTheDocument();
  return editCall();
}

describe("EditWebInfoVenue venue editing", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
    // jsdom lacks URL.createObjectURL; the new-photo preview needs it.
    URL.createObjectURL = vi.fn(() => "blob:preview");
  });

  test("shows the current venue photo preview from buildMediaUrl", async () => {
    await renderLoaded();

    // Once in the Photo field, once in the Preview section.
    for (const img of screen.getAllByRole("img", { name: "Venue" })) {
      expect(img).toHaveAttribute(
        "src",
        "http://localhost:8000/media/conferences/wsc2026-venue.jpg"
      );
    }
  });

  test("save PATCHes text fields as FormData without venue_photo when no file is selected", async () => {
    const { container } = await renderLoaded();

    const call = await submitForm(container);

    expect(call[1].method).toBe("PATCH");
    const body = call[1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("venue_text")).toBe(
      "The winter school takes place in Děčín."
    );
    expect(body.get("venue_map_embed_url")).toBe(
      "https://www.google.com/maps/embed?pb=fake"
    );
    expect(body.has("venue_photo")).toBe(false);
  });

  test("save appends the selected venue photo file to FormData", async () => {
    const { container } = await renderLoaded();

    const file = new File(["fake"], "venue.png", {
      type: "image/png",
    });
    fireEvent.change(container.querySelector('input[name="venue_photo"]'), {
      target: { files: [file] },
    });

    const call = await submitForm(container);

    const body = call[1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("venue_photo")).toBe(file);
    expect(body.get("venue_text")).toBe(
      "The winter school takes place in Děčín."
    );
  });
});
