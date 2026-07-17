const axios = require('axios');
const mongoose = require('mongoose');

const uri = process.env.MONGODB_URI; // Dùng biến môi trường từ GitHub Secrets

mongoose.connect(uri);

const MovieSchema = new mongoose.Schema({}, { strict: false });
const Movie = mongoose.model('Movie', MovieSchema);

async function syncNewMovies() {
    try {
        console.log("--- ĐANG CẬP NHẬT PHIM MỚI ---");
        const listRes = await axios.get('https://phimapi.com/v1/api/danh-sach?page=1');
        const items = listRes.data.data.items;

        for (const item of items) {
            const detailRes = await axios.get(`https://phimapi.com/phim/${item.slug}`);
            const fullData = detailRes.data.movie;

            delete fullData._id;
            fullData.api_id = item._id;

            // Upsert: Nếu trùng slug thì cập nhật, không thì tạo mới
            await Movie.findOneAndUpdate(
                { slug: fullData.slug },
                { $set: fullData },
                { upsert: true }
            );
            console.log(`Đã cập nhật: ${fullData.name}`);
        }
        process.exit();
    } catch (err) {
        console.error(err);
        process.exit(1);
    }
}

syncNewMovies();
