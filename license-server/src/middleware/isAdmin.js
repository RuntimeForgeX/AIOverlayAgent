function requireAdmin(req, res, next) {
  if (!req.session?.userId) {
    return res.redirect("/login");
  }
  if (req.session.user?.role !== "admin") {
    return res.status(403).render("error", {
      title: "Forbidden",
      message: "Admin access required.",
    });
  }
  next();
}

module.exports = { requireAdmin };
