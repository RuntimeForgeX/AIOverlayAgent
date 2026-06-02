const express = require("express");
const auth = require("../controllers/auth.controller");

const router = express.Router();

router.get("/login", auth.showLogin);
router.get("/register", auth.showRegister);
router.post("/register", auth.register);
router.post("/login", auth.login);
router.post("/logout", auth.logout);

module.exports = router;
