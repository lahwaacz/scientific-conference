import { render, screen } from "@testing-library/react";
import SubmissionFields from "./SubmissionFields";

const baseProps = {
  formData: {
    name: "",
    email: "",
    affiliation: "",
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

  test("keeps the arrival and departure date inputs intact", () => {
    render(<SubmissionFields {...baseProps} arrivalDepartureTentative />);

    expect(document.querySelector('input[name="arrival"]')).toHaveAttribute(
      "type",
      "date"
    );
    expect(document.querySelector('input[name="departure"]')).toHaveAttribute(
      "type",
      "date"
    );
  });
});
