// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");

const routesToPatch = [
  path.join(frontendDir, "app/api/auth-exchange/route.ts"),
  path.join(frontendDir, "app/auth/exchange/route.ts"),
  path.join(frontendDir, "app/api/auth/logout/route.ts"),
];

function restoreRoutes() {
  console.log("⚡ Restoring routes to force-dynamic...");
  for (const file of routesToPatch) {
    if (fs.existsSync(file)) {
      let content = fs.readFileSync(file, "utf8");
      content = content.replace(/export const dynamic = "force-static";/g, 'export const dynamic = "force-dynamic";');
      fs.writeFileSync(file, content, "utf8");
    }
  }
}

process.on("SIGINT", () => {
  restoreRoutes();
  process.exit(130);
});

process.on("SIGTERM", () => {
  restoreRoutes();
  process.exit(143);
});

console.log("⚡ Preparing Capacitor static export (toggling routes to force-static)...");
for (const file of routesToPatch) {
  if (fs.existsSync(file)) {
    let content = fs.readFileSync(file, "utf8");
    content = content.replace(/export const dynamic = "force-dynamic";/g, 'export const dynamic = "force-static";');
    fs.writeFileSync(file, content, "utf8");
  }
}

let buildError = null;
try {
  execSync("npx next build", {
    cwd: frontendDir,
    stdio: "inherit",
    env: {
      ...process.env,
      CAPACITOR_BUILD: "true",
      NEXT_PUBLIC_FRONTEND_URL: process.env.NEXT_PUBLIC_FRONTEND_URL || "https://iqoqo.cc",
    },
  });
} catch (err) {
  buildError = err;
} finally {
  restoreRoutes();
}

if (buildError) {
  process.exit(1);
}
