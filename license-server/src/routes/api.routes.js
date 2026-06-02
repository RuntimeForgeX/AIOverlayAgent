const express = require("express");
const rateLimit = require("express-rate-limit");
const api = require("../controllers/api.controller");
const { asyncHandler } = require("../utils/asyncHandler");

const router = express.Router();

const activateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 30,
  message: { error: "Too many activation attempts. Try again later." },
  standardHeaders: true,
  legacyHeaders: false,
});

router.post("/activate", activateLimiter, asyncHandler(api.activate));

module.exports = router;
