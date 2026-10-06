import { render, screen, within } from "@testing-library/react";

/**
 * Landing reads the conference slug singleton (utils/conferenceSlug), which
 * captures window.location.pathname at init time. Every test therefore
 * reloads the module graph (vi.resetModules), points window.location at the
 * landing root ("/"), inits the slug, and only then imports Landing so the
 * whole import chain (utils/api included) binds to the fresh slug state.
 */

function setLocation(locationValue) {
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: locationValue,
  });
}

async function renderLanding(props = {}) {
  vi.resetModules();
  setLocation({ pathname: "/" });
  const slugModule = await import("../../utils/conferenceSlug");
  slugModule.initConferenceSlug();
  const { default: Landing } = await import("./Landing");
  render(<Landing {...props} />);
  return slugModule;
}

function listResponse(items) {
  return { ok: true, json: async () => items };
}

function conference(overrides) {
  return {
    slug: "wsc2026",
    title: "WSC 2026",
    date_start: "2026-05-29",
    date_end: "2026-05-30",
    year: 2026,
    location: "Děčín",
    card_photo: "media/wsc2026.png",
    short_description: "The running one.",
    status: "running",
    ...overrides,
  };
}

// Deliberately NOT grouped by status: the component must group by `status`
// while preserving the server order within each group.
const mixedPayload = [
  conference({
    slug: "past-old",
    title: "Past Old",
    status: "past",
    date_start: null,
    date_end: null,
    year: 2023,
    card_photo: null,
  }),
  conference({
    slug: "future-b",
    title: "Future B",
    status: "future",
    date_start: "2027-06-01",
    date_end: null,
    year: 2027,
  }),
  conference({ slug: "wsc2026" }),
  conference({
    slug: "past-new",
    title: "Past New",
    status: "past",
    date_start: "2025-05-29",
    date_end: "2025-05-30",
    year: 2025,
  }),
  conference({
    slug: "future-a",
    title: "Future A",
    status: "future",
    date_start: "2028-06-01",
    date_end: "2028-06-03",
    year: 2028,
  }),
];

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

describe("Landing", () => {
  test("groups conferences Running → Upcoming → Past preserving server order within groups", async () => {
    globalThis.fetch.mockResolvedValue(listResponse(mixedPayload));

    await renderLanding();

    await screen.findByRole("heading", { name: "Running" });
    // Group heading order is fixed, never the payload order.
    const headings = screen
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    expect(headings).toEqual(["Running", "Upcoming", "Past"]);

    // Per-group membership and counts.
    const running = screen
      .getByRole("heading", { name: "Running" })
      .closest("section");
    const upcoming = screen
      .getByRole("heading", { name: "Upcoming" })
      .closest("section");
    const past = screen
      .getByRole("heading", { name: "Past" })
      .closest("section");
    expect(within(running).getAllByRole("link")).toHaveLength(1);
    expect(within(upcoming).getAllByRole("link")).toHaveLength(2);
    expect(within(past).getAllByRole("link")).toHaveLength(2);

    // Document order of the card anchors proves the grouped output keeps
    // the flat server order inside each group despite the shuffled payload.
    const hrefs = screen
      .getAllByRole("link")
      .map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual([
      "/wsc2026/",
      "/future-b/",
      "/future-a/",
      "/past-old/",
      "/past-new/",
    ]);

    // The allowlisted global endpoint is hit, without a conference prefix.
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/conferences/"
    );
  });

  test("each card is a plain anchor to the conference URL, without a hash", async () => {
    globalThis.fetch.mockResolvedValue(listResponse([conference({})]));

    const slugModule = await renderLanding();

    const link = await screen.findByRole("link");
    const href = link.getAttribute("href");
    expect(href).toBe(slugModule.conferenceUrl("wsc2026"));
    expect(href).toBe("/wsc2026/");
    expect(href).not.toContain("#");
  });

  test("formats the date range, falls back to the year, then to Dates TBA", async () => {
    globalThis.fetch.mockResolvedValue(listResponse(mixedPayload));

    await renderLanding();

    // Both dates → full range.
    expect(
      await screen.findByText("29 May 2026 – 30 May 2026")
    ).toBeInTheDocument();
    // One date missing → the year only.
    expect(screen.getByText("2027")).toBeInTheDocument();
    // Both dates missing → TBA.
    expect(screen.getByText("Dates TBA")).toBeInTheDocument();
  });

  test("omits empty groups entirely", async () => {
    globalThis.fetch.mockResolvedValue(
      listResponse([conference({}), conference({ slug: "wsc2027" })])
    );

    await renderLanding();

    expect(
      await screen.findByRole("heading", { name: "Running" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Upcoming" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Past" })
    ).not.toBeInTheDocument();
  });

  test("shows the empty state when there are no conferences", async () => {
    globalThis.fetch.mockResolvedValue(listResponse([]));

    await renderLanding();

    expect(await screen.findByText("No conferences yet.")).toBeInTheDocument();
    expect(screen.queryAllByRole("heading", { level: 2 })).toHaveLength(0);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  test("shows an error state when the fetch fails", async () => {
    globalThis.fetch.mockRejectedValue(new Error("network down"));

    await renderLanding();

    expect(
      await screen.findByText(/failed to load conferences/i)
    ).toBeInTheDocument();
  });

  test("shows a not-found banner above the cards for an unknown slug", async () => {
    globalThis.fetch.mockResolvedValue(listResponse(mixedPayload));

    await renderLanding({ unknownSlug: "ghost-conference" });

    expect(
      await screen.findByText('Conference "ghost-conference" was not found.')
    ).toBeInTheDocument();
    // The landing itself still renders as the recovery path.
    expect(
      await screen.findByRole("heading", { name: "Running" })
    ).toBeInTheDocument();
  });

  test("shows no not-found banner on the plain landing page", async () => {
    globalThis.fetch.mockResolvedValue(listResponse(mixedPayload));

    await renderLanding();

    expect(
      await screen.findByRole("heading", { name: "Running" })
    ).toBeInTheDocument();
    expect(screen.queryByText(/was not found/i)).not.toBeInTheDocument();
  });

  test("card title pairs the title with the year like the conference page", async () => {
    globalThis.fetch.mockResolvedValue(
      listResponse([
        conference({ title: "Winter School" }),
        conference({
          slug: "no-dates",
          title: "No Dates Yet",
          date_start: null,
          date_end: null,
          year: null,
        }),
      ])
    );

    await renderLanding();

    expect(
      await screen.findByRole("heading", { name: "Winter School 2026" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "No Dates Yet" })
    ).toBeInTheDocument();
  });

  test("renders a card without an image when the photo is null", async () => {
    globalThis.fetch.mockResolvedValue(
      listResponse([
        conference({ slug: "with-photo", title: "With Photo" }),
        conference({
          slug: "no-photo",
          title: "No Photo",
          card_photo: null,
        }),
      ])
    );

    await renderLanding();

    const withPhoto = await screen.findByRole("link", { name: /With Photo/ });
    const img = within(withPhoto).getByRole("img", { name: "With Photo" });
    expect(img.getAttribute("src")).toBe(
      "http://localhost:8000/media/wsc2026.png"
    );

    const noPhoto = screen.getByRole("link", { name: /No Photo/ });
    expect(within(noPhoto).queryByRole("img")).not.toBeInTheDocument();
  });
});
