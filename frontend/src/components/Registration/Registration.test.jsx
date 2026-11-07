import { render, screen } from "@testing-library/react";
import Registration from "./Registration";

const { holder } = vi.hoisted(() => ({ holder: { info: null } }));

vi.mock("../hooks/useConferenceInfo", () => ({
  useConferenceInfo: () => holder.info,
}));

function renderedRequirements() {
  return screen.getAllByRole("listitem").map((item) => item.textContent);
}

describe("Registration", () => {
  beforeEach(() => {
    holder.info = null;
  });

  test("renders no requirements until the conference info arrives", () => {
    render(<Registration />);

    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
    expect(screen.queryByText("Affiliation")).not.toBeInTheDocument();
  });

  test("renders the derived requirements instead of legacy instructions", () => {
    holder.info = {
      registration_instructions: "Bring an abstract\nPay the fee",
      registration_fee_note: "",
    };

    render(<Registration />);

    expect(renderedRequirements()).toEqual([
      "Name",
      "Your e-mail",
      "Affiliation",
      "Participation type",
      "Title and abstract of your talk or poster",
      "Arrival and departure dates",
    ]);
    expect(screen.queryByText("Bring an abstract")).not.toBeInTheDocument();
    expect(screen.queryByText("Pay the fee")).not.toBeInTheDocument();
  });

  test("omits participation and contribution items for attend-only registration without dates", () => {
    holder.info = {
      registration_allow_talk: false,
      registration_allow_poster: false,
      registration_allow_attend: true,
      registration_collect_dates: false,
      registration_fee_note: "",
    };

    render(<Registration />);

    expect(renderedRequirements()).toEqual([
      "Name",
      "Your e-mail",
      "Affiliation",
    ]);
  });
});
