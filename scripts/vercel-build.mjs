// Builds the app into Vercel's Build Output API layout (.vercel/output):
//   static/            React + Vite frontend
//   functions/api.func Express API bundled into a single Node.js function
// Vercel serves this output as-is, so the frontend and /api share one origin
// and the session cookie works without extra CORS configuration.
import { spawnSync } from "node:child_process";
import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputDir = path.join(root, ".vercel/output");
const frontendDir = path.join(root, "artifacts/scamshield-ai");
const apiDir = path.join(root, "artifacts/api-server");
const functionDir = path.join(outputDir, "functions/api.func");

function pnpm(args, options = {}) {
  // npm_execpath points at the pnpm that invoked this script.
  const pnpmBin = process.env.npm_execpath;
  const [command, commandArgs] = pnpmBin
    ? [process.execPath, [pnpmBin, ...args]]
    : ["pnpm", args];
  return spawnSync(command, commandArgs, {
    cwd: root,
    stdio: "inherit",
    shell: !pnpmBin && process.platform === "win32",
    ...options,
  });
}

function pushDatabaseSchema() {
  if (!(process.env.DATABASE_URL || process.env.POSTGRES_URL) || process.env.SKIP_DB_PUSH) {
    console.log("Skipping database schema push (DATABASE_URL not set).");
    return;
  }
  console.log("Pushing database schema with drizzle-kit...");
  const result = pnpm(["--filter", "@workspace/db", "run", "push"], {
    stdio: ["ignore", "inherit", "inherit"],
    timeout: 120_000,
  });
  if (result.status !== 0) {
    console.warn(
      "WARNING: database schema push did not complete. Run `pnpm --filter @workspace/db run push` manually.",
    );
  }
}

async function buildFrontend() {
  const result = pnpm(["--filter", "@workspace/scamshield-ai", "run", "build"], {
    env: { ...process.env, NODE_ENV: "production", BASE_PATH: "/" },
  });
  if (result.status !== 0) throw new Error("Frontend build failed.");
  await cp(path.join(frontendDir, "dist/public"), path.join(outputDir, "static"), {
    recursive: true,
  });
}

async function buildApiFunction() {
  const apiRequire = createRequire(path.join(apiDir, "package.json"));
  const { build } = apiRequire("esbuild");

  await build({
    entryPoints: [path.join(apiDir, "src/app.ts")],
    outfile: path.join(functionDir, "index.mjs"),
    platform: "node",
    target: "node22",
    format: "esm",
    bundle: true,
    minify: true,
    sourcemap: false,
    logLevel: "info",
    // pg only loads pg-native when explicitly requested; keep it out of the bundle.
    external: ["pg-native", "pino-pretty"],
    define: { "process.env.NODE_ENV": '"production"' },
    // Bundled CommonJS packages (express, pg, ...) still call require().
    banner: {
      js: `import { createRequire as __bannerCrReq } from 'node:module';
import __bannerPath from 'node:path';
import __bannerUrl from 'node:url';
globalThis.require = __bannerCrReq(import.meta.url);
globalThis.__filename = __bannerUrl.fileURLToPath(import.meta.url);
globalThis.__dirname = __bannerPath.dirname(globalThis.__filename);`,
    },
  });

  await writeFile(
    path.join(functionDir, ".vc-config.json"),
    JSON.stringify(
      {
        runtime: "nodejs22.x",
        handler: "index.mjs",
        launcherType: "Nodejs",
        shouldAddHelpers: false,
        maxDuration: 60,
      },
      null,
      2,
    ),
  );
  await writeFile(
    path.join(functionDir, "package.json"),
    JSON.stringify({ type: "module" }),
  );
}

async function writeRoutes() {
  const config = {
    version: 3,
    routes: [
      {
        src: "^/assets/(.*)$",
        headers: { "cache-control": "public, max-age=31536000, immutable" },
        continue: true,
      },
      {
        src: "^/(?!api(?:/|$)).*$",
        headers: {
          "x-content-type-options": "nosniff",
          "referrer-policy": "strict-origin-when-cross-origin",
          "x-frame-options": "DENY",
        },
        continue: true,
      },
      { handle: "filesystem" },
      { src: "^/api(?:/.*)?$", dest: "/api" },
      // Client-side routing: unknown paths fall back to the SPA shell.
      { src: "^/(.*)$", dest: "/index.html" },
    ],
  };
  await writeFile(path.join(outputDir, "config.json"), JSON.stringify(config, null, 2));
}

await rm(outputDir, { recursive: true, force: true });
await mkdir(functionDir, { recursive: true });
pushDatabaseSchema();
await buildFrontend();
await buildApiFunction();
await writeRoutes();
console.log(`Vercel output written to ${path.relative(root, outputDir)}`);
