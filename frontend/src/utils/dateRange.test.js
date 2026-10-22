import { afterEach, describe, expect, it } from "vitest";
import { formatDateRange } from "./dateRange";

const originalTZ = process.env.TZ;

afterEach(() => {
  if (originalTZ === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = originalTZ;
  }
});

describe("formatDateRange", () => {
  it("collapses the month and year for a same-month range", () => {
    expect(formatDateRange("2027-08-20", "2027-08-22")).toBe(
      "20–22 August 2027"
    );
  });

  it("renders one date when the start and end are the same day", () => {
    expect(formatDateRange("2027-08-20", "2027-08-20")).toBe("20 August 2027");
  });

  it("keeps full dates when the range crosses a month", () => {
    expect(formatDateRange("2027-05-31", "2027-06-02")).toBe(
      "31 May 2027 – 2 June 2027"
    );
  });

  it("keeps full dates when the range crosses a year", () => {
    expect(formatDateRange("2027-12-28", "2028-01-03")).toBe(
      "28 December 2027 – 3 January 2028"
    );
  });

  it("keeps date-only values on the same calendar day in UTC-negative zones", () => {
    process.env.TZ = "America/New_York";

    expect(formatDateRange("2027-06-01", "2027-06-30")).toBe("1–30 June 2027");
    expect(formatDateRange("2027-12-31", "2027-12-31")).toBe(
      "31 December 2027"
    );
  });
});
