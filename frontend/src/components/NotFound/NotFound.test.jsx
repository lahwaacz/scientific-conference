import { render, screen } from "@testing-library/react";
import NotFound from "./NotFound";

// The react-router-dom test alias maps Link to a plain <a href={to}>, so the
// home link is asserted by its rendered href.
describe("NotFound", () => {
  test("renders the heading", () => {
    render(<NotFound />);

    expect(
      screen.getByRole("heading", { name: "Page Not Found" })
    ).toBeInTheDocument();
  });

  test("renders the message text", () => {
    render(<NotFound />);

    expect(
      screen.getByText("The page you are looking for does not exist.")
    ).toBeInTheDocument();
  });

  test("renders a link back to home", () => {
    render(<NotFound />);

    const link = screen.getByRole("link", { name: "Back to home" });
    expect(link).toHaveAttribute("href", "/");
  });
});
