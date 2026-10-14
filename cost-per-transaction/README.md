# BTC Cost per Transaction (`BTC %ex`)

비트코인의 트랜잭션당 비용(Cost per Transaction, CPT)을 최근 100봉 범위 안에서 0~1로 정규화하고, 이동평균선 3개로 추세를 보여 주는 TradingView 지표입니다.

- 스크립트: [`btc_cost_per_transaction.pine`](btc_cost_per_transaction.pine) (Pine Script v5)
- 차트 범례에 표시되는 이름: `BTC %ex`

## 계산 방식

1. **트랜잭션당 비용**을 계산합니다.
   - `채굴자 수익(USD) ÷ 트랜잭션 수`
   - Blockchain.com이 제공하던 CPTRA 지표와 정의가 같습니다.
2. **정규화**합니다.
   - 최근 100봉의 최솟값을 0, 최댓값을 1로 놓고 현재 값의 위치를 계산합니다.
   - 100봉이 모두 같은 값이라서 범위가 0이면 `na`를 반환합니다.
3. **이동평균**을 계산합니다.
   - 정규화한 값에 Short, Mid, Long 기간의 이동평균을 적용해서 세 선으로 그립니다.

## 데이터 출처

| 항목 | TradingView 심볼 | 제공처 |
|---|---|---|
| 채굴자 수익(USD) | `COINMETRICS:BTC_MINERREVENUEUSD` | Coin Metrics |
| 트랜잭션 수 | `COINMETRICS:BTC_TXCOUNT` | Coin Metrics |

두 심볼 모두 일봉(`'D'`)으로 요청합니다. 당일 데이터는 다음 날 반영되므로, 오늘 봉에는 전날 값이 쓰입니다.

## 기본 설정

| 입력 | 기본값 |
|---|---|
| Short Period | 5 |
| Mid Period | 50 |
| Long Period | 200 |
| Type of Moving Average | SMA (EMA, WMA 선택 가능) |
| Warn if data is older than (days) | 3 (상태 표시줄에는 표시하지 않음) |

| 선 | 색상 | 두께 |
|---|---|---|
| CPT MA Short | `#4CAF50` (녹색) | 2 |
| CPT MA Mid | `#2962FF` (파란색) | 1 |
| CPT MA Long | `#000000` (검은색) | 1 |

## 데이터 갱신 경고

마지막 데이터가 설정한 일수보다 오래되면 차트 오른쪽 위에 빨간 경고(`Data not updated since YYYY-MM-DD`)가 표시됩니다.

이 경고를 넣은 이유는 다음과 같습니다. Pine의 `ta.sma` 같은 함수는 `na` 값을 건너뛰고 계산합니다. 그래서 데이터가 끊겨 정규화 값이 `na`가 되어도 선이 사라지지 않고, 마지막 값에서 평평하게 굳은 채로 계속 그려집니다. 경고가 없으면 차트만 보고는 데이터가 멈췄다는 사실을 알기 어렵습니다.

## 적용 방법

1. TradingView의 Pine Editor에 `btc_cost_per_transaction.pine`의 내용을 붙여 넣고 저장합니다.
2. 이미 차트에 붙어 있는 지표에는 예전 설정이 남아 있습니다. 새 기본값을 쓰려면 지표 설정 창에서 **Defaults → Reset settings**를 누릅니다.

## 변경 이력

### 2026-10-14: 데이터 출처를 Coin Metrics로 교체

- **문제:** 예전 버전은 `QUANDL:BCHAIN/CPTRA`를 사용했습니다. 이 심볼은 현재 `BCHAIN:CPTRA`로 연결되는데, 2026-06-22 이후로 새 데이터가 들어오지 않았습니다. 같은 BCHAIN 계열인 MIREV, NTRAN, ETRAV, TRFEE도 같은 날짜에 멈췄습니다. 원본인 Blockchain.com의 데이터는 계속 갱신되고 있었으므로, TradingView로 데이터를 넘겨주는 단계(Nasdaq Data Link, 예전 Quandl)에서 공급이 끊긴 것으로 판단했습니다.
- **증상:** 마지막 값이 매일 반복되면서 6월 말부터 선이 평평해졌습니다. 9월 중순에는 녹색 선이 급등했고, 2026-09-29부터는 세 선이 모두 0.85 / 0.19 / 0.14(SMA 5/50/200 기준)에서 멈췄습니다.
- **조치:** Coin Metrics의 채굴자 수익과 트랜잭션 수로 같은 지표를 직접 계산하도록 바꿨습니다. 2023-07-02부터 2026-06-22까지 기존 `BCHAIN:CPTRA`와 비교한 결과, 상관계수는 0.998이고 두 값의 비율은 중앙값 기준 0.999였습니다.
- **그 밖의 변경**
  - 데이터 갱신 경고를 추가했습니다.
  - 계산만 하고 그리지 않던 입력 3개(CPT #1~#3)를 제거했습니다.
  - 기간 입력을 `input.int`로 바꿨습니다.
  - 기본값과 선 스타일을 기존 차트 설정과 같게 맞췄습니다.
