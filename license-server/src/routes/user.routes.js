const express = require("express");
const user = require("../controllers/user.controller");
const { requireAuth } = require("../middleware/auth");

const router = express.Router();

router.get("/dashboard", requireAuth, user.dashboard);
router.post("/request-license", requireAuth, user.requestLicense);

module.exports = router;
