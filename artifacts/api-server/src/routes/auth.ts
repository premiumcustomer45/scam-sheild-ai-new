import bcrypt from "bcryptjs";
import { Router, type IRouter } from "express";
import { rateLimit } from "express-rate-limit";
import { eq } from "drizzle-orm";
import {
  LoginBody,
  LoginResponse,
  LogoutResponse,
  RegisterBody,
  RegisterResponse,
  GetCurrentUserResponse,
} from "@workspace/api-zod";
import { db, usersTable } from "@workspace/db";
import { clearSessionCookie, getSessionUser, setSessionCookie, toPublicUser } from "../lib/auth";

const router: IRouter = Router();
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 8,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many sign-in attempts. Try again later." },
});
const registerLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  limit: 5,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many account creation attempts. Try again later." },
});

function isUniqueViolation(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    error.code === "23505"
  );
}

router.post("/auth/register", registerLimiter, async (req, res): Promise<void> => {
  const input = RegisterBody.safeParse(req.body);
  if (!input.success) {
    res.status(400).json({ error: "Enter a name, valid email, and password of at least 10 characters." });
    return;
  }

  const name = input.data.name.trim();
  const email = input.data.email.trim().toLowerCase();
  if (!name) {
    res.status(400).json({ error: "Name is required." });
    return;
  }

  const passwordHash = await bcrypt.hash(input.data.password, 12);
  try {
    const [user] = await db
      .insert(usersTable)
      .values({ name, email, passwordHash })
      .returning();
    setSessionCookie(res, user.id);
    res.status(201).json(RegisterResponse.parse({ user: toPublicUser(user) }));
  } catch (error) {
    if (isUniqueViolation(error)) {
      res.status(409).json({ error: "An account with that email already exists." });
      return;
    }
    req.log.error({ err: error }, "Account registration failed");
    res.status(500).json({ error: "Could not create the account." });
  }
});

router.post("/auth/login", loginLimiter, async (req, res): Promise<void> => {
  const input = LoginBody.safeParse(req.body);
  if (!input.success) {
    res.status(400).json({ error: "Enter a valid email and password." });
    return;
  }
  const email = input.data.email.trim().toLowerCase();
  const [user] = await db.select().from(usersTable).where(eq(usersTable.email, email)).limit(1);
  const validPassword = user
    ? await bcrypt.compare(input.data.password, user.passwordHash)
    : false;
  if (!user || !validPassword) {
    res.status(401).json({ error: "Email or password is incorrect." });
    return;
  }
  setSessionCookie(res, user.id);
  res.json(LoginResponse.parse({ user: toPublicUser(user) }));
});

router.post("/auth/logout", (_req, res): void => {
  clearSessionCookie(res);
  res.json(LogoutResponse.parse({ success: true }));
});

router.get("/auth/me", async (req, res): Promise<void> => {
  try {
    const user = await getSessionUser(req);
    res.json(
      GetCurrentUserResponse.parse({
        user: user ? toPublicUser(user) : null,
      }),
    );
  } catch (error) {
    req.log.error({ err: error }, "Session lookup failed");
    res.status(500).json({ error: "Could not load the current session." });
  }
});

export default router;
