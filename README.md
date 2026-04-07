# SAT Logcat Viewer

Ung dung desktop de doc va xem log tu dien thoai Android thong qua ADB (Android Debug Bridge).

## Tinh nang

- **Ket noi thiet bi**: Tu dong phat hien va ket noi cac thiet bi Android qua USB
- **Doc log thoi gian thuc**: Su dung `adb logcat` de doc log lien tuc tu thiet bi
- **Loc log**: Loc theo muc do (Verbose, Debug, Info, Warn, Error, Fatal), PID hoac ten package
- **Tim kiem**: Tim kiem trong tat ca cac cot, ho tro regex
- **Highlight**: To sang cac dong khop voi tu khoa tim kiem
- **Xuat log**: Xuat log ra file .txt
- **Giao dien**: Giao dien don gian, ho tro dark theme

## Yeu cau he thong

- Python 3.8+
- PyQt6
- Android Platform Tools (adb)

## Cai dat

1. Cai dat cac thu vien Python:
```bash
pip install PyQt6
```

2. Tai va cai dat Android Platform Tools tu trang chu Android Developer.

3. Dam bao `adb` co trong PATH he thong.

## Su dung

1. Chay ung dung:
```bash
python main.py
```

2. Ket noi dien thoai Android qua USB va bat che do Debug USB.

3. Chon thiet bi tu dropdown "Device Selector".

4. Chon muc do log toi thieu tu "Log Level Filter" (VD: Info+ de xem tu Info tro len).

5. Nhap PID hoac ten package vao "Target Filter" neu muon loc theo ung dung cu the.

6. Nhap tu khoa vao "Search Bar" de tim kiem, co the su dung regex.

7. Nhan "Start" de bat dau doc log.

8. Dung "Stop" de dung doc log.

9. Su dung "Clear Log" de xoa log da doc.

10. "Export .txt" de xuat log ra file.

## Luu y

- Thiet bi phai bat che do Developer Options va USB Debugging.
- Neu adb khong ket noi duoc, kiem tra lai USB va che do debug.
- Log se tu dong cuon xuong duoi khi co log moi, co the tat bang checkbox "Auto-scroll".

## Cau truc du an

- `main.py`: Entry point cua ung dung
- `app/ui/main_window.py`: Cua so chinh va giao dien nguoi dung
- `app/core/device_monitor.py`: Monitor danh sach thiet bi Android
- `app/core/logcat_worker.py`: Doc va xu ly logcat tu thiet bi
- `app/core/adb_client.py`: Cac ham giao tiep voi ADB
- `app/core/logcat_parser.py`: Parse dong log thanh LogEntry
- `app/core/filter_task.py`: Xu ly loc log trong thread rieng
- `app/models/log_entry.py`: Dinh nghia LogEntry
- `app/models/log_store.py`: Luu tru cac entry log
- `app/models/log_filter.py`: Xu ly bo loc va tim kiem
- `app/models/log_table_model.py`: Model cho bang hien thi log
- `app/ui/highlight_delegate.py`: To sang cac dong khop tim kiem
- `app/dialogs/log_detail_dialog.py`: Dialog chi tiet log
- `app/ui/theme.py`: Cai dat giao dien (dark theme)

## Phat trien

De phat trien them tinh nang:

1. Sua doi cac file trong `app/` theo cau truc MVC (Models, Views, Controllers).

2. Dung PyQt6 signals/slots cho giao tiep giua cac component.

3. Chay lint va test sau khi sua doi.

## License

Du an nay duoc phat trien boi SAT.</content>
<parameter name="filePath">README.md