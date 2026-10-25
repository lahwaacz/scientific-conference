import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { mockNavigate, setTestLocation } from "react-router-dom";
import { fetchWithAuth } from "../../utils/api";
import Header from "./Header";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  buildApiUrl: (path) => path,
  fetchWithAuth: vi.fn(),
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

function mockUserFetch(user) {
  fetchWithAuth.mockImplementation((url) =>
    url === "/api/auth/user/"
      ? Promise.resolve({ ok: true, json: async () => user })
      : Promise.resolve({ ok: true })
  );
}

beforeEach(() => {
  setTestLocation({ pathname: "/", search: "" });
  vi.clearAllMocks();
});

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

describe("Header admin nav", () => {
  afterEach(() => {
    setTestLocation({ pathname: "/", search: "" });
  });

  test("admin route renders admin nav instead of public links", async () => {
    setTestLocation({ pathname: "/admin-panel/edit-program", search: "" });
    mockUserFetch({ username: "alice", is_superuser: true });

    render(<Header />);

    expect(await screen.findByText("alice")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Admin panel home" })
    ).toHaveAttribute("href", "/admin-panel");
    expect(screen.getByRole("link", { name: "View site" })).toHaveAttribute(
      "href",
      "/"
    );
    expect(screen.getByRole("link", { name: "Django admin" })).toHaveAttribute(
      "href",
      "/admin/"
    );
    expect(screen.getByRole("button", { name: "Logout" })).toBeInTheDocument();
    expect(screen.queryByText("Program")).not.toBeInTheDocument();
  });

  test("admin route without superuser hides the Django admin link", async () => {
    setTestLocation({ pathname: "/admin-panel", search: "" });
    mockUserFetch({ username: "alice", is_superuser: false });

    render(<Header />);

    expect(await screen.findByText("alice")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Django admin" })
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View site" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Logout" })).toBeInTheDocument();
  });

  test("logout posts to the logout endpoint and navigates home", async () => {
    setTestLocation({ pathname: "/admin-panel", search: "" });
    mockUserFetch({ username: "alice", is_superuser: true });

    render(<Header />);

    expect(await screen.findByText("alice")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    expect(fetchWithAuth).toHaveBeenCalledWith("/api/auth/logout/", {
      method: "POST",
    });
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/"));
  });
});
