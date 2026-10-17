import {
  isArrivalDepartureTentative,
  registrationWindowStatus,
  submissionEditEffectiveDeadline,
  submissionEditWindowStatus,
} from "./registrationWindow";

const info = (overrides = {}) => ({
  registration_opening: null,
  registration_deadline: null,
  date_start: null,
  date_end: null,
  ...overrides,
});

const day = (iso) => new Date(`${iso}T12:00:00`);

describe("registrationWindowStatus", () => {
  test("no bounds means always open", () => {
    expect(registrationWindowStatus(info(), day("2026-05-15"))).toBe("open");
  });

  test("no info yet means open", () => {
    expect(registrationWindowStatus(null, day("2026-05-15"))).toBe("open");
  });

  test("closed before the opening date, open on it", () => {
    const conf = info({ registration_opening: "2026-05-01" });
    expect(registrationWindowStatus(conf, day("2026-04-30"))).toBe("not-open");
    expect(registrationWindowStatus(conf, day("2026-05-01"))).toBe("open");
  });

  test("open on the deadline date, closed after it", () => {
    const conf = info({ registration_deadline: "2026-05-31" });
    expect(registrationWindowStatus(conf, day("2026-05-31"))).toBe("open");
    expect(registrationWindowStatus(conf, day("2026-06-01"))).toBe("closed");
  });

  test("open only inside the window", () => {
    const conf = info({
      registration_opening: "2026-05-01",
      registration_deadline: "2026-05-31",
    });
    expect(registrationWindowStatus(conf, day("2026-04-30"))).toBe("not-open");
    expect(registrationWindowStatus(conf, day("2026-05-15"))).toBe("open");
    expect(registrationWindowStatus(conf, day("2026-06-01"))).toBe("closed");
  });

  test("uses the local date, not UTC", () => {
    const conf = info({ registration_deadline: "2026-05-31" });
    // 2026-06-01 00:30 local time: past the deadline locally, but still
    // 2026-05-31 in UTC — a UTC-based comparison would wrongly stay open.
    const afterMidnightLocal = new Date(2026, 5, 1, 0, 30);
    expect(registrationWindowStatus(conf, afterMidnightLocal)).toBe("closed");
  });

  test("a past conference is ended even without a deadline", () => {
    const conf = info({ date_end: "2026-05-31" });
    expect(registrationWindowStatus(conf, day("2026-05-31"))).toBe("open");
    expect(registrationWindowStatus(conf, day("2026-06-01"))).toBe("ended");
  });

  test("a past conference stays ended even with a future deadline", () => {
    const conf = info({
      date_end: "2026-05-31",
      registration_deadline: "2030-01-01",
    });
    expect(registrationWindowStatus(conf, day("2026-06-01"))).toBe("ended");
  });
});

describe("submissionEditWindowStatus", () => {
  test("no deadline and no date_start means always open", () => {
    expect(submissionEditWindowStatus(info(), day("2099-05-15"))).toBe("open");
  });

  test("no info yet means open", () => {
    expect(submissionEditWindowStatus(null, day("2026-05-15"))).toBe("open");
  });

  test("a future deadline keeps editing open", () => {
    const conf = info({ submission_edit_deadline: "2026-05-31" });
    expect(submissionEditWindowStatus(conf, day("2026-05-15"))).toBe("open");
  });

  test("open on the deadline date, closed after it", () => {
    const conf = info({ submission_edit_deadline: "2026-05-31" });
    expect(submissionEditWindowStatus(conf, day("2026-05-31"))).toBe("open");
    expect(submissionEditWindowStatus(conf, day("2026-06-01"))).toBe("closed");
  });

  test("an empty deadline closes editing the day before date_start", () => {
    const conf = info({ date_start: "2026-05-10" });
    expect(submissionEditWindowStatus(conf, day("2026-05-09"))).toBe("open");
    expect(submissionEditWindowStatus(conf, day("2026-05-10"))).toBe("closed");
    expect(submissionEditWindowStatus(conf, day("2026-05-11"))).toBe("closed");
  });

  test("an explicit deadline wins over date_start", () => {
    const conf = info({
      date_start: "2026-05-10",
      submission_edit_deadline: "2026-06-01",
    });
    expect(submissionEditWindowStatus(conf, day("2026-06-01"))).toBe("open");
    expect(submissionEditWindowStatus(conf, day("2026-06-02"))).toBe("closed");
  });

  test("ignores the registration window but not the conference end date", () => {
    const conf = info({
      registration_opening: "2026-05-01",
      registration_deadline: "2026-05-31",
      date_end: "2026-06-05",
    });
    expect(submissionEditWindowStatus(conf, day("2026-06-05"))).toBe("open");
    expect(submissionEditWindowStatus(conf, day("2026-06-06"))).toBe("closed");
    expect(submissionEditWindowStatus(conf, day("2026-06-10"))).toBe("closed");
  });

  test("date_end caps a later explicit edit deadline", () => {
    const conf = info({
      submission_edit_deadline: "2026-06-20",
      date_end: "2026-06-05",
    });
    expect(submissionEditWindowStatus(conf, day("2026-06-05"))).toBe("open");
    expect(submissionEditWindowStatus(conf, day("2026-06-06"))).toBe("closed");
  });
});

