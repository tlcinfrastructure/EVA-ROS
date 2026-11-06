# Phase 3 — tiến độ kiểm thử GRUB VM (06/11/2026)

## Kết quả đã quan sát

QEMU 8.2.2 chạy TCG, không mạng, không gắn ổ vật lý; OVMF 2024.02 với bản sao VARS có khóa Microsoft. Boot stack là bản sao signed shim/GRUB 2.12-1ubuntu7.3 của Ubuntu. File ghi chỉ thuộc VM/workspace.

- GRUB thật render EVA-ROS ở framebuffer **1920×1080**.
- lsfonts xác nhận **GNU Unifont Regular 16**; console trả shim_lock=y, lockdown=y. Đây là bằng chứng enforcement trong guest, không phải phép đo trạng thái firmware host.
- Ubuntu, Windows và UEFI đứng đầu trong menu thử, class được khai báo trong harness. Cả icon selected/unselected đều hiện.
- Phím xuống đổi selection sang Windows; End cuộn tới mục 8. Tên dài bị cắt trong vùng chữ, không tràn sang EVA.
- Enter vào submenu có hai mục; Esc trở ra. e mở editor, c mở console.
- Enter tại Windows gọi TEST_ONLY_WINDOWS, chỉ echo/sleep; không boot Windows thật.
- Timeout=-1 không tự boot trong thời gian thao tác/chờ kiểm thử.

## Các sửa lỗi đã thực hiện

1. Harness cần insmod gfxmenu/png như generator Ubuntu.
2. Theme đổi font dự kiến Unifont Regular 16 thành tên được VM xác nhận GNU Unifont Regular 16.
3. Đổi tọa độ thập phân sang phần trăm nguyên cộng offset: left=15%+11, top=27%+1, width=32%+11, height=31%+6. Sau thay đổi này, theme nạp được. Bố cục 1920×1080 và cỡ 16 được giữ.

Các lần trước đó rơi về menu chữ mặc định đã được giữ làm bằng chứng. Trong một lượt bật debug=all và tái vào normal có ghi nhận ngoại lệ guest #UD; chưa xác định nguyên nhân, chưa đánh giá là lỗi theme hay VM/GRUB. Lượt khởi động sạch không bật debug render và thao tác được như ảnh. Cần điều tra nếu tái diễn; không coi mọi stress test đã pass.

## Chưa hoàn tất Phase 3

- Native order/classes trên cấu hình được generator của máy thật sinh ra: chưa triển khai/kiểm thử. Harness hiện chủ động khai báo chúng, không chứng minh installer đã làm việc đó.
- Mode thấp hơn/fallback và độ phân giải thật laptop.
- Installer/rollback end-to-end trong môi trường cách ly.
- Review đầy đủ chainloader Windows; boot Ubuntu/Windows thật và power on/restart thuộc nghiệm thu phần cứng sau phê duyệt cài.

Acceptance cài đặt vẫn khóa. Không thay GRUB/EFI/BootOrder trên host. Không push thay đổi mới lên GitHub. Người dùng báo đã tự push snapshot Phase 2.

Các ảnh thực nằm trong thư mục results/phase3 của bản làm việc; gói công khai kèm ảnh chọn lọc ở docs/vm-screenshots. Các test static không tự chạy VM, nên kết quả NOT RUN BY THIS SCRIPT chỉ áp dụng cho runner đó.

## Khối Windows đã đọc

Đã nhận khối os-prober/UEFI từ cấu hình hiện tại. Windows sử dụng part_gpt/fat, search theo UUID ESP và chainloader EFI Microsoft; phù hợp với đường firmware đã khảo sát. Chưa thử boot Windows. UEFI entry chưa có class, được bảo vệ bằng fwsetup --is-supported. Chi tiết định danh chỉ giữ trong evidence riêng, không đưa vào gói công khai.

## Ma trận số lượng mục

Đã khởi động VM độc lập cho 3, 4 và 5 mục; ảnh matrix-3/4/5 tại 1920×1080 được xem trực tiếp. Ba hàng đầu đúng; End cuộn đến mục cuối ở ca 4/5. Các ảnh three/four/five-entries trước đó chụp quá sớm ở khung đen 1280×800, được coi là ảnh chuyển tiếp, không dùng làm pass/fail. Lượt 8 mục và submenu 2 mục đã kiểm tra riêng. VM đã tự tắt sau từng lượt, không còn chạy nền.
