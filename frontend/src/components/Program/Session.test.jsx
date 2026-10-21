import { render, screen } from "@testing-library/react";
import Session from "./Session";

const posterSession = {
  id: 8,
  kind: "poster",
  chair: "",
  start_time: "16:30:00",
  end_time: "17:30:00",
  talks: [
    {
      id: 20,
      title: "Adaptive mesh refinement for contact problems",
      talk_type: "poster",
      participant: { name: "Hana Nováková" },
      start_time: null,
      end_time: null,
    },
  ],
};

describe("Session", () => {
  test("renders a poster session with one shared time slot and no per-poster times", () => {
    render(<Session session={posterSession} />);

    expect(screen.getByText("Poster session")).toBeInTheDocument();
    expect(screen.getByText("16:30 – 17:30")).toBeInTheDocument();
    expect(
      screen.getByText("Adaptive mesh refinement for contact problems")
    ).toBeInTheDocument();
    expect(screen.queryByText("–")).not.toBeInTheDocument();
  });

  test("renders a talk session without a poster time header", () => {
    render(
      <Session
        session={{
          ...posterSession,
          kind: "talk",
          chair: "Chair",
          talks: [
            {
              ...posterSession.talks[0],
              talk_type: "talk",
              start_time: "16:30:00",
              end_time: "16:50:00",
            },
          ],
        }}
      />
    );

    expect(screen.queryByText("Poster session")).not.toBeInTheDocument();
    expect(screen.getByText("16:30 – 16:50")).toBeInTheDocument();
  });
});
