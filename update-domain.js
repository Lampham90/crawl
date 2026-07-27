const puppeteer = require('puppeteer');
const fs = require('fs');

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

    const firstResultUrl = await page.evaluate(() => {
      const firstLink = document.querySelector('.result__url');
      if (firstLink) {
        let href = firstLink.innerText.trim();
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
      
      console.log(`[SUCCESS] Tìm thấy domain: ${domainOnly}`);

      // Ghi đè trực tiếp vào file domain.txt trong repo
      fs.writeFileSync('domain.txt', domainOnly, 'utf8');
      console.log('[FILE] Đã ghi thành công vào domain.txt');
    } else {
      console.log('[WARNING] Không tìm thấy kết quả.');
    }

  } catch (error) {
    console.error('[ERROR] Lỗi:', error.message);
  } finally {
    await browser.close();
    console.log('[BROWSER] Đã đóng trình duyệt.');
  }
})();
