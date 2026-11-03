#!/usr/bin/env node
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
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
const fs = require("fs");
const path = require("path");

async function generate() {
  const repoRoot = path.resolve(__dirname, "..");
  const playwrightPath = path.join(repoRoot, "frontend", "node_modules", "playwright");
  const { chromium } = require(playwrightPath);

  const svgPath = path.join(repoRoot, "frontend", "assets", "icon.svg");
  const svgContent = fs.readFileSync(svgPath, "utf8");
  const cleanSvg = svgContent.replace(/<!--[\s\S]*?-->/g, "").trim();

  const browser = await chromium.launch({ headless: true });

  // 1. Generate 1024x1024 AppIcon for iOS
  console.log("Generating iOS AppIcon (1024x1024)...");
  const iconPage = await browser.newPage({
    viewport: { width: 1024, height: 1024, deviceScaleFactor: 1 },
  });

  const iconHtml = `<!DOCTYPE html>
  <html>
  <head>
    <style>
      body {
        margin: 0;
        padding: 0;
        width: 1024px;
        height: 1024px;
        background: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      svg {
        width: 720px;
        height: 720px;
      }
    </style>
  </head>
  <body>
    ${cleanSvg}
  </body>
  </html>`;

  await iconPage.setContent(iconHtml);
  const iconDest = path.join(
    repoRoot,
    "frontend",
    "ios",
    "App",
    "App",
    "Assets.xcassets",
    "AppIcon.appiconset",
    "AppIcon-512@2x.png"
  );
  await iconPage.screenshot({ path: iconDest, type: "png" });
  await iconPage.close();
  console.log(`Saved AppIcon to ${iconDest}`);

  // 2. Generate 2732x2732 Splash screen for iOS
  console.log("Generating iOS Splash screen (2732x2732)...");
  const splashPage = await browser.newPage({
    viewport: { width: 2732, height: 2732, deviceScaleFactor: 1 },
  });

  const splashHtml = `<!DOCTYPE html>
  <html>
  <head>
    <style>
      body {
        margin: 0;
        padding: 0;
        width: 2732px;
        height: 2732px;
        background: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      svg {
        width: 800px;
        height: 800px;
      }
    </style>
  </head>
  <body>
    ${cleanSvg}
  </body>
  </html>`;

  await splashPage.setContent(splashHtml);
  const splashDir = path.join(
    repoRoot,
    "frontend",
    "ios",
    "App",
    "App",
    "Assets.xcassets",
    "Splash.imageset"
  );

  const splashTargets = [
    "splash-2732x2732.png",
    "splash-2732x2732-1.png",
    "splash-2732x2732-2.png",
  ];

  for (const target of splashTargets) {
    const dest = path.join(splashDir, target);
    await splashPage.screenshot({ path: dest, type: "png" });
    console.log(`Saved Splash to ${dest}`);
  }
  await splashPage.close();

  await browser.close();
  console.log("iOS asset generation completed successfully.");
}

generate().catch(err => {
  console.error("Failed to generate iOS assets:", err);
  process.exit(1);
});
