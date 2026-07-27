const puppeteer = require('puppeteer');

const GIST_ID = 'ffd69254e5dea5892b2d38f1a7edb63f';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

async function updateGist(newDomain) {
  console.log(`[GIST] Đang cập nhật Gist với domain mới: ${newDomain}`);
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
    console.log('[GIST] Cập nhật Gist thành công!');
  } else {
    console.error('[GIST] Lỗi khi cập nhật Gist:', await response.text());
  }
}

(async () => {
  console.log('[BROWSER] Đang khởi động trình duyệt...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--lang=vi-VN,vi'
    ]
  });

  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36');
  await page.setViewport({ width: 1920, height: 1080 });

  try {
    const keyword = 'javhdz';
    // Sử dụng DuckDuckGo thay vì Google để tránh bị chặn bot
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(keyword)}`;
    
    console.log(`[SEARCH] Đang truy cập DuckDuckGo: ${searchUrl}`);
    await page.goto(searchUrl, { waitUntil: 'networkidle2', timeout: 60000 });

    console.log('[SEARCH] Đang tìm kết quả đầu tiên...');
    // DuckDuckGo bản HTML thuần có cấu trúc link kết quả rất chuẩn và ổn định
    await page.waitForSelector('.result__url', { timeout: 30000 });

    const firstResultUrl = await page.evaluate(() => {
      const firstLink = document.querySelector('.result__url');
      if (firstLink) {
        let href = firstLink.innerText.trim();
        // Thêm https:// nếu chưa có
        if (!href.startsWith('http')) {
          href = 'https://' + href;
        }
        return href;
      }
      return null;
    });

    if (firstResultUrl) {
      const urlObj = new URL(firstResultUrl);
      const domainOnly = `${urlObj.protocol}//${urlObj.hostname}`;
      
      console.log(`[SUCCESS] Tìm thấy trang web đầu tiên: ${firstResultUrl}`);
      console.log(`[SUCCESS] Domain trích xuất: ${domainOnly}`);

      // Ghi lên Gist
      await updateGist(domainOnly);
    } else {
      console.log('[WARNING] Không tìm thấy link kết quả trên DuckDuckGo.');
    }

  } catch (error) {
    console.error('[ERROR] Đã xảy ra lỗi:', error.message);
  } finally {
    await browser.close();
    console.log('[BROWSER] Đã đóng trình duyệt.');
  }
})();