describe("submissionEditEffectiveDeadline", () => {
  test("returns the explicit deadline", () => {
    const conf = info({
      date_start: "2026-05-10",
      submission_edit_deadline: "2026-06-01",
    });
    expect(submissionEditEffectiveDeadline(conf)).toBe("2026-06-01");
  });

  test("caps the explicit deadline at an earlier date_end", () => {
    const conf = info({
      submission_edit_deadline: "2026-06-20",
      date_end: "2026-06-05",
    });
    expect(submissionEditEffectiveDeadline(conf)).toBe("2026-06-05");
  });

  test("falls back to the day before date_start", () => {
    expect(
      submissionEditEffectiveDeadline(info({ date_start: "2026-05-10" }))
    ).toBe("2026-05-09");
  });

  test("keeps the day before date_start when it is earlier than date_end", () => {
    expect(
      submissionEditEffectiveDeadline(
        info({ date_start: "2026-05-10", date_end: "2026-06-05" })
      )
    ).toBe("2026-05-09");
  });

  test("falls back to date_end when no deadline or date_start is set", () => {
    expect(
      submissionEditEffectiveDeadline(info({ date_end: "2026-06-05" }))
    ).toBe("2026-06-05");
  });

  test("returns null when neither is set", () => {
    expect(submissionEditEffectiveDeadline(info())).toBeNull();
    expect(submissionEditEffectiveDeadline(null)).toBeNull();
  });
});

describe("isArrivalDepartureTentative", () => {
  test("not tentative without a deadline or date_start", () => {
    expect(isArrivalDepartureTentative(info(), day("2020-05-15"))).toBe(false);
  });

  test("no info yet means not tentative", () => {
    expect(isArrivalDepartureTentative(null, day("2026-05-15"))).toBe(false);
  });

  test("tentative strictly more than one month before the deadline", () => {
    const conf = info({ submission_edit_deadline: "2026-09-15" });
    expect(isArrivalDepartureTentative(conf, day("2026-05-15"))).toBe(true);
    expect(isArrivalDepartureTentative(conf, day("2026-08-14"))).toBe(true);
  });

  test("not tentative within one month of the deadline", () => {
    const conf = info({ submission_edit_deadline: "2026-09-15" });
    expect(isArrivalDepartureTentative(conf, day("2026-08-16"))).toBe(false);
    expect(isArrivalDepartureTentative(conf, day("2026-09-15"))).toBe(false);
  });

  test("exactly one month before the deadline is not tentative", () => {
    const conf = info({ submission_edit_deadline: "2026-09-15" });
    expect(isArrivalDepartureTentative(conf, day("2026-08-15"))).toBe(false);
  });

  test("an explicit deadline wins over date_start", () => {
    const conf = info({
      date_start: "2026-09-20",
      submission_edit_deadline: "2026-08-31",
    });
    expect(isArrivalDepartureTentative(conf, day("2026-07-30"))).toBe(true);
    expect(isArrivalDepartureTentative(conf, day("2026-07-31"))).toBe(false);
  });

  test("falls back to date_start when the deadline is missing or empty", () => {
    const missing = info({ date_start: "2026-09-20" });
    expect(isArrivalDepartureTentative(missing, day("2026-08-19"))).toBe(true);
    expect(isArrivalDepartureTentative(missing, day("2026-08-20"))).toBe(false);
    const empty = info({
      date_start: "2026-09-20",
      submission_edit_deadline: "",
    });
    expect(isArrivalDepartureTentative(empty, day("2026-08-19"))).toBe(true);
    expect(isArrivalDepartureTentative(empty, day("2026-08-20"))).toBe(false);
  });

  test("the one-month boundary crosses the year turn", () => {
    const conf = info({ date_start: "2027-01-15" });
    expect(isArrivalDepartureTentative(conf, day("2026-12-14"))).toBe(true);
    expect(isArrivalDepartureTentative(conf, day("2026-12-15"))).toBe(false);
  });

  test("a month-end cutoff clamps instead of overflowing (31 March -> 28 February)", () => {
    const conf = info({ date_start: "2026-03-31" });
    expect(isArrivalDepartureTentative(conf, day("2026-02-27"))).toBe(true);
    expect(isArrivalDepartureTentative(conf, day("2026-02-28"))).toBe(false);
    expect(isArrivalDepartureTentative(conf, day("2026-03-01"))).toBe(false);
  });

  test("a month-end cutoff clamps in a leap year (31 March -> 29 February)", () => {
    const conf = info({ date_start: "2028-03-31" });
    expect(isArrivalDepartureTentative(conf, day("2028-02-28"))).toBe(true);
    expect(isArrivalDepartureTentative(conf, day("2028-02-29"))).toBe(false);
  });
});
