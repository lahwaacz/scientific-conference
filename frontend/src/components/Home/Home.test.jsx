import { render } from "@testing-library/react";
import Home from "./Home";

vi.mock("../Hero/Hero", () => ({
  default: () => <div data-testid="hero" />,
}));
vi.mock("../Registration/Registration", () => ({
  default: () => <div data-testid="registration" />,
}));
vi.mock("../Sponsors/Sponsors", () => ({
  default: () => <div data-testid="sponsors" />,
}));
vi.mock("../OrganisingCommittee/OrganisingCommittee", () => ({
  default: () => <div data-testid="committee" />,
}));
vi.mock("../Organisers/Organisers", () => ({
  default: () => <div data-testid="organisers" />,
}));

describe("Home", () => {
  test("renders Sponsors between Registration and the committee", () => {
    const { container } = render(<Home />);
    const order = [...container.querySelectorAll("[data-testid]")].map(
      (node) => node.dataset.testid
    );

    expect(order).toEqual([
      "hero",
      "registration",
      "sponsors",
      "committee",
      "organisers",
    ]);
  });
});
