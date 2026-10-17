import { render, screen } from "@testing-library/react";
import Accommodation from "./Accommodation";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  buildApiUrl: (path) => path,
}));

const accommodationPayload = {
  description: "Stay in **Děčín**.",
  options: [],
};

beforeEach(() => {
  globalThis.fetch = vi.fn((url) => {
    if (url.includes("accommodation")) {
      return Promise.resolve({
        ok: true,
        json: async () => accommodationPayload,
      });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
});

describe("Accommodation", () => {
  test("renders description markdown as elements, not literal syntax", async () => {
    render(<Accommodation />);

    const bold = await screen.findByText("Děčín");
    expect(bold.tagName).toBe("STRONG");

    // Raw markdown syntax must not show up as literal characters.
    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument();
  });

  test("renders option description markdown as elements", async () => {
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        description: "",
        options: [
          {
            id: 1,
            name: "Hotel",
            url: "https://example.com",
            description: "Book **early**.",
          },
        ],
      }),
    });

    render(<Accommodation />);

    const bold = await screen.findByText("early");
    expect(bold.tagName).toBe("STRONG");
    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument();
  });
});
