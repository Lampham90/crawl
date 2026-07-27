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
      '--lang=vi-VN,vi',
      '--window-size=1920,1080'
    ]
  });

  const page = await browser.newPage();

  // Giả lập thông tin thiết bị và trình duyệt chuẩn
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36');
  await page.setViewport({ width: 1920, height: 1080 });
  
  // Đặt header Accept-Language mạnh để ưu tiên tiếng Việt/tiếng Anh, tránh trang ngôn ngữ địa phương lạ
  await page.setExtraHTTPHeaders({
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
  });

  try {
    const keyword = 'javhdz';
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(keyword)}&hl=vi`;
    
    console.log(`[GOOGLE] Đang truy cập thẳng link tìm kiếm: ${searchUrl}`);
    await page.goto(searchUrl, { waitUntil: 'networkidle2', timeout: 60000 });

    // Xử lý trang Cookie Consent của Google (nếu có) trước khi tìm kết quả
    try {
      console.log('[GOOGLE] Kiểm tra xem có bị vướng trang Cookie Consent không...');
      // Tìm nút "Reject all" hoặc "Từ chối tất cả" (bằng nhiều loại selector khác nhau của Google)
      const cookieButton = await page.$('button[id="W0wltc"], div.QS5gu.sy4vM');
      if (cookieButton) {
         console.log('[GOOGLE] Phát hiện trang Cookie. Đang click Từ chối...');
         await cookieButton.click();
         await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 });
      } else {
         console.log('[GOOGLE] Không thấy trang Cookie, tiếp tục tìm kiếm.');
      }
    } catch (e) {
      console.log('[GOOGLE] Bỏ qua kiểm tra Cookie.');
    }

    console.log('[GOOGLE] Đang tìm kiếm phần tử kết quả...');
    // Cố gắng đợi thẻ chứa kết quả
    await page.waitForSelector('div#search, div#main', { timeout: 30000 });

    console.log('[GOOGLE] Phân tích URL trang web đầu tiên...');
    const firstResultUrl = await page.evaluate(() => {
      // Tìm kiếm các thẻ a chứa URL thực tế trong vùng kết quả
      const links = document.querySelectorAll('div#search a, div#main a');
      for (let a of links) {
        // Bỏ qua các link nội bộ của google
        if (a.href && a.href.startsWith('http') && !a.href.includes('google.com')) {
           return a.href;
        }
      }
      return null;
    });

    if (firstResultUrl) {
      const urlObj = new URL(firstResultUrl);
      const domainOnly = `${urlObj.protocol}//${urlObj.hostname}`;
      
      console.log(`[SUCCESS] Trang web đầu tiên tìm được: ${firstResultUrl}`);
      console.log(`[SUCCESS] Domain trích xuất: ${domainOnly}`);

      // Ghi lên Gist
      await updateGist(domainOnly);
    } else {
      console.log('[WARNING] Không trích xuất được link từ kết quả trả về. Có thể Google đã thay đổi giao diện hoặc trả về trang báo lỗi.');
      
      // In ra nội dung text để debug
      const pageText = await page.evaluate(() => document.body.innerText.substring(0, 500));
      console.log(`[DEBUG] Nội dung trang hiện tại (500 ký tự đầu):\n${pageText}`);
    }

  } catch (error) {
    console.error('[ERROR] Đã xảy ra lỗi:', error.message);
  } finally {
    await browser.close();
    console.log('[BROWSER] Đã đóng trình duyệt.');
  }
})();
