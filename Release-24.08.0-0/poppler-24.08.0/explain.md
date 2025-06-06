# Poppler 24.08.0 소개

## 📌 개요

**Poppler**는 PDF 문서를 렌더링하거나 처리하는 데 사용되는 **오픈 소스 PDF 렌더링 라이브러리**입니다. `xpdf`라는 오래된 툴에서 파생되어 현재는 리눅스, 윈도우, macOS 등 다양한 플랫폼에서 사용됩니다.

> ✅ 버전: **24.08.0**  
> ✅ 릴리즈일: **2024년 8월 (예정 또는 출시됨)**  
> ✅ 라이선스: GPL v2

---

## 🚀 주요 기능

- PDF 페이지를 이미지로 렌더링 (PNG 등)
- 텍스트 추출
- 페이지 회전, 자르기, 병합
- PDF 메타데이터 읽기
- 다양한 출력 백엔드 지원 (Cairo, Qt5/6, Splash 등)

---

## 🛠️ 주요 도구들

| 도구 이름      | 설명 |
|----------------|------|
| `pdftoppm`     | PDF 페이지를 이미지(PPM/PNG 등)로 변환 |
| `pdftocairo`   | Cairo 백엔드를 활용해 다양한 형식(PNG, SVG, PS 등)으로 변환 |
| `pdfinfo`      | PDF 메타데이터 추출 |
| `pdftotext`    | PDF 텍스트 추출 |
| `pdfimages`    | PDF 내부 이미지 추출 |
| `pdfseparate`  | PDF를 페이지 단위로 분리 |
| `pdfunite`     | 여러 PDF 병합 |

---

## 📥 설치 방법

### ✅ Windows (예: conda 또는 직접 설치)

```bash
# conda 설치 예시
conda install -c conda-forge poppler
