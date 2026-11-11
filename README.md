# pinescript

TradingView에서 사용하는 Pine Script 지표를 보관하는 저장소입니다. 지표마다 폴더를 하나씩 두고, 폴더 안의 README에 계산 방식과 데이터 출처, 변경 이력을 기록합니다.

| 폴더 | 지표 | 설명 |
|---|---|---|
| [`cost-per-transaction`](cost-per-transaction/) | BTC Cost per Transaction (`BTC %ex`) | 채굴자 수익 ÷ 트랜잭션 수를 정규화하고 이동평균 3개로 표시합니다. |
| [`1-125-flow-v2`](1-125-flow-v2/) | Crypto Flow v2 (`Flow v2 (1-10)` 등 4개) | **권장 버전입니다.** 시가총액 순위 구간별 코인의 기준 시각 이후·최근 60분 상대 강도를 순위표와 강조 선으로 보여 주고, 네 순위표를 차트 오른쪽에 정확한 높이로 쌓습니다. |
| [`1-125-flow`](1-125-flow/) | Crypto Ranks 1-10 / 11-50 / 51-100 / 101-125 | 이전 버전입니다. 시가총액 순위 구간의 코인들을 호스트 차트 위에 겹쳐 그리고, 보이는 구간의 등락률을 순위표로 보여 줍니다. 새로 설치할 때는 `1-125-flow-v2`를 쓰세요. |
| [`td-sequential`](td-sequential/) | TD Sequential (`TD Seq`) | DeMark의 셋업 9와 카운트다운 13을 차트에 숫자로 표시하고 TDST 선을 그립니다. |
| [`td-research-v6`](td-research-v6/) | TD Research v6 | Kidze 차트 연구 기반의 Sequential·Combo·Aggressive 후보를 표시하며, 9·13 확대와 꼬리 바깥 라벨 배치를 적용한 연구판입니다. |
