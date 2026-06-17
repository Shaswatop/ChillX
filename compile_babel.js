const fs = require('fs');
const babel = require('@babel/core');

function compileFile(htmlPath, outputPath) {
  const html = fs.readFileSync(htmlPath, 'utf8');
  const vs = '{% verbatim %}';
  const ve = '{% endverbatim %}';

  let si = html.indexOf(vs);
  let ei = html.indexOf(ve);
  let jsx;

  if (si !== -1 && ei !== -1) {
    let inner = html.substring(si + vs.length, ei);
    const sm = '<script type="text/babel">';
    const em = '</script>';
    let ssi = inner.indexOf(sm);
    let eei = inner.indexOf(em);
    if (ssi !== -1 && eei !== -1) {
      jsx = inner.substring(ssi + sm.length, eei);
    }
  } else {
    const sm = '<script type="text/babel">';
    const em = '</script>';
    let ssi = html.indexOf(sm);
    let eei = html.indexOf(em, ssi);
    if (ssi !== -1 && eei !== -1) {
      jsx = html.substring(ssi + sm.length, eei);
    }
  }

  if (!jsx) { console.log(htmlPath + ': no babel script found'); return false; }

  console.log(htmlPath + ': ' + jsx.length + ' JSX chars');

  try {
    const result = babel.transformSync(jsx, {
      presets: [['@babel/preset-react', { runtime: 'classic' }]],
    });
    fs.writeFileSync(outputPath, result.code);
    console.log('  -> ' + outputPath + ' (' + result.code.length + ' chars)');
    return true;
  } catch(e) {
    console.log('  ERROR: ' + e.message.substring(0, 300));
    return false;
  }
}

function updateHtml(htmlPath) {
  let html = fs.readFileSync(htmlPath, 'utf8');

  // Remove CDN babel script
  const babelCDN = '<script crossorigin src="https://unpkg.com/@babel/standalone/babel.min.js"></script>';
  html = html.replace(babelCDN, '');

  // Replace verbatim block with compiled script
  const vs = '{% verbatim %}';
  const ve = '{% endverbatim %}';
  let si = html.indexOf(vs);
  let ei = html.indexOf(ve);
  if (si !== -1 && ei !== -1) {
    let inner = html.substring(si + vs.length, ei);
    const sm = '<script type="text/babel">';
    const em = '</script>';
    let ssi = inner.indexOf(sm);
    let eei = inner.indexOf(em);
    if (ssi !== -1 && eei !== -1) {
      const fileName = htmlPath.replace(/^.*[\\/]/, '').replace('.html', '') + '.js';
      const compiledTag = '<script src="/static/js/' + fileName + '"></script>';
      html = html.substring(0, si) + compiledTag + html.substring(ei + ve.length);
      fs.writeFileSync(htmlPath, html);
      console.log('  -> Updated ' + htmlPath);
      return true;
    }
  }
  return false;
}

const shopPath = 'templates/dashboard/shop.html';
const invPath = 'templates/dashboard/inventory.html';

if (compileFile(shopPath, 'static/js/shop.js')) {
  updateHtml(shopPath);
}
if (compileFile(invPath, 'static/js/inventory.js')) {
  updateHtml(invPath);
}
