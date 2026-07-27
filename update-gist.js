const puppeteer = require('puppeteer');

const GIST_ID = 'ffd69254e5dea5892b2d38f1a7edb63f';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

async function updateGist(newDomain) {
  console.log(`[GIST] Đang cập nhật Gist với domain mới: ${newDomain}`);
  const response = await fetch(`https://api.github.com/gists/${GIST_ID}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github+json',
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
    console.log('[GIST] Cập nhật Gist thành công!');
  } else {
    console.error('[GIST] Lỗi khi cập nhật Gist:', await response.text());
  }
}

(async () => {
  console.log('[BROWSER] Đang khởi động trình duyệt...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--lang=vi-VN,vi']
  });

  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36');
  await page.setViewport({ width: 1920, height: 1080 });

  try {
    const searchUrl = `https://html.duckduckgo.com/html/?q=javhdz`;
    console.log(`[SEARCH] Đang truy cập: ${searchUrl}`);
    await page.goto(searchUrl, { waitUntil: 'networkidle2', timeout: 60000 });

    await page.waitForSelector('.result__url', { timeout: 30000 });

    // Lọc qua các kết quả để lấy đúng domain chuẩn chứa từ khóa "javhdz"
    const validUrl = await page.evaluate(() => {
      const linkElements = document.querySelectorAll('.result__url');
      for (let el of linkElements) {
        let href = el.innerText.trim();
        if (!href.startsWith('http')) {
          href = 'https://' + href;
        }
        
        try {
          const urlObj = new URL(href);
          // Bắt buộc domain phải chứa chữ "javhdz" để loại bỏ các trang tào lao
          if (urlObj.hostname.includes('javhdz')) {
            return `${urlObj.protocol}//${urlObj.hostname}`;
          }
        } catch (e) {}
      }
      return null;
    });

    if (validUrl) {
      console.log(`[SUCCESS] Đã lọc và tìm thấy domain chuẩn: ${validUrl}`);
      await updateGist(validUrl);
    } else {
      console.log('[WARNING] Không tìm thấy domain hợp lệ chứa từ khóa javhdz.');
    }

  } catch (error) {
    console.error('[ERROR] Lỗi:', error.message);
  } finally {
    await browser.close();
    console.log('[BROWSER] Đã đóng trình duyệt.');
  }
})();
