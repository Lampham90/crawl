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

    // Đợi trang load các khối kết quả
    await page.waitForSelector('.result', { timeout: 30000 });

    // Quét toàn bộ các thẻ a có trên trang để tìm link chứa từ khóa
    const validUrl = await page.evaluate(() => {
      const links = document.querySelectorAll('a');
      for (let a of links) {
        let href = a.href || '';
        
        // Giải mã link chuyển hướng của DuckDuckGo nếu có
        if (href.includes('duckduckgo.com/l/?uddg=')) {
          try {
            const urlParams = new URLSearchParams(new URL(href).search);
            const targetUrl = urlParams.get('uddg');
            if (targetUrl) {
              href = decodeURIComponent(targetUrl);
            }
          } catch (e) {}
        }

        try {
          const urlObj = new URL(href);
          // Lọc chính xác domain chứa từ khóa "javhdz" và bỏ qua các link rác của chính duckduckgo
          if (urlObj.hostname.includes('javhdz') && !urlObj.hostname.includes('duckduckgo')) {
            return `${urlObj.protocol}//${urlObj.hostname}`;
          }
        } catch (e) {}
      }
      return null;
    });

    if (validUrl) {
      console.log(`[SUCCESS] Đã tìm và lọc được domain chuẩn: ${validUrl}`);
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
