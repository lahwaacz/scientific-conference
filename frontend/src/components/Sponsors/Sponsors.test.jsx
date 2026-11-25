import { act, render, screen, waitFor } from "@testing-library/react";
import Sponsors from "./Sponsors";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  buildApiUrl: (path) => path,
}));

function mockSponsors(payload) {
  globalThis.fetch.mockResolvedValue({
    ok: true,
    json: async () => payload,
  });
}

describe("Sponsors", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  test("renders nothing for an empty sponsor list", async () => {
    mockSponsors([]);
    const { container } = render(<Sponsors />);

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
    await act(async () => {});

    expect(
      screen.queryByRole("heading", { name: "Sponsors" })
    ).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  test("renders a linked logo tile for a safe sponsor URL", async () => {
    mockSponsors([
      {
        id: 1,
        name: "Example Sponsor",
        url: "https://sponsor.example",
        logo: "/media/sponsors/example.png",
        order: 0,
      },
    ]);
    render(<Sponsors />);

    const logo = await screen.findByRole("img", {
      name: "Example Sponsor",
    });
    const link = logo.closest("a");

    expect(logo).toHaveAttribute("alt", "Example Sponsor");
    expect(link).not.toBeNull();
    expect(link).toHaveAttribute("href", "https://sponsor.example");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
  });

  test("links a plain http sponsor URL", async () => {
    mockSponsors([
      {
        id: 4,
        name: "Legacy Sponsor",
        url: "http://legacy.example",
        logo: null,
        order: 0,
      },
    ]);
    render(<Sponsors />);

    const link = await screen.findByRole("link", { name: "Legacy Sponsor" });
    expect(link).toHaveAttribute("href", "http://legacy.example");
  });

  test("stays hidden when the fetch rejects", async () => {
    globalThis.fetch.mockRejectedValue(new Error("offline"));
    const { container } = render(<Sponsors />);

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
    await act(async () => {});

    expect(container).toBeEmptyDOMElement();
  });

  test("stays hidden for a non-OK response", async () => {
    globalThis.fetch.mockResolvedValue({
      ok: false,
      json: async () => [],
    });
    const { container } = render(<Sponsors />);

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
    await act(async () => {});

    expect(container).toBeEmptyDOMElement();
  });

  test("stays hidden for a malformed payload", async () => {
    mockSponsors({ detail: "Unexpected" });
    const { container } = render(<Sponsors />);

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
    await act(async () => {});

    expect(container).toBeEmptyDOMElement();
  });

  test("renders the sponsor name when no logo is available", async () => {
    mockSponsors([
      {
        id: 2,
        name: "Text-only Sponsor",
        url: null,
        logo: null,
        order: 0,
      },
    ]);
    render(<Sponsors />);

    const name = await screen.findByText("Text-only Sponsor");
    expect(name.tagName).toBe("SPAN");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  test("does not link a tile with a javascript URL", async () => {
    mockSponsors([
      {
        id: 3,
        name: "Unsafe Sponsor",
        url: "javascript:alert(1)",
        logo: null,
        order: 0,
      },
    ]);
    render(<Sponsors />);

    const name = await screen.findByText("Unsafe Sponsor");
    expect(name.closest("a")).toBeNull();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
