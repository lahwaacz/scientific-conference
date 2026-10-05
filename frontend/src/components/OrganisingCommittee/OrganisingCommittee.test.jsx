import { render, screen } from "@testing-library/react";
import OrganisingCommittee from "./OrganisingCommittee";

// Unknown conference slugs make every scoped list endpoint return a 404
// body like {"detail": "Not found."} — list consumers must treat any
// non-array payload as an empty list instead of crashing on .map().
describe("OrganisingCommittee payload tolerance", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  test("renders committee cards for an array payload", async () => {
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 1,
          name: "Jane Doe",
          department: "FNSPE",
          email: "jane@example.com",
          photo: null,
        },
      ],
    });

    render(<OrganisingCommittee />);

    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
  });

  test("renders an empty section when the API returns a 404 body", async () => {
    globalThis.fetch.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Not found." }),
    });

    render(<OrganisingCommittee />);

    expect(await screen.findByText("Organising Committee")).toBeInTheDocument();
    expect(screen.queryByText("Not found.")).not.toBeInTheDocument();
  });

  test("renders an empty section when the API returns a non-array body", async () => {
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ detail: "Not found." }),
    });

    render(<OrganisingCommittee />);

    expect(await screen.findByText("Organising Committee")).toBeInTheDocument();
  });
});
