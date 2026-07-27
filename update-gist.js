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
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--lang=vi-VN,vi'
    ]
  });

  const page = await browser.newPage();

  // Giả lập giao diện người dùng thật để tránh bị Google chặn
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36');
  await page.setViewport({ width: 1280, height: 800 });

  try {
    console.log('[GOOGLE] Đang truy cập Google Search...');
    await page.goto('https://www.google.com', { waitUntil: 'networkidle2' });

    // Nhập từ khóa "javhdz" vào ô tìm kiếm
    console.log('[GOOGLE] Đang nhập từ khóa: javhdz');
    await page.type('textarea[name="q"]', 'javhdz', { delay: 100 });
    await page.keyboard.press('Enter');

    console.log('[GOOGLE] Đang đợi kết quả tìm kiếm hiển thị...');
    // Đợi một trong các selector kết quả phổ biến của Google xuất hiện
    await page.waitForSelector('div#search, div.g', { timeout: 30000 });

    // Lấy link kết quả đầu tiên chính xác nhất
    const firstResultUrl = await page.evaluate(() => {
      // Tìm thẻ a bên trong kết quả tìm kiếm đầu tiên tránh các link quảng cáo sponsored
      const firstLink = document.querySelector('div#search div.g a, div.tF2Cxc a');
      return firstLink ? firstLink.href : null;
    });

    if (firstResultUrl) {
      const urlObj = new URL(firstResultUrl);
      const domainOnly = `${urlObj.protocol}//${urlObj.hostname}`;
      
      console.log(`[SUCCESS] Tìm thấy trang web đầu tiên: ${firstResultUrl}`);
      console.log(`[SUCCESS] Lọc ra domain sạch: ${domainOnly}`);

      // Ghi lên Gist
      await updateGist(domainOnly);
    } else {
      console.log('[WARNING] Không tìm thấy đường dẫn hợp lệ nào trong kết quả tìm kiếm.');
    }

  } catch (error) {
    console.error('[ERROR] Đã xảy ra lỗi trong quá trình cào Google:', error.message);
  } finally {
    await browser.close();
    console.log('[BROWSER] Đã đóng trình duyệt.');
  }
})();
