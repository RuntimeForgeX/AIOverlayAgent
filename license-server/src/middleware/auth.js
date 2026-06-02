function requireAuth(req, res, next) {
  if (!req.session?.userId) {
    return res.redirect("/login");
  }
  next();
}

function attachUser(req, res, next) {
  res.locals.user = req.session.user || null;
  res.locals.isAdmin = req.session.user?.role === "admin";
  res.locals.appName = "AI Overlay License";
  res.locals.baseUrl = process.env.APP_BASE_URL || "";
  next();
}

module.exports = { requireAuth, attachUser };
