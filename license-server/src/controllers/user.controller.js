const { prisma } = require("../config/database");
const { flash, isValidPlan, sanitizeString } = require("../utils/helpers");

async function dashboard(req, res) {
  const userId = req.session.userId;
  const [licenses, requests] = await Promise.all([
    prisma.license.findMany({
      where: { userId },
      include: { devices: true },
      orderBy: { issuedAt: "desc" },
    }),
    prisma.keyRequest.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
      take: 20,
    }),
  ]);

  res.render("dashboard", {
    title: "Dashboard",
    licenses,
    requests,
  });
}

async function requestLicense(req, res) {
  const plan = sanitizeString(req.body.plan, 20);
  const notes = sanitizeString(req.body.notes, 500);

  if (!isValidPlan(plan)) {
    flash(req, "error", "Invalid plan selected.");
    return res.redirect("/dashboard");
  }

  await prisma.keyRequest.create({
    data: {
      userId: req.session.userId,
      plan,
      notes: notes || null,
      status: "pending",
    },
  });

  flash(req, "success", "License request submitted. An admin will review it.");
  res.redirect("/dashboard");
}

module.exports = { dashboard, requestLicense };
