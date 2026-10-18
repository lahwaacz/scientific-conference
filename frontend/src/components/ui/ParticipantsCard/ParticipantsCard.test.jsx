import { render, screen } from "@testing-library/react";
import ParticipantsCard from "./ParticipantsCard";

describe("ParticipantsCard abstract button", () => {
  test("renders the abstract button when the participant has an abstract", () => {
    render(
      <ParticipantsCard
        name="Jana Novotná"
        department="CTU"
        abstractId={12}
        photo={null}
      />
    );

    expect(
      screen.getByRole("button", { name: "TO THE ABSTRACT" })
    ).toBeInTheDocument();
  });

  test("hides the abstract button when the abstract id is null", () => {
    render(
      <ParticipantsCard
        name="Jan Novák"
        department="CTU"
        abstractId={null}
        photo={null}
      />
    );

    expect(
      screen.queryByRole("button", { name: "TO THE ABSTRACT" })
    ).not.toBeInTheDocument();
  });

  test("hides the abstract button when the abstract id is missing", () => {
    render(<ParticipantsCard name="Jan Novák" department="CTU" photo={null} />);

    expect(
      screen.queryByRole("button", { name: "TO THE ABSTRACT" })
    ).not.toBeInTheDocument();
  });
});
