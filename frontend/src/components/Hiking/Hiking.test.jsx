import { render, screen } from "@testing-library/react";
import Hiking from "./Hiking";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  buildApiUrl: (path) => path,
}));

const routesPayload = [
  {
    id: 1,
    name: "Peak loop",
    way_description: "Follow the [map](https://example.com) to the summit.",
    map_url: null,
    stops: [],
  },
];

beforeEach(() => {
  globalThis.fetch = vi.fn((url) => {
    if (url.includes("hiking")) {
      return Promise.resolve({ ok: true, json: async () => routesPayload });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
});

describe("Hiking", () => {
  test("renders way_description markdown as a link", async () => {
    render(<Hiking />);

    const link = await screen.findByRole("link", { name: "map" });
    expect(link).toHaveAttribute("href", "https://example.com");

    // The visible label survives the markdown restructuring.
    expect(screen.getByText("Way:")).toBeInTheDocument();
  });

  test("renders stop description markdown as a link", async () => {
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 1,
          name: "Peak loop",
          way_description: "",
          map_url: null,
          stops: [
            {
              id: 2,
              name: "Summit",
              photo: null,
              description: "See the [map](https://example.com).",
            },
          ],
        },
      ],
    });

    render(<Hiking />);

    const link = await screen.findByRole("link", { name: "map" });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(screen.getByText("SUMMIT")).toBeInTheDocument();
  });
});
