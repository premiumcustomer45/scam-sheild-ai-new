import express, { type Express } from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import helmet from "helmet";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();
app.set("trust proxy", 1);

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(helmet());
const allowedOrigins = new Set(
  (process.env.FRONTEND_URL ?? "")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean),
);
app.use((req, res, next) => {
  const origin = req.get("origin");
  if (!origin) {
    next();
    return;
  }
  const protocol = req.get("x-forwarded-proto")?.split(",")[0] ?? req.protocol;
  const host = req.get("x-forwarded-host") ?? req.get("host");
  const sameOrigin = host ? `${protocol}://${host}` : "";
  if (origin !== sameOrigin && !allowedOrigins.has(origin)) {
    res.status(403).json({ error: "Origin is not allowed." });
    return;
  }
  cors({ origin, credentials: true })(req, res, next);
});
app.use(express.json({ limit: "64kb" }));
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

app.use("/api", router);

app.use(
  (
    error: unknown,
    req: express.Request,
    res: express.Response,
    _next: express.NextFunction,
  ) => {
    req.log.error({ err: error }, "Unhandled API error");
    res.status(500).json({ error: "An unexpected server error occurred." });
  },
);

export default app;
