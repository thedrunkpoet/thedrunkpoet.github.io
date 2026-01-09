const fs = require('fs');
const path = require('path');
const showdown = require('showdown');

// Initialize Showdown converter
const converter = new showdown.Converter();

// Directory paths
const postsDir = path.join(__dirname, '_posts');
const outputDir = path.join(__dirname, '_site');
const mainPagePath = path.join(__dirname, 'index.html');

// Ensure the output directory exists
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir);
}

// Function to convert Markdown to HTML
function convertMarkdownToHtml() {
  const files = fs.readdirSync(postsDir);

  files.forEach(file => {
    if (path.extname(file) === '.md') {
      const filePath = path.join(postsDir, file);
      const markdownContent = fs.readFileSync(filePath, 'utf8');
      const htmlContent = converter.makeHtml(markdownContent);

      const outputFileName = path.basename(file, '.md') + '.html';
      const outputFilePath = path.join(outputDir, outputFileName);

      fs.writeFileSync(outputFilePath, htmlContent, 'utf8');
      console.log(`Converted ${file} to ${outputFileName}`);
    }
  });
}

// Function to update the main page
function updateMainPage() {
  const files = fs.readdirSync(outputDir);
  let mainPageContent = '<html><head><title>My Blog</title></head><body><h1>Blog Posts</h1><ul>';

  files.forEach(file => {
    if (path.extname(file) === '.html') {
      const fileName = path.basename(file, '.html');
      mainPageContent += `<li><a href="_site/${file}">${fileName}</a></li>`;
    }
  });

  mainPageContent += '</ul></body></html>';
  fs.writeFileSync(mainPagePath, mainPageContent, 'utf8');
  console.log('Updated main page');
}

// Run the conversion and update process
convertMarkdownToHtml();
updateMainPage();