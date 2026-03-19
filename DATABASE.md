# Cấu trúc Database

Database: `law` (MySQL)

## Sơ đồ quan hệ

```
PDChuDe (Chủ đề)
  └── PDDeMuc (Đề mục)
        └── PDChuong (Chương)
              └── PDDieu (Điều)
                    ├── PDTable (Bảng HTML trong điều)
                    ├── PDFile (File đính kèm)
                    └── PDMucLienQuan (Điều liên quan)
```

---

## Bảng `pdchude` — Chủ đề pháp điển

| Cột  | Kiểu             | Ghi chú     |
|------|------------------|-------------|
| `id` | VARCHAR(128)     | Primary key |
| `ten` | TEXT            | Tên chủ đề  |
| `stt` | INT             | Số thứ tự   |

---

## Bảng `pddemuc` — Đề mục

| Cột        | Kiểu         | Ghi chú                          |
|------------|--------------|----------------------------------|
| `id`       | VARCHAR(128) | Primary key                      |
| `ten`      | TEXT         | Tên đề mục                       |
| `stt`      | INT          | Số thứ tự                        |
| `chude_id` | VARCHAR(128) | FK → `pdchude.id`                |

---

## Bảng `pdchuong` — Chương

| Cột        | Kiểu         | Ghi chú                          |
|------------|--------------|----------------------------------|
| `mapc`     | VARCHAR(128) | Primary key (mã phân cấp)        |
| `ten`      | TEXT         | Tên chương                       |
| `chimuc`   | TEXT         | Chỉ mục (I, II, III...)          |
| `stt`      | INT          | Số thứ tự                        |
| `demuc_id` | VARCHAR(128) | FK → `pddemuc.id`                |

---

## Bảng `pddieu` — Điều luật

| Cột           | Kiểu         | Ghi chú                          |
|---------------|--------------|----------------------------------|
| `mapc`        | VARCHAR(128) | Primary key (mã phân cấp)        |
| `ten`         | TEXT         | Tên điều                         |
| `chimuc`      | INT          | Số thứ tự điều                   |
| `stt`         | INT          | Số thứ tự trong chương           |
| `noidung`     | TEXT         | Nội dung điều luật               |
| `vbqppl`      | TEXT         | Tên văn bản quy phạm pháp luật   |
| `vbqppl_link` | TEXT (null)  | Link văn bản trên vbpl.vn        |
| `demuc_id`    | VARCHAR(128) | FK → `pddemuc.id`                |
| `chuong_id`   | VARCHAR(128) | FK → `pdchuong.mapc`             |
| `chude_id`    | VARCHAR(128) | FK → `pdchude.id`                |

---

## Bảng `pdtable` — Bảng HTML trong điều

| Cột       | Kiểu         | Ghi chú              |
|-----------|--------------|----------------------|
| `id`      | INT          | Primary key (auto)   |
| `dieu_id` | VARCHAR(128) | FK → `pddieu.mapc`   |
| `html`    | TEXT         | Nội dung HTML bảng   |

---

## Bảng `pdfile` — File đính kèm

| Cột       | Kiểu         | Ghi chú              |
|-----------|--------------|----------------------|
| `id`      | INT          | Primary key (auto)   |
| `dieu_id` | VARCHAR(128) | FK → `pddieu.mapc`   |
| `link`    | TEXT         | URL file             |
| `path`    | TEXT         | Đường dẫn local      |

---

## Bảng `pdmuclienquan` — Điều liên quan

| Cột        | Kiểu         | Ghi chú              |
|------------|--------------|----------------------|
| `id`       | INT          | Primary key (auto)   |
| `dieu_id1` | VARCHAR(128) | FK → `pddieu.mapc`   |
| `dieu_id2` | VARCHAR(128) | FK → `pddieu.mapc`   |

---

## Bảng `vbpl` — Văn bản pháp luật (document-crawler)

| Cột       | Kiểu | Ghi chú                              |
|-----------|------|--------------------------------------|
| `id`      | INT  | ItemID từ vbpl.vn                    |
| `noidung` | TEXT | Nội dung HTML toàn văn               |

---

## Bảng `vb_chimuc` — Chỉ mục văn bản (split_document)

| Cột           | Kiểu | Ghi chú                              |
|---------------|------|--------------------------------------|
| `id`          | INT  | Primary key                          |
| `id_vb`       | INT  | FK → `vbpl.id`                       |
| `noi_dung`    | TEXT | Nội dung đoạn (chương hoặc điều)     |
| `chi_muc_cha` | INT  | ID chương cha (null nếu là chương)   |
