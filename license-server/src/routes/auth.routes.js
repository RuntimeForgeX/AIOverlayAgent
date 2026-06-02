const express = require("express");
const auth = require("../controllers/auth.controller");
const { asyncHandler } = require("../utils/asyncHandler");

const router = express.Router();

router.get("/login", auth.showLogin);
router.get("/register", auth.showRegister);
router.post("/register", asyncHandler(auth.register));
router.post("/login", asyncHandler(auth.login));
router.post("/logout", auth.logout);

module.exports = router;
