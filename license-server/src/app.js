require("dotenv").config();

const path = require("path");
const express = require("express");
const session = require("express-session");
const helmet = require("helmet");
const cors = require("cors");
const pgSession = require("connect-pg-simple")(session);

const { attachUser } = require("./middleware/auth");
const { getFlash, formatDate } = require("./utils/helpers");

const authRoutes = require("./routes/auth.routes");
const userRoutes = require("./routes/user.routes");
const adminRoutes = require("./routes/admin.routes");
const apiRoutes = require("./routes/api.routes");

const app = express();

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.set("trust proxy", 1);

app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        scriptSrc: ["'self'", "https://cdn.jsdelivr.net"],
        fontSrc: ["'self'", "https://cdn.jsdelivr.net"],
        imgSrc: ["'self'", "data:"],
      },
    },
  })
);

app.use(
  cors({
    origin: false,
  })
);

app.use(express.urlencoded({ extended: true }));
app.use(express.json({ limit: "32kb" }));

function buildSessionStore() {
  if (process.env.USE_MEMORY_SESSION === "1") {
    return undefined;
  }
  if (!process.env.DATABASE_URL) {
    return undefined;
  }
  return new pgSession({
    conString: process.env.DATABASE_URL,
    tableName: "session",
    createTableIfMissing: true,
  });
}

app.use(
  session({
    store: buildSessionStore(),
    secret: process.env.SESSION_SECRET || "dev-secret-change-me",
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      maxAge: 7 * 24 * 60 * 60 * 1000,
    },
  })
);

app.use(attachUser);
app.use((req, res, next) => {
  res.locals.flash = getFlash(req);
  res.locals.formatDate = formatDate;
  res.locals.lastIssuedJwt = req.session.lastIssuedJwt || null;
  next();
});

app.use(express.static(path.join(__dirname, "public")));

app.get("/", (req, res) => {
  if (req.session.userId) {
    return res.redirect(
      req.session.user?.role === "admin" ? "/admin" : "/dashboard"
    );
  }
  res.redirect("/login");
});

app.get("/request", (req, res) => {
  if (req.session.userId) {
    return res.redirect("/dashboard");
  }
  res.redirect("/register");
});

app.use(authRoutes);
app.use(userRoutes);
app.use(adminRoutes);
app.use("/api", apiRoutes);

app.use((req, res) => {
  res.status(404).render("error", {
    title: "Not Found",
    message: "Page not found.",
  });
});

app.use((err, req, res, _next) => {
  console.error(err);
  res.status(500).render("error", {
    title: "Error",
    message: process.env.NODE_ENV === "development" ? err.message : "Server error.",
  });
});

module.exports = app;
