require("dotenv").config();

const path = require("path");
const express = require("express");
const ejs = require("ejs");
const session = require("express-session");
const helmet = require("helmet");
const cors = require("cors");
const { Pool } = require("pg");
const pgSession = require("connect-pg-simple")(session);

const { attachUser } = require("./middleware/auth");
const { getFlash, formatDate } = require("./utils/helpers");

const authRoutes = require("./routes/auth.routes");
const userRoutes = require("./routes/user.routes");
const adminRoutes = require("./routes/admin.routes");
const apiRoutes = require("./routes/api.routes");

const app = express();
const viewsPath = path.join(__dirname, "views");

app.set("view engine", "ejs");
app.set("views", viewsPath);
app.set("trust proxy", 1);

// Resolve includes from views root (fixes partials in admin/* templates).
app.engine(
  "ejs",
  (filePath, options, callback) => {
    ejs.renderFile(
      filePath,
      options,
      { root: viewsPath, views: [viewsPath], filename: filePath },
      callback
    );
  }
);

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

  const dbUrl = new URL(process.env.DATABASE_URL);
  const sslmode = dbUrl.searchParams.get("sslmode");
  const sslaccept = dbUrl.searchParams.get("sslaccept");
  const ssl =
    sslmode && sslmode !== "disable"
      ? { rejectUnauthorized: sslaccept !== "accept_invalid_certs" }
      : undefined;
  dbUrl.searchParams.delete("sslmode");
  dbUrl.searchParams.delete("sslaccept");
  dbUrl.searchParams.delete("sslcert");
  dbUrl.searchParams.delete("sslrootcert");

  return new pgSession({
    pool: new Pool({
      connectionString: dbUrl.toString(),
      ssl,
      max: 2,
    }),
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
  res.locals.currentPath = req.path;
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
  const code = err.code || "";
  const isDb =
    code.startsWith("P") ||
    /database|prisma|ECONNREFUSED|Can't reach database|certificate|SSL/i.test(
      err.message || ""
    );
  const message = isDb
    ? "Database connection failed. Check DATABASE_URL in .env, verify the database is running/reachable, or run local Postgres: docker compose up -d"
    : process.env.NODE_ENV === "development"
      ? err.message
      : "Server error.";
  res.status(500).render("error", { title: "Error", message });
});

module.exports = app;
