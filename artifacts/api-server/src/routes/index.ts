import { Router, type IRouter } from "express";
import authRouter from "./auth";
import dashboardRouter from "./dashboard";
import feedbackRouter from "./feedback";
import healthRouter from "./health";
import scansRouter from "./scans";

const router: IRouter = Router();

router.use(healthRouter);
router.use(authRouter);
router.use(scansRouter);
router.use(dashboardRouter);
router.use(feedbackRouter);

export default router;
