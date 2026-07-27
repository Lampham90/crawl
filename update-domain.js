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

    // Lọc qua tất cả các kết quả trả về để tìm domain chuẩn xác chứa từ khóa
    const validUrl = await page.evaluate(() => {
      const linkElements = document.querySelectorAll('.result__url');
      for (let el of linkElements) {
        let href = el.innerText.trim();
        if (!href.startsWith('http')) {
          href = 'https://' + href;
        }
        
        try {
          const urlObj = new URL(href);
          // ĐIỀU KIỆN LỌC: Domain bắt buộc phải chứa chữ "javhdz" để loại bỏ trang tào lao
          if (urlObj.hostname.includes('javhdz')) {
            return `${urlObj.protocol}//${urlObj.hostname}`;
          }
        } catch (e) {
          // Bỏ qua nếu URL lỗi
        }
      }
      return null;
    });

    if (validUrl) {
      console.log(`[SUCCESS] Đã lọc và tìm thấy domain chuẩn: ${validUrl}`);

      // Ghi đè vào file domain.txt trong repo
      fs.writeFileSync('domain.txt', validUrl, 'utf8');
      console.log('[FILE] Đã ghi thành công vào domain.txt');
    } else {
      console.log('[WARNING] Không tìm thấy domain hợp lệ chứa từ khóa javhdz trong kết quả.');
    }

  } catch (error) {
    console.error('[ERROR] Lỗi:', error.message);
  } finally {
    await browser.close();
    console.log('[BROWSER] Đã đóng trình duyệt.');
  }
})();
