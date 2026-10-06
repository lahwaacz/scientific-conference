import { registrationWindowStatus } from "./registrationWindow";

const info = (overrides = {}) => ({
  registration_opening: null,
  registration_deadline: null,
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

  test("a past conference is closed even without a deadline", () => {
    const conf = info({ date_end: "2026-05-31" });
    expect(registrationWindowStatus(conf, day("2026-05-31"))).toBe("open");
    expect(registrationWindowStatus(conf, day("2026-06-01"))).toBe("closed");
  });

  test("a past conference stays closed even with a future deadline", () => {
    const conf = info({
      date_end: "2026-05-31",
      registration_deadline: "2030-01-01",
    });
    expect(registrationWindowStatus(conf, day("2026-06-01"))).toBe("closed");
  });
});
