import { fireEvent, render, screen, within } from "@testing-library/react";
import { mockNavigate } from "react-router-dom";
import Abstracts from "./Abstracts";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  buildApiUrl: (path) => path,
}));

const ABSTRACT = {
  id: 1,
  title: "A talk",
  authors_string: "A. Uthor",
  department: "Dept",
  text: "Abstract body",
  contribution_type: "talk",
  talk_id: 7,
};

const POSTER = {
  ...ABSTRACT,
  id: 2,
  title: "A poster",
  talk_id: 20,
  session_id: 8,
  contribution_type: "poster",
};

function mockFetches({
  program,
  programFails = false,
  abstract = ABSTRACT,
  abstracts = null,
}) {
  globalThis.fetch = vi.fn((url) => {
    if (url.includes("program")) {
      return programFails
        ? Promise.reject(new Error("offline"))
        : Promise.resolve({ ok: true, json: async () => program });
    }
    return Promise.resolve({
      ok: true,
      json: async () => abstracts ?? [abstract],
    });
  });
}

const programButton = () =>
  screen.queryByRole("button", { name: "TO THE PROGRAM" });

describe("Abstracts program button visibility", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  test("hides the button when the program is not ready", async () => {
    mockFetches({ program: [] });

    render(<Abstracts />);

    expect(await screen.findByText("A talk")).toBeInTheDocument();
    expect(programButton()).not.toBeInTheDocument();
  });

  test("shows the button when the program has days", async () => {
    mockFetches({ program: [{ id: 1, date: "2027-05-29" }] });

    render(<Abstracts />);

    expect(await screen.findByText("A talk")).toBeInTheDocument();
    expect(programButton()).toBeInTheDocument();
  });

  test("hides the button for poster abstracts without a talk", async () => {
    mockFetches({
      program: [{ id: 1, date: "2027-05-29" }],
      abstract: {
        ...ABSTRACT,
        id: 2,
        title: "A poster",
        talk_id: null,
        contribution_type: "poster",
      },
    });

    render(<Abstracts />);

    expect(await screen.findByText("A poster")).toBeInTheDocument();
    expect(programButton()).not.toBeInTheDocument();
  });

  test("shows poster badges and type filters when both types exist", async () => {
    mockFetches({
      program: [{ id: 1, date: "2027-05-29" }],
      abstracts: [ABSTRACT, POSTER],
    });

    render(<Abstracts />);

    expect(await screen.findByText("A poster")).toBeInTheDocument();
    expect(screen.getByText("Poster")).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Filter abstracts" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All (2)" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Talks (1)" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Posters (1)" })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Posters (1)" }));

    expect(screen.queryByText("A talk")).not.toBeInTheDocument();
    expect(screen.getByText("A poster")).toBeInTheDocument();
  });

  test("hides type filters for a talk-only list", async () => {
    mockFetches({ program: [{ id: 1, date: "2027-05-29" }] });

    render(<Abstracts />);

    expect(await screen.findByText("A talk")).toBeInTheDocument();
    expect(
      screen.queryByRole("group", { name: "Filter abstracts" })
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Poster")).not.toBeInTheDocument();
  });

  test("shows the poster badge but no filters for a poster-only list", async () => {
    mockFetches({
      program: [{ id: 1, date: "2027-05-29" }],
      abstracts: [POSTER],
    });

    render(<Abstracts />);

    expect(await screen.findByText("A poster")).toBeInTheDocument();
    expect(screen.getByText("Poster")).toBeInTheDocument();
    expect(
      screen.queryByRole("group", { name: "Filter abstracts" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Posters (1)" })
    ).not.toBeInTheDocument();
  });

  test("poster program button links to its poster session", async () => {
    mockFetches({
      program: [{ id: 1, date: "2027-05-29" }],
      abstracts: [POSTER],
    });

    render(<Abstracts />);

    const card = await screen.findByText("A poster");
    fireEvent.click(
      within(card.closest('[id^="abstract-"]')).getByRole("button", {
        name: "TO THE PROGRAM",
      })
    );

    expect(mockNavigate).toHaveBeenCalledWith("/program?session=8");
  });

  test("fails open when the program fetch fails", async () => {
    mockFetches({ program: [], programFails: true });

    render(<Abstracts />);

    expect(await screen.findByText("A talk")).toBeInTheDocument();
    expect(programButton()).toBeInTheDocument();
  });
});
