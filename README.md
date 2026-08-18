# 미국 대형주 기술적 스크리너

미국 시가총액 상위 종목을 매일 자동으로 스캔해서, 아래 기준에 맞는 종목을 찾아주는 스크리너입니다.

## 보는 지표 / 매수 기준

| 지표 | 기준 | 코드 위치 |
|---|---|---|
| 이동평균선 | 25일, 112일, 224일, 448일 (참고용으로 표시) | `config.py: ma_periods` |
| RSI | 30~35 구간이면 매수 관심권 | `config.py: rsi_buy_low/high` |
| OBV | 해당 종목의 OBV가 자기 자신의 이동평균(기본 20일)보다 높으면 매집 우위로 판단 | `config.py: obv_ma_period` |
| 일목 구름대 | 최근 구간(기본 120봉) 중 구름이 가장 두꺼운(선행스팬 A/B가 가장 많이 겹치는) 지점을 찾고, 그 구간 하단에 현재가가 근접(기본 2% 이내)하면 지지 매수 신호 | `config.py: cloud_lookback, cloud_pullback_tolerance` |
| 매물대 | 최근 1년 가격대별 거래량(Volume Profile)을 계산해 POC(최다거래가)와 Value Area를 구하고, 현재가가 POC/Value Area 하단에 근접(기본 2% 이내)하면 지지 매수 신호 | `config.py: volume_profile_*` |

4개 조건(RSI/OBV/구름대/매물대) 중 몇 개를 충족했는지 `매칭 N/4`로 표시하고, 기본적으로 2개 이상 충족한 종목을 "관심 종목"으로 따로 뽑아줍니다.

> 구름대·매물대 신호는 사용자마다 해석이 다를 수 있는 지표라, `config.py`에서 얼마든지 조정할 수 있게 만들었습니다. 실제로 써보면서 tolerance(허용 오차)나 lookback(조회 구간)을 취향에 맞게 조절하세요.

## 종목 선정 방식

무료로 "실시간 시총 상위 50개"를 그대로 주는 API가 없어서, 대형주 후보 리스트(`universe.py`, 100여개 종목)를 두고 **매 실행 시마다 실시간 시가총액을 조회해서 상위 50개를 다시 골라냅니다.** 신규 상장/편입 종목이 후보 리스트에 없으면 놓칠 수 있으니, 가끔 `universe.py`를 확인해서 빠진 대형주가 있으면 추가해주세요.

## 설치 및 실행

```bash
pip install -r requirements.txt
python3 main.py
```

실행하면:
1. 콘솔에 결과 표 출력
2. `results/latest.md`, `results/latest.csv`, `results/YYYY-MM-DD.md` 저장

### 주요 옵션

```bash
python3 main.py --top-n 30                 # 상위 30개만 스크리닝
python3 main.py --rsi-low 25 --rsi-high 35  # RSI 기준 조정
python3 main.py --cloud-tolerance 0.03      # 구름대 허용 오차 3%로 조정
python3 main.py --vp-tolerance 0.03         # 매물대 허용 오차 3%로 조정
python3 main.py --min-signals 3             # 관심 종목 기준을 3개 이상 충족으로 상향
python3 main.py --no-save                   # 파일 저장 없이 콘솔 출력만
```

## 매일 자동 실행 (GitHub Actions)

`.github/workflows/daily-screen.yml`이 평일 21:30 UTC(미국 정규장 마감 이후)에 자동으로 스크리너를 돌리고 `results/` 폴더에 결과를 커밋합니다. 저장소의 Actions 탭에서 실행 로그를 확인하거나, `results/latest.md`를 열어서 그날의 스크리닝 결과를 바로 볼 수 있습니다.

수동으로 즉시 실행하고 싶으면 GitHub 저장소의 Actions 탭 → "Daily US Stock Screen" → "Run workflow"를 누르면 됩니다.

> 이 저장소를 만든 샌드박스 환경은 보안 정책상 Yahoo Finance로 나가는 네트워크가 막혀 있어서 이 환경에서는 직접 실시간 실행을 테스트하지 못했습니다. 로직은 합성 데이터로 검증했으니, 로컬 PC나 GitHub Actions(외부 인터넷 제한 없음)에서 실행해 실제 값이 잘 나오는지 한 번 확인해보세요.

## 코드 구조

```
main.py                        # CLI 진입점
us_stock_screener/
  config.py                    # 모든 기준값(임계값) 설정
  universe.py                  # 대형주 후보 티커 목록
  data.py                      # yfinance로 시총 조회 + 일봉 데이터 다운로드
  indicators.py                # SMA/RSI/OBV/일목구름대/매물대 계산
  screener.py                  # 종목별 지표 계산 + 매수 조건 판정
  report.py                    # 결과를 Markdown/CSV로 포맷
results/                       # 실행 결과 저장 위치 (Actions가 자동 커밋)
```

## 한계 및 주의사항

- 무료 데이터(Yahoo Finance) 특성상 지연/결측이 있을 수 있습니다. 투자 판단의 참고용으로만 사용하세요.
- 구름대 "최다밀집구간"과 매물대 "지지 판단"은 표준 지표가 아니라 사용자 설명을 바탕으로 합리적으로 해석해 구현한 로직입니다. 실제 차트로 비교해보고 `config.py` 값을 취향에 맞게 조정하는 것을 권장합니다.
- 이 도구는 매수 신호를 자동 실행하지 않습니다. 어디까지나 "확인할 종목 목록"을 매일 뽑아주는 스크리너입니다.
