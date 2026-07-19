# Công cụ Đồng Bộ Timeline CapCut từ JSON Timestamps

Công cụ Python này giúp tự động đồng bộ hóa timeline CapCut Desktop dựa trên dữ liệu timestamp JSON có sẵn mà không cần render.

## ⚠️ CẢNH BÁO QUAN TRỌNG
> [!IMPORTANT]
> **HÃY ĐÓNG ỨNG DỤNG CAPCUT TRƯỚC KHI CHẠY SCRIPT.**
> Nếu CapCut đang mở, nó sẽ tự động lưu dự án đè lên những thay đổi mà script vừa ghi vào file `draft_content.json`, dẫn đến mất đồng bộ hoặc xung đột dữ liệu.

> [!WARNING]
> Kể từ phiên bản CapCut 6.0+, file `draft_content.json` có thể đã bị mã hóa. Script này có bước validate tự động. Nếu phát hiện file bị mã hóa, chương trình sẽ báo lỗi và dừng lại an toàn thay vì làm hỏng dự án của bạn.

---

## 🚀 Hướng Dẫn Sử Dụng

### 1. Sử dụng ứng dụng giao diện đồ họa (GUI)
Để mở ứng dụng Desktop trực quan, chỉ cần chạy lệnh sau:
```bash
python gui_app.py
```
**Tính năng nổi bật của GUI:**
- Cho phép duyệt tìm thư mục chứa dự án và file JSON bằng cửa sổ chọn (file picker).
- **Tự động quét và hiển thị danh sách dự án** trong thư mục đã chọn vào danh sách thả xuống (Combobox).
- Hiển thị kết quả log tiến trình đồng bộ thời gian thực kèm màu sắc trực quan (Lỗi màu đỏ, Cảnh báo màu cam, Thành công màu xanh lá).
- Ghi nhớ cấu hình thư mục đã chọn lần trước để tiết kiệm thời gian.

### 2. Cách Tìm Thư Mục Dự Án CapCut (`--drafts-dir`)
Để tìm đường dẫn chính xác nơi CapCut Desktop lưu trữ các project của bạn:
1. Mở **CapCut Desktop**.
2. Trên màn hình trang chủ (Home), nhấp vào biểu tượng **Settings (Răng cưa)** ở góc trên bên phải -> Chọn **Global Settings**.
3. Tại tab **Project**, bạn sẽ thấy mục **Save to** hiển thị đường dẫn hiện tại (Ví dụ của bạn: `D:\CAIDAT\CAPCUT`).
4. Đây chính là giá trị truyền vào tham số `--drafts-dir` (hoặc nhập vào ô thư mục trong GUI).

### 3. Ví dụ Lệnh Chạy qua CLI (Dòng lệnh)

#### Chạy thử nghiệm (Dry Run) để xem kế hoạch mà không ghi đè dự án:
```bash
python sync_capcut.py --drafts-dir "D:\CAIDAT\CAPCUT" --project-name "Project_Test_01" --timestamps "sample_timestamps.json" --dry-run
```

#### Thực hiện đồng bộ hóa thực tế (Mặc định tự động tạo backup `.bak`):
```bash
python sync_capcut.py --drafts-dir "D:\CAIDAT\CAPCUT" --project-name "Project_Test_01" --timestamps "sample_timestamps.json"
```

#### Đồng bộ thực tế và bỏ qua bước tạo backup:
```bash
python sync_capcut.py --drafts-dir "D:\CAIDAT\CAPCUT" --project-name "Project_Test_01" --timestamps "sample_timestamps.json" --backup False
```

---

## 🛠️ Quy Trình Đồng Bộ & Logic Xử Lý

1. **Voice Track**: Script tự đo độ dài thực tế của file voice bằng `ffprobe` và đặt segment voice chạy suốt từ giây `0`.
2. **Visuals (Track ảnh/video)**: Xếp các segment nối tiếp nhau theo đúng khoảng `start`/`end` trong file JSON.
3. **Xử lý lệch thời gian tự động ở segment cuối cùng**:
   - Nếu tổng thời gian visuals **ngắn hơn** voice -> Tự kéo dài segment cuối cùng.
     - *Lưu ý*: Nếu segment cuối cùng là **video** và việc kéo dài vượt quá thời lượng gốc của video đó -> Script sẽ in cảnh báo riêng và giữ nguyên độ dài gốc để tránh lỗi đứng hình trên CapCut. Nếu là **ảnh** thì kéo dài tự do.
   - Nếu tổng thời gian visuals **dài hơn** voice -> Tự cắt ngắn segment cuối cùng.
   - Nếu chênh lệch > 2 giây -> In cảnh báo kiểm tra lại timestamp nhưng vẫn tự động điều chỉnh.

---

## 📂 Định Dạng File JSON Mẫu (`sample_timestamps.json`)
```json
{
  "voice": {
    "file": "voice_full.mp3"
  },
  "visuals": [
    {
      "type": "image",
      "file": "img_01.png",
      "start": 0.0,
      "end": 3.2
    },
    {
      "type": "video",
      "file": "clip_02.mp4",
      "start": 3.2,
      "end": 7.5
    },
    {
      "type": "image",
      "file": "img_03.png",
      "start": 7.5,
      "end": 10.0
    }
  ]
}
```
*Lưu ý: Script hỗ trợ tự suy rộng schema linh hoạt (chấp nhận cả `audio` thay cho `voice`, `clips` thay cho `visuals`, v.v.).*
