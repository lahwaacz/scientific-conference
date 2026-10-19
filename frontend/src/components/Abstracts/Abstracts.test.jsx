import { render, screen } from "@testing-library/react";
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
  talk_id: 7,
};

function mockFetches({ program, programFails = false, abstract = ABSTRACT }) {
  globalThis.fetch = vi.fn((url) => {
    if (url.includes("program")) {
      return programFails
        ? Promise.reject(new Error("offline"))
        : Promise.resolve({ ok: true, json: async () => program });
    }
    return Promise.resolve({ ok: true, json: async () => [abstract] });
  });
}

const programButton = () =>
  screen.queryByRole("button", { name: "TO THE PROGRAM" });

describe("Abstracts program button visibility", () => {
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
      abstract: { ...ABSTRACT, id: 2, title: "A poster", talk_id: null },
    });

    render(<Abstracts />);

    expect(await screen.findByText("A poster")).toBeInTheDocument();
    expect(programButton()).not.toBeInTheDocument();
  });

  test("fails open when the program fetch fails", async () => {
    mockFetches({ program: [], programFails: true });

    render(<Abstracts />);

    expect(await screen.findByText("A talk")).toBeInTheDocument();
    expect(programButton()).toBeInTheDocument();
  });
});
