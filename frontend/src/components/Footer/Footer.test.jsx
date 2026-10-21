import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import Footer from "./Footer";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

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
  document.body.style.cssText = "";
  fetchWithAuth.mockReset();
  globalThis.fetch = vi.fn().mockResolvedValue(jsonOf(infoPayload));
});

describe("Footer", () => {
  test("restores body scrolling after a successful admin login", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access: "A", refresh: "R" }),
    });
    render(<Footer />);

    fireEvent.click(
      await screen.findByRole("button", { name: /administration/i })
    );
    expect(document.body.style.position).toBe("fixed");
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.change(screen.getByPlaceholderText(/enter username/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByPlaceholderText(/enter password/i), {
      target: { value: "pw" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^login$/i }));

    await waitFor(() => expect(document.body.style.position).toBe(""));
    expect(document.body.style.overflow).toBe("");
  });

  test("renders the footer venue field, not the venue page description", async () => {
    render(<Footer />);

    expect(await screen.findByText("Footer venue blurb")).toBeInTheDocument();
    expect(
      screen.queryByText("Venue page description")
    ).not.toBeInTheDocument();
  });
});
