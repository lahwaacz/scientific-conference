import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const script = join(process.cwd(), "docker-entrypoint.d", "20-app-config.sh");

function runEntrypoint(env) {
  const directory = mkdtempSync(join(tmpdir(), "app-config-"));
  const output = join(directory, "app-config.js");
  try {
    execFileSync("sh", [script], {
      env: { ...process.env, ...env, APP_CONFIG_OUTPUT: output },
      stdio: "pipe",
    });
    return readFileSync(output, "utf8");
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

describe("app-config entrypoint", () => {
  test("writes the base path and defaults the API base", () => {
    const config = runEntrypoint({ BASE_PATH: "/conference/" });
    expect(config).toContain('basePath: "/conference/"');
    expect(config).toContain('apiBase: "/conference"');
  });

  test("accepts an explicit safe API base", () => {
    const config = runEntrypoint({
      BASE_PATH: "/conference",
      API_BASE: "https://api.example.com/base/",
    });
    expect(config).toContain('apiBase: "https://api.example.com/base"');
  });

  test.each([
    ["API_BASE", '";alert(1);//'],
    ["BASE_PATH", '/conference";alert(1);//'],
    ["API_BASE", "https://example.com/\nalert(1)"],
  ])("rejects an unsafe %s value", (name, value) => {
    expect(() =>
      runEntrypoint({ BASE_PATH: "/conference", [name]: value })
    ).toThrow();
  });
});
