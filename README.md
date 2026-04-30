# HW8 — DeFi EDA: Aave

EDA одного из топ-50 протоколов DeFi с использованием 6 инструментов сбора данных,
изученных на семинаре Vega. Выбран **Aave** (топ-1 lending по TVL на DeFiLlama,
~$13.9B).

## Инструменты (все 6)

| Инструмент | Назначение | Ключ |
|---|---|---|
| **web3.py** | Снимок Aave V3 Pool: 5 резервов, supply/borrow rates, utilization, Oracle цены | RPC URL (опц., есть public fallback) |
| **Etherscan API** | Транзакции AAVE-токена, распределение размеров переводов, дневная активность | да |
| **The Graph** (Messari Aave V3 subgraph) | 365 дней истории топ-рынка: supply/borrow/util + дневной flow | да |
| **Dune Analytics** | Public DEX leaderboard через `get_latest_result`, плюс publish-flow для своего запроса | да |
| **DeFiLlama** | TVL по версиям V1/V2/V3, по чейнам, dominance vs топ-10 lending | нет |
| **GeckoTerminal + CoinGecko + Binance** | Топ-10 пулов AAVE, цена/mcap/turnover, cross-source spread | нет |

## Структура

| Файл | Назначение |
|---|---|
| `Aave_HW.ipynb` | Готовый ноутбук со всеми outputs (30 ячеек, ~1.3MB с графиками) |
| `_build_aave_nb.py` | Генератор ноутбука (для регенерации после правок) |
| `.env.example` | Шаблон для API-ключей |
| `HW8.pdf` | Текст задания |
| `Vega Blockchain and DeFi Data.pdf` | Конспект семинара |
| `Uniswap_Seminar.ipynb` | Семинарский ноутбук (образец для структуры) |
| `Chat_Transcript.pdf` | Транскрипт переписки с LLM (требование задания) |
| `Chat_Transcript.md` | Исходник транскрипта в markdown |
| `_md_to_pdf.py` | Генератор PDF из markdown |

## Запуск

```bash
git clone https://github.com/SergeySolovyev/DeFi-EDA.git
cd DeFi-EDA
cp .env.example .env          # и заполнить ключи
pip install pandas numpy matplotlib plotly requests web3 python-dotenv \
            nbclient jupyter ipykernel dune-client
jupyter notebook Aave_HW.ipynb
```

Чтобы пересобрать ноутбук с нуля:

```bash
python _build_aave_nb.py
jupyter nbconvert --to notebook --execute --inplace Aave_HW.ipynb
```

## Публичный Dune-дашборд (extra task)

**https://dune.com/sssolovjov/hw8-aave-eda** — 4 графика по Aave V3 Ethereum:
daily borrow events (90d), top borrowed reserves (30d), daily liquidations (90d),
daily unique borrowers (60d).

## Результаты (на 2026-04-30)

- **Aave V3 TVL**: $13.94B (Ethereum + 20 других чейнов)
- **Доля в lending-секторе**: 39.6% (от топ-10 протоколов), пик 59.8% в сентябре 2025
- **Топ-3 рынка V3 на Ethereum**: WETH ($4.76B), weETH ($3.19B), WBTC ($2.22B)
- **Cross-source AAVE price**: Oracle / CoinGecko / Binance / DEX расходятся в пределах ±10 bps

Подробные выводы — в секции 10 ноутбука.

## Заметки

- `.env` исключён из репо через `.gitignore`. Ключи на руках у автора.
- Section 9 ноутбука содержит SQL-шаблоны для публичного Dune-дашборда (extra task).
- Free Dune plan не позволяет создавать запросы через API — для этого используется
  UI-flow (см. Section 9), а из Python вызывается `get_latest_result(QUERY_ID)`.
