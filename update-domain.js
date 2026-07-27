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
    const oldDomainUrl = 'https://javhdz.im/';
    console.log(`[NAVIGATE] Đang truy cập domain cũ: ${oldDomainUrl}`);
    
    // Mở link cũ và chờ trang tự động redirect sang domain mới
    await page.goto(oldDomainUrl, { waitUntil: 'networkidle2', timeout: 60000 });

    // Lấy URL thực tế sau khi trang đã nhảy hướng hoàn tất
    const finalUrl = page.url();
    const urlObj = new URL(finalUrl);
    const finalDomain = `${urlObj.protocol}//${urlObj.hostname}`;

    console.log(`[SUCCESS] Domain chính thức sau khi điều hướng: ${finalDomain}`);

    // Ghi đè trực tiếp vào file domain.txt trong repository
    fs.writeFileSync('domain.txt', finalDomain, 'utf8');
    console.log('[FILE] Đã ghi thành công vào domain.txt');

  } catch (error) {
    console.error('[ERROR] Lỗi:', error.message);
  } finally {
    await browser.close();
    console.log('[BROWSER] Đã đóng trình duyệt.');
  }
})();
