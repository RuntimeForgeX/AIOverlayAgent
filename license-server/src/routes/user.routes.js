const express = require("express");
const user = require("../controllers/user.controller");
const { requireAuth } = require("../middleware/auth");
const { asyncHandler } = require("../utils/asyncHandler");

const router = express.Router();

router.get("/dashboard", requireAuth, asyncHandler(user.dashboard));
router.post("/request-license", requireAuth, asyncHandler(user.requestLicense));

module.exports = router;
