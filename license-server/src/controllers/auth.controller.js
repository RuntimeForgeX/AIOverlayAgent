const bcrypt = require("bcryptjs");
const { prisma } = require("../config/database");
const { flash, isValidEmail, sanitizeString } = require("../utils/helpers");

async function showLogin(req, res) {
  res.render("login", { title: "Login", error: null });
}

async function showRegister(req, res) {
  res.render("register", { title: "Register", error: null });
}

async function register(req, res) {
  const email = sanitizeString(req.body.email, 120).toLowerCase();
  const name = sanitizeString(req.body.name, 80);
  const password = req.body.password || "";

  if (!isValidEmail(email)) {
    return res.render("register", { title: "Register", error: "Invalid email." });
  }
  if (password.length < 8) {
    return res.render("register", {
      title: "Register",
      error: "Password must be at least 8 characters.",
    });
  }

  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) {
    return res.render("register", {
      title: "Register",
      error: "Email already registered.",
    });
  }

  const hash = await bcrypt.hash(password, 12);
  const user = await prisma.user.create({
    data: { email, name: name || null, password: hash, role: "user" },
  });

  req.session.userId = user.id;
  req.session.user = { id: user.id, email: user.email, name: user.name, role: user.role };
  flash(req, "success", "Account created. Request a license from your dashboard.");
  res.redirect("/dashboard");
}

async function login(req, res) {
  const email = sanitizeString(req.body.email, 120).toLowerCase();
  const password = req.body.password || "";

  const user = await prisma.user.findUnique({ where: { email } });
  if (!user || !(await bcrypt.compare(password, user.password))) {
    return res.render("login", { title: "Login", error: "Invalid email or password." });
  }

  req.session.userId = user.id;
  req.session.user = {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
  };
  res.redirect(user.role === "admin" ? "/admin" : "/dashboard");
}

function logout(req, res) {
  req.session.destroy(() => {
    res.redirect("/login");
  });
}

module.exports = {
  showLogin,
  showRegister,
  register,
  login,
  logout,
};
