const fs = require('fs');
const babel = require('@babel/core');

const htmlPath = 'templates/dashboard/shop.html';
const outputPath = 'static/js/shop.js';

let html = fs.readFileSync(htmlPath, 'utf8');

// Structure: {% verbatim %}<script type="text/babel">\n...JSX...\n{% endverbatim %}</script>
// verbatim/endverbatim are on SAME line as script tags

const vs = '{% verbatim %}';
const ve = '{% endverbatim %}';
const scriptStart = '<script type="text/babel">';
const scriptEnd = '</script>';

const si = html.indexOf(vs);
const ei = html.indexOf(ve);
if (si === -1 || ei === -1) { console.error('No verbatim block'); process.exit(1); }

// JSX content is between opening script tag and {% endverbatim %}
const jsxStart = si + vs.length + html.substring(si + vs.length, ei).indexOf(scriptStart) + scriptStart.length;
const jsxEnd = ei;
let jsx = html.substring(jsxStart, jsxEnd).trim();
console.log('JSX length:', jsx.length);

// Compile
const result = babel.transformSync(jsx, {
  presets: [['@babel/preset-react', { runtime: 'classic' }]],
});
fs.writeFileSync(outputPath, result.code);
console.log('Compiled -> ' + outputPath + ' (' + result.code.length + ' chars)');

// Find closing </script> after {% endverbatim %}
const eei = html.indexOf(scriptEnd, ei + ve.length);
if (eei === -1) { console.error('No closing script tag'); process.exit(1); }

// Replace from {% verbatim %} to </script> (inclusive) with compiled script tag
const before = html.substring(0, si);
const after = html.substring(eei + scriptEnd.length);
const newHtml = before + '<script src="/static/js/shop.js"></script>' + after;

// Remove babel CDN
const babelCDN = '<script crossorigin src="https://unpkg.com/@babel/standalone/babel.min.js"></script>';
const cleanHtml = newHtml.replace(babelCDN, '');

fs.writeFileSync(htmlPath, cleanHtml);
console.log('DONE');
