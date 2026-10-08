import { countWords, validateSubmissionForm } from "./submissionForm";

const validFormData = (overrides = {}) => ({
  name: "Alice Smith",
  email: "alice@example.com",
  affiliation: "CTU Prague",
  abstract_title: "A talk",
  abstract_text: "A brief description of the contribution.",
  additional_authors: "",
  additional_affiliations: "",
  arrival: "2026-09-10",
  departure: "2026-09-12",
  info: "",
  is_student: false,
  ...overrides,
});

const words = (count) =>
  Array.from({ length: count }, (_, i) => `word${i}`).join(" ");

describe("countWords", () => {
  test("returns 0 for empty and whitespace-only text", () => {
    expect(countWords("")).toBe(0);
    expect(countWords("   \n\t  ")).toBe(0);
  });

  test("counts whitespace-separated words", () => {
    expect(countWords("one two three")).toBe(3);
  });

  test("treats runs of whitespace, tabs, and newlines as one separator", () => {
    expect(countWords("  one   two\nthree\tfour  ")).toBe(4);
  });
});

describe("validateSubmissionForm", () => {
  test("returns no errors for a valid form", () => {
    expect(
      validateSubmissionForm({ formData: validFormData(), photo: null })
    ).toEqual({});
  });

  test("flags an invalid email", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ email: "invalid-email" }),
      photo: null,
    });
    expect(errors.email).toBe("Please enter a valid email");
  });

  test("trims the email before validating", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ email: "  alice@example.com  " }),
      photo: null,
    });
    expect(errors.email).toBeUndefined();
  });

  test("flags an affiliation shorter than 3 characters", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ affiliation: "CT" }),
      photo: null,
    });
    expect(errors.affiliation).toBe("Please enter a valid affiliation");
  });

  test("accepts an affiliation of exactly 3 characters", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ affiliation: "CTU" }),
      photo: null,
    });
    expect(errors.affiliation).toBeUndefined();
  });

  test("flags an abstract over 250 words", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ abstract_text: words(251) }),
      photo: null,
    });
    expect(errors.abstract_text).toBe("Abstract must not exceed 250 words");
  });

  test("accepts an abstract of exactly 250 words", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ abstract_text: words(250) }),
      photo: null,
    });
    expect(errors.abstract_text).toBeUndefined();
  });

  test("flags a missing arrival date", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ arrival: "" }),
      photo: null,
    });
    expect(errors.arrival).toBe("Please select arrival date");
  });

  test("flags a missing departure date", () => {
    const errors = validateSubmissionForm({
      formData: validFormData({ departure: "" }),
      photo: null,
    });
    expect(errors.departure).toBe("Please select departure date");
  });

  test("flags a departure on or before the arrival", () => {
    for (const departure of ["2026-09-10", "2026-09-09"]) {
      const errors = validateSubmissionForm({
        formData: validFormData({ arrival: "2026-09-10", departure }),
        photo: null,
      });
      expect(errors.departure).toBe(
        "Departure date must be after arrival date"
      );
    }
  });

  test("flags a photo larger than 5MB", () => {
    const errors = validateSubmissionForm({
      formData: validFormData(),
      photo: { size: 5 * 1024 * 1024 + 1 },
    });
    expect(errors.photo).toBe("Photo size must not exceed 5MB");
  });

  test("accepts a photo of exactly 5MB", () => {
    const errors = validateSubmissionForm({
      formData: validFormData(),
      photo: { size: 5 * 1024 * 1024 },
    });
    expect(errors.photo).toBeUndefined();
  });
});
