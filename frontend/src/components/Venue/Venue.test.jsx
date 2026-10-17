import { render, screen } from "@testing-library/react";
import Venue from "./Venue";

/**
 * Venue renders from useConferenceInfo, which GETs /api/conference-info/
 * through the global fetch. Mocking that fetch resolves the hook; the slug
 * singleton stays null (landing scope), so the URL goes out unprefixed.
 */

const venuePayload = {
  venue_text: "The winter school takes place in Děčín.",
  venue_photo: "/media/conferences/wsc2026-venue.jpg",
  venue_map_embed_url: "https://www.google.com/maps/embed?pb=fake",
};

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

function expectBefore(a, b) {
  expect(
    a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING
  ).toBeTruthy();
}

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

describe("Venue", () => {
  test("renders the venue photo between the text and the map", async () => {
    globalThis.fetch.mockResolvedValue(jsonOf(venuePayload));

    render(<Venue />);

    const text = await screen.findByText(
      "The winter school takes place in Děčín."
    );
    const photo = screen.getByRole("img", { name: "Venue" });
    expect(photo).toHaveAttribute(
      "src",
      "http://localhost:8000/media/conferences/wsc2026-venue.jpg"
    );
    const map = screen.getByTitle("Venue map");

    expectBefore(text, photo);
    expectBefore(photo, map);
  });

  test("renders no image when venue_photo is null", async () => {
    globalThis.fetch.mockResolvedValue(
      jsonOf({ ...venuePayload, venue_photo: null })
    );

    render(<Venue />);

    const text = await screen.findByText(
      "The winter school takes place in Děčín."
    );
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    // The map follows the description directly.
    const map = screen.getByTitle("Venue map");
    expectBefore(text, map);
  });

  test("renders venue_text markdown as elements, not literal syntax", async () => {
    globalThis.fetch.mockResolvedValue(
      jsonOf({
        venue_text:
          "The winter school takes place in **Děčín**. See the [venue website](https://example.com).",
        venue_photo: null,
        venue_map_embed_url: null,
      })
    );

    render(<Venue />);

    const bold = await screen.findByText("Děčín");
    expect(bold.tagName).toBe("STRONG");

    const link = screen.getByRole("link", { name: "venue website" });
    expect(link).toHaveAttribute("href", "https://example.com");

    // Raw markdown syntax must not show up as literal characters.
    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument();
  });

  test("renders nothing for an empty venue_text", async () => {
    globalThis.fetch.mockResolvedValue(
      jsonOf({ ...venuePayload, venue_text: "", venue_photo: null })
    );

    render(<Venue />);

    const map = await screen.findByTitle("Venue map");
    expect(map).toBeInTheDocument();
    expect(
      screen.queryByText("The winter school takes place in Děčín.")
    ).not.toBeInTheDocument();
  });
});
