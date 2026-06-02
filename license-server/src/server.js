const app = require("./app");

const PORT = parseInt(process.env.PORT || "3000", 10);

app.listen(PORT, () => {
  console.log(`License server running at http://localhost:${PORT}`);
  console.log(`  Login:     http://localhost:${PORT}/login`);
  console.log(`  Register:  http://localhost:${PORT}/register`);
  console.log(`  Activate:  POST http://localhost:${PORT}/api/activate`);
});
