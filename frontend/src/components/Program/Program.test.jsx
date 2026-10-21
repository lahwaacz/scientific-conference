import { render, screen } from "@testing-library/react";
import { setTestLocation } from "react-router-dom";
import Program from "./Program";

const { holder } = vi.hoisted(() => ({
  holder: { info: { program_text: "" } },
}));

vi.mock("./../hooks/useConferenceInfo", () => ({
  useConferenceInfo: () => holder.info,
}));

vi.mock("./ProgramDay", () => ({
  default: ({ day, highlightTalkId, highlightSessionId }) => (
    <div>
      day:{day.date}|talk:{highlightTalkId ?? "none"}|session:
      {highlightSessionId ?? "none"}
    </div>
  ),
}));

function programResponse(days) {
  return { ok: true, json: async () => days };
}

describe("Program", () => {
  beforeEach(() => {
    holder.info = { program_text: "" };
    setTestLocation({ pathname: "/", search: "" });
    globalThis.fetch = vi.fn(() => Promise.resolve(programResponse([])));
  });

  test("shows the not-ready notice when the schedule is empty", async () => {
    render(<Program />);

    expect(
      await screen.findByText("The program is not ready yet.")
    ).toBeInTheDocument();
  });

  test("hides the not-ready notice when the schedule has days", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve(programResponse([{ id: 1, date: "2027-05-29" }]))
    );
    render(<Program />);

    expect(await screen.findByText(/day:2027-05-29/)).toBeInTheDocument();
    expect(
      screen.queryByText("The program is not ready yet.")
    ).not.toBeInTheDocument();
  });

  test("passes session and talk highlight targets to the day", async () => {
    setTestLocation({ pathname: "/", search: "?session=8" });
    globalThis.fetch = vi.fn(() =>
      Promise.resolve(programResponse([{ id: 1, date: "2027-05-29" }]))
    );
    render(<Program />);

    expect(await screen.findByText(/session:8/)).toBeInTheDocument();
    expect(screen.getByText(/talk:none/)).toBeInTheDocument();
  });

  test("renders the program text as markdown above the schedule", async () => {
    holder.info = { program_text: "## Talk rules\n\n- 20 minutes" };
    globalThis.fetch = vi.fn(() =>
      Promise.resolve(programResponse([{ id: 1, date: "2027-05-29" }]))
    );
    render(<Program />);

    expect(
      await screen.findByRole("heading", { level: 2, name: "Talk rules" })
    ).toBeInTheDocument();
    expect(screen.getByText("20 minutes")).toBeInTheDocument();
    expect(
      screen.queryByText("The program is not ready yet.")
    ).not.toBeInTheDocument();
  });
});
