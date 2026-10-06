import { render, screen } from "@testing-library/react";
import Registration from "./Registration";

const { holder } = vi.hoisted(() => ({ holder: { info: null } }));

vi.mock("../hooks/useConferenceInfo", () => ({
  useConferenceInfo: () => holder.info,
}));

describe("Registration", () => {
  beforeEach(() => {
    holder.info = null;
  });

  test("renders no instructions until the conference info arrives", () => {
    render(<Registration />);

    expect(screen.queryByText("Affiliation")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Your contact address and e-mail/i)
    ).not.toBeInTheDocument();
  });

  test("falls back to the generic instructions when none are configured", () => {
    holder.info = { registration_instructions: "", registration_fee_note: "" };

    render(<Registration />);

    expect(screen.getByText("Affiliation")).toBeInTheDocument();
    expect(
      screen.getByText("The abstract of your contribution")
    ).toBeInTheDocument();
  });

  test("renders the configured instructions, one per line", () => {
    holder.info = {
      registration_instructions: "Bring an abstract\nPay the fee",
      registration_fee_note: "",
    };

    render(<Registration />);

    expect(screen.getByText("Bring an abstract")).toBeInTheDocument();
    expect(screen.getByText("Pay the fee")).toBeInTheDocument();
    expect(screen.queryByText("Affiliation")).not.toBeInTheDocument();
  });
});
