const { prisma } = require("../config/database");
const {
  generateRawLicenseJWT,
  newJti,
  planToExpiry,
} = require("../services/jwt.service");
const { flash, sanitizeString } = require("../utils/helpers");

async function dashboard(req, res) {
  const pending = await prisma.keyRequest.findMany({
    where: { status: "pending" },
    include: { user: { select: { email: true, name: true } } },
    orderBy: { createdAt: "asc" },
  });
  const licenses = await prisma.license.findMany({
    include: {
      user: { select: { email: true, name: true } },
      devices: true,
    },
    orderBy: { issuedAt: "desc" },
    take: 50,
  });
  const usersCount = await prisma.user.count();
  const activeLicensesCount = await prisma.license.count({
    where: { revoked: false },
  });
  const pendingRequestsCount = await prisma.keyRequest.count({
    where: { status: "pending" },
  });

  res.render("admin/dashboard", {
    title: "Admin",
    pending,
    licenses,
    stats: {
      users: usersCount,
      activeLicenses: activeLicensesCount,
      pendingRequests: pendingRequestsCount,
    },
  });
}

async function approveRequest(req, res) {
  const requestId = sanitizeString(req.params.id, 40);
  const keyRequest = await prisma.keyRequest.findUnique({
    where: { id: requestId },
    include: { user: true },
  });

  if (!keyRequest || keyRequest.status !== "pending") {
    flash(req, "error", "Request not found or already processed.");
    return res.redirect("/admin");
  }

  const jti = newJti();
  const { expiresAt } = planToExpiry(keyRequest.plan);
  const rawJwt = generateRawLicenseJWT({
    userId: keyRequest.userId,
    plan: keyRequest.plan,
    jti,
  });

  await prisma.$transaction([
    prisma.license.create({
      data: {
        jti,
        userId: keyRequest.userId,
        plan: keyRequest.plan,
        expiresAt,
        rawJwt,
      },
    }),
    prisma.keyRequest.update({
      where: { id: requestId },
      data: { status: "approved" },
    }),
  ]);

  req.session.lastIssuedJwt = rawJwt;
  flash(
    req,
    "success",
    `Approved ${keyRequest.plan} license for ${keyRequest.user.email}. Raw JWT shown below.`
  );
  res.redirect("/admin");
}

async function rejectRequest(req, res) {
  const requestId = sanitizeString(req.params.id, 40);
  await prisma.keyRequest.updateMany({
    where: { id: requestId, status: "pending" },
    data: { status: "rejected" },
  });
  flash(req, "success", "Request rejected.");
  res.redirect("/admin");
}

async function revokeLicense(req, res) {
  const id = sanitizeString(req.params.id, 40);
  await prisma.license.update({
    where: { id },
    data: { revoked: true },
  });
  flash(req, "success", "License revoked.");
  res.redirect("/admin");
}

async function unbindDevice(req, res) {
  const deviceId = sanitizeString(req.params.id, 40);
  await prisma.device.delete({ where: { id: deviceId } });
  flash(req, "success", "Device unbound. User can activate on a new machine.");
  res.redirect("/admin");
}

async function licensesPage(req, res) {
  const licenses = await prisma.license.findMany({
    include: {
      user: { select: { email: true, name: true } },
      devices: true,
    },
    orderBy: { issuedAt: "desc" },
  });
  res.render("admin/licenses", { title: "All Licenses", licenses });
}

module.exports = {
  dashboard,
  approveRequest,
  rejectRequest,
  revokeLicense,
  unbindDevice,
  licensesPage,
};
