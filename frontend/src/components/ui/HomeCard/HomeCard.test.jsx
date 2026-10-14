import { render, screen } from "@testing-library/react";
import HomeCard from "./HomeCard";

// The People API returns `email` as a string that may be empty; the card
// must turn a present email into a mailto link and render no link at all
// for an empty one (an empty mailto: would be a dead control).
describe("HomeCard email link", () => {
  test("renders the email as a clickable mailto link", () => {
    render(
      <HomeCard
        name="Jane Doe"
        affiliation="FNSPE"
        email="jane@example.com"
        photo={null}
      />
    );

    const link = screen.getByRole("link", { name: "jane@example.com" });
    expect(link).toHaveAttribute("href", "mailto:jane@example.com");
  });

  test("renders no link when the email is empty", () => {
    render(
      <HomeCard name="Jane Doe" affiliation="FNSPE" email="" photo={null} />
    );

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryByText("mailto:")).not.toBeInTheDocument();
  });

  test("renders no link when the email is missing", () => {
    render(<HomeCard name="Jane Doe" affiliation="FNSPE" photo={null} />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
