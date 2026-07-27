const puppeteer = require('puppeteer');

const GIST_ID = 'ffd69254e5dea5892b2d38f1a7edb63f';
// Dùng GitHub Actions API nội bộ, không cần Secret
const GITHUB_TOKEN = process.env.GITHUB_TOKEN; 

async function updateGist(newDomain) {
  const response = await fetch(`https://api.github.com/gists/${GIST_ID}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${GITHUB_TOKEN}`,
      'Accept': 'vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'Node.js-Script'
    },
    body: JSON.stringify({
      files: {
        'domain.txt': {
          content: newDomain
        }
      }
    })
  });

  if (response.ok) {
    console.log('Đã cập nhật Gist thành công với domain:', newDomain);
  } else {
    console.error('Lỗi khi cập nhật Gist:', await response.text());
  }
}

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();

  try {
    // 1. Vào Google Search và tìm từ khóa "javhdz"
    await page.goto('https://www.google.com');
    await page.type('textarea[name="q"]', 'javhdz');
    await page.keyboard.press('Enter');
    await page.waitForSelector('#search');

    // 2. Lấy link kết quả đầu tiên
    const firstResultUrl = await page.evaluate(() => {
      const firstLink = document.querySelector('#search div.g a');
      return firstLink ? firstLink.href : null;
    });

    await browser.close();

    if (firstResultUrl) {
      const urlObj = new URL(firstResultUrl);
      const domainOnly = `${urlObj.protocol}//${urlObj.hostname}`;
      
      console.log('Tìm thấy domain mới:', domainOnly);
      // 3. Đẩy thẳng vào Gist qua API
      await updateGist(domainOnly);
    }
  } catch (error) {
    console.error('Lỗi:', error);
    await browser.close();
  }
})();
