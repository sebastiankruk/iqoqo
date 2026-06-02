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

function walk(dir, callback) {
  fs.readdirSync(dir).forEach(file => {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      walk(fullPath, callback);
    } else {
      if (fullPath.endsWith(".tsx") || fullPath.endsWith(".ts")) {
        callback(fullPath);
      }
    }
  });
}

let modifiedCount = 0;

walk("./frontend", file => {
  let content = fs.readFileSync(file, "utf8");
  let originalContent = content;

  // Replace /manifestation/${id} to /manifestation?id=${id}
  content = content.replace(/\/manifestation\/\$\{([^}]+)\}/g, "/manifestation?id=${$1}");

  // Replace /manifestation/" + id to /manifestation?id=" + id
  content = content.replace(/\/manifestation\/"\s*\+\s*([a-zA-Z0-9_.]+)/g, '/manifestation?id=" + $1');

  // Replace href={`/manifestation/${id}`} to href={`/manifestation?id=${id}`}
  content = content.replace(/href=\{`\/manifestation\/\$\{([^}]+)\}`\}/g, "href={`/manifestation?id=${$1}`}");

  // Item links
  content = content.replace(/\/item\/\$\{([^}]+)\}/g, "/item?id=${$1}");
  content = content.replace(/\/item\/"\s*\+\s*([a-zA-Z0-9_.]+)/g, '/item?id=" + $1');
  content = content.replace(/href=\{`\/item\/\$\{([^}]+)\}`\}/g, "href={`/item?id=${$1}`}");

  if (content !== originalContent) {
    fs.writeFileSync(file, content, "utf8");
    modifiedCount++;
    console.log(`Modified ${file}`);
  }
});

console.log(`Modified ${modifiedCount} files.`);
