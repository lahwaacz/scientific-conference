import { render, screen } from "@testing-library/react";
import Footer from "./Footer";

/**
 * The footer venue column renders the dedicated `footer_venue_text` field,
 * independent of the venue page's `venue_text`. `useConferenceInfo` GETs
 * /api/conference-info/ through the global fetch, which is mocked here.
 */

const infoPayload = {
  footer_venue_text: "Footer venue blurb",
  venue_text: "Venue page description",
};

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue(jsonOf(infoPayload));
});

describe("Footer", () => {
  test("renders the footer venue field, not the venue page description", async () => {
    render(<Footer />);

    expect(await screen.findByText("Footer venue blurb")).toBeInTheDocument();
    expect(
      screen.queryByText("Venue page description")
    ).not.toBeInTheDocument();
  });
});
