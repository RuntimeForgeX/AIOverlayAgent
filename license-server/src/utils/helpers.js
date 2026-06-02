const validator = require("validator");

const PLANS = ["15days", "30days", "lifetime"];

function sanitizeString(value, maxLen = 500) {
  if (value == null) return "";
  return String(value).trim().slice(0, maxLen);
}

function isValidPlan(plan) {
  return PLANS.includes(plan);
}

function isValidEmail(email) {
  return validator.isEmail(email || "");
}

function flash(req, type, message) {
  req.session.flash = { type, message };
}

function getFlash(req) {
  const f = req.session.flash;
  delete req.session.flash;
  return f;
}

function formatDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleString();
}

module.exports = {
  PLANS,
  sanitizeString,
  isValidPlan,
  isValidEmail,
  flash,
  getFlash,
  formatDate,
};
