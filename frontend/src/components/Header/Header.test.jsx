import { fireEvent, render, screen } from "@testing-library/react";
import Header from "./Header";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  buildApiUrl: (path) => path,
}));

function mockSectionFetches({ accommodation, hiking }) {
  globalThis.fetch = vi.fn((url) => {
    if (url.includes("accommodation")) {
      return Promise.resolve({
        ok: true,
        json: async () => accommodation,
      });
    }
    return Promise.resolve({ ok: true, json: async () => hiking });
  });
}

describe("Header venue submenu visibility", () => {
  test("hides accommodation and hiking links when both are empty", async () => {
    mockSectionFetches({
      accommodation: { description: "", options: [] },
      hiking: [],
    });

    render(<Header />);

    expect(await screen.findByText("Venue")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Toggle venue submenu" })
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Accommodation")).not.toBeInTheDocument();
    expect(screen.queryByText("Hiking excursion")).not.toBeInTheDocument();
  });

  test("hovering the venue item opens no menu when both are empty", async () => {
    mockSectionFetches({
      accommodation: { description: "", options: [] },
      hiking: [],
    });

    const { container } = render(<Header />);

    expect(await screen.findByText("Venue")).toBeInTheDocument();
    const wrapper = container.querySelector("[class*='dropdownWrapper']");
    fireEvent.mouseEnter(wrapper);

    expect(
      container.querySelector("[class*='dropdownMenu']")
    ).not.toBeInTheDocument();
  });

  test("keeps the links when the sections have content", async () => {
    mockSectionFetches({
      accommodation: { description: "Hotels near the venue", options: [] },
      hiking: [{ id: 1, name: "Route" }],
    });

    render(<Header />);

    expect(
      await screen.findByRole("button", { name: "Toggle venue submenu" })
    ).toBeInTheDocument();
  });

  test("counts accommodation options as content even without a description", async () => {
    mockSectionFetches({
      accommodation: {
        description: "",
        options: [{ id: 1, name: "Hotel" }],
      },
      hiking: [],
    });

    render(<Header />);

    expect(
      await screen.findByRole("button", { name: "Toggle venue submenu" })
    ).toBeInTheDocument();
  });

  test("fails open when a section fetch fails", async () => {
    globalThis.fetch = vi.fn((url) =>
      url.includes("accommodation")
        ? Promise.reject(new Error("offline"))
        : Promise.resolve({ ok: true, json: async () => [] })
    );

    render(<Header />);

    expect(
      await screen.findByRole("button", { name: "Toggle venue submenu" })
    ).toBeInTheDocument();
  });
});
