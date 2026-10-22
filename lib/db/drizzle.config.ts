import { defineConfig } from "drizzle-kit";

const url = process.env.DATABASE_URL ?? process.env.POSTGRES_URL;
if (!url) {
  throw new Error("DATABASE_URL, ensure the database is provisioned");
}

export default defineConfig({
  // Relative to lib/db (the cwd when run via pnpm); absolute Windows paths
  // break drizzle-kit's schema glob.
  schema: "./src/schema/index.ts",
  dialect: "postgresql",
  dbCredentials: {
    url,
  },
});
