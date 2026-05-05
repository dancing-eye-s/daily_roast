# Award Archive Pipeline

이 폴더는 대한민국 광고대상 수상작 아카이브를 점진적으로 쌓기 위한 수집 파이프라인입니다.

## 구조

- `seeds/source_index.json`
  - 연도별 개요 기사, 인터뷰, PDF 등 원문 소스 목록
- `seeds/entries.seed.json`
  - 실제 사이트에서 랜덤으로 노출할 엔트리의 정규화 seed
- `raw/`
  - 요청한 원문 HTML/PDF 캐시
- `normalized/award_archive.json`
  - 프런트와 검수에 쓰는 정규화 결과물
- `reports/`
  - fetch/build 요약 리포트

## 실행

```bash
python3 scripts/build_award_archive.py fetch
python3 scripts/build_award_archive.py ocr
python3 scripts/promote_ocr_candidates.py --dry-run
python3 scripts/promote_ocr_candidates.py
python3 scripts/build_award_archive.py build
python3 scripts/build_award_archive.py all
```

`ocr`는 이미지형 수상표를 OCR해 `archive/ocr/`에 텍스트 아티팩트를 생성합니다.

`promote_ocr_candidates.py`는 `archive/ocr/parsed_candidates.json`에서 신뢰도 높은 후보만 골라
`entries.seed.json`으로 승격합니다.

`all`은 원문 fetch, OCR, 정규화 결과 생성을 순서대로 실행합니다.

## 동작 방식

1. `source_index.json`과 `entries.seed.json`의 URL을 모읍니다.
2. 각 URL의 HTML/PDF를 `archive/raw/`에 캐시합니다.
3. seed 엔트리를 정규화해 `archive/normalized/award_archive.json`을 생성합니다.
4. 같은 데이터로 프런트용 `data/archive.js`도 다시 생성합니다.
5. 이미지형 수상표는 `archive/ocr/*.json`, `archive/ocr/*.txt`에 OCR 결과를 남깁니다.
6. 검토된 OCR 후보는 `promote_ocr_candidates.py`로 seed에 병합합니다.

## PDF 파싱

현재 로컬 환경에는 PDF 파서가 설치되어 있지 않아 PDF는 캐시만 하고 본문 추출은 비활성화됩니다.

`pypdf`를 설치하면 PDF 텍스트 추출이 자동으로 활성화됩니다.

## 확장 포인트

- `source_index.json`에 연도별 인터뷰/보도/PDF URL 추가
- `entries.seed.json`에 신규 수상작 추가
- 필요하면 `build_award_archive.py`에 사이트별 파서 추가
- OCR 텍스트를 바탕으로 2019/2017/2015/2013 이미지형 수상표 자동 파서 추가

## 검수 원칙

- `copyStatus = verified`
  - 실제 기사, 영상, 포스터, 공식 인터뷰에서 직접 확인한 문구
- `copyStatus = inferred`
  - 기사 설명, 수상 소개, 맥락 설명에서 정리한 핵심 메시지
