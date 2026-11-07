import { render, screen } from "@testing-library/react";
import SubmissionFields from "./SubmissionFields";

const baseProps = {
  formData: {
    name: "",
    email: "",
    affiliation: "",
    contribution_type: "talk",
    abstract_title: "",
    abstract_text: "",
    additional_authors: "",
    additional_affiliations: "",
    arrival: "",
    departure: "",
    info: "",
    is_student: false,
  },
  errors: {},
  photoPreview: null,
  onChange: vi.fn(),
  onPhotoChange: vi.fn(),
  onRemovePhoto: vi.fn(),
  onCropPhoto: undefined,
  wordCount: 0,
};

describe("SubmissionFields", () => {
  test("renders the plain arrival and departure labels by default", () => {
    render(<SubmissionFields {...baseProps} />);

    const arrival = screen.getByText("Arrival Date");
    const departure = screen.getByText("Departure Date");
    expect(arrival.textContent).toBe("Arrival Date *");
    expect(departure.textContent).toBe("Departure Date *");
    expect(screen.queryByText(/tentative/i)).not.toBeInTheDocument();
  });

  test("marks the arrival and departure labels as tentative", () => {
    render(<SubmissionFields {...baseProps} arrivalDepartureTentative />);

    const arrival = screen.getByText("Arrival Date (tentative)");
    const departure = screen.getByText("Departure Date (tentative)");
    expect(arrival.textContent).toBe("Arrival Date (tentative) *");
    expect(departure.textContent).toBe("Departure Date (tentative) *");
  });

  test("keeps the arrival and departure date inputs required by default", () => {
    render(<SubmissionFields {...baseProps} arrivalDepartureTentative />);

    expect(document.querySelector('input[name="arrival"]')).toHaveAttribute(
      "type",
      "date"
    );
    expect(document.querySelector('input[name="arrival"]')).toBeRequired();
    expect(document.querySelector('input[name="departure"]')).toHaveAttribute(
      "type",
      "date"
    );
    expect(document.querySelector('input[name="departure"]')).toBeRequired();
  });

  test("removes both date controls when dates are hidden", () => {
    render(<SubmissionFields {...baseProps} showDates={false} />);

    expect(document.querySelector('input[name="arrival"]')).toBeNull();
    expect(document.querySelector('input[name="departure"]')).toBeNull();
    expect(screen.queryByText(/Arrival Date/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Departure Date/i)).not.toBeInTheDocument();
  });

  test("shows the open abstract hint without a deadline and no required asterisk", () => {
    render(<SubmissionFields {...baseProps} />);

    expect(
      screen.getByText(
        "Required for the final contribution — you can add it later."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Abstract").textContent).not.toContain("*");
    expect(screen.getByText("Title").textContent).toBe("Title *");
  });

  test("shows the formatted deadline in the open abstract hint", () => {
    render(
      <SubmissionFields {...baseProps} abstractLaterUntil="15 June 2099" />
    );

    expect(
      screen.getByText(
        "Required for the final contribution — you can add it later until 15 June 2099."
      )
    ).toBeInTheDocument();
  });

  test("shows the closed abstract hint instead of promising later editing", () => {
    render(
      <SubmissionFields
        {...baseProps}
        abstractLaterUntil="15 June 2099"
        abstractEditingClosed
      />
    );

    expect(
      screen.getByText(
        "The abstract can no longer be added online; contact the organizers."
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/you can add it later/i)).not.toBeInTheDocument();
  });
});
