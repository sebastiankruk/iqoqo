const fs = require('fs');
const path = require('path');

function walk(dir, callback) {
  fs.readdirSync(dir).forEach(file => {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      walk(fullPath, callback);
    } else {
      if (fullPath.endsWith('.tsx') || fullPath.endsWith('.ts')) {
        callback(fullPath);
      }
    }
  });
}

let modifiedCount = 0;

walk('./frontend', (file) => {
  let content = fs.readFileSync(file, 'utf8');
  let originalContent = content;

  // Replace /manifestation/${id} to /manifestation?id=${id}
  content = content.replace(/\/manifestation\/\$\{([^}]+)\}/g, '/manifestation?id=${$1}');
  
  // Replace /manifestation/" + id to /manifestation?id=" + id
  content = content.replace(/\/manifestation\/"\s*\+\s*([a-zA-Z0-9_.]+)/g, '/manifestation?id=" + $1');

  // Replace href={`/manifestation/${id}`} to href={`/manifestation?id=${id}`}
  content = content.replace(/href=\{`\/manifestation\/\$\{([^}]+)\}`\}/g, 'href={`/manifestation?id=${$1}`}');

  // Item links
  content = content.replace(/\/item\/\$\{([^}]+)\}/g, '/item?id=${$1}');
  content = content.replace(/\/item\/"\s*\+\s*([a-zA-Z0-9_.]+)/g, '/item?id=" + $1');
  content = content.replace(/href=\{`\/item\/\$\{([^}]+)\}`\}/g, 'href={`/item?id=${$1}`}');

  if (content !== originalContent) {
    fs.writeFileSync(file, content, 'utf8');
    modifiedCount++;
    console.log(`Modified ${file}`);
  }
});

console.log(`Modified ${modifiedCount} files.`);
