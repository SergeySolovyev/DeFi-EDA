# HW8 — DeFi EDA: Chat Transcript

## 1. Выбор протокола

**User:** Нужно сделать DeFi EDA на топ-50 протокол. Семинар был на Uniswap.
Какой выбрать, чтобы покрыть те же 6 инструментов и получить интересные
выводы?

**Assistant:** Лучший кандидат — **Aave**:
- Топ-1 lending по DeFiLlama (~$13.9B TVL), стабильно в топ-3 всего DeFi.
- Контрастирует с Uniswap (DEX = swap volume, Aave = supply/borrow stocks),
  значит метрики будут другие: utilization, borrow APY, ликвидации.
- Богатые данные на каждом уровне: Aave V3 контракт на mainnet, Aave-токен
  с активной торговлей, Messari Aave V3 subgraph, decoded таблицы на Dune
  (`aave_v3_ethereum.*`).
- В DeFiLlama есть отдельные slugs `aave-v1`, `aave-v2`, `aave-v3` — можно
  показать эволюцию версий.

Структура ноутбука копирует семинар, но адаптируется под lending:

1. web3.py — снимок Aave V3 Pool: 5 резервов с supply/borrow rates и
   utilization, цены через Aave Oracle.
2. Etherscan API — транзакции AAVE-токена.
3. The Graph — историческая динамика топ-рынка (Messari subgraph).
4. Dune — публичный DEX leaderboard через `get_latest_result`, плюс свои
   запросы для Dune-дашборда.
5. DeFiLlama — TVL по версиям и чейнам, dominance vs lending-сектор.
6. GeckoTerminal + CoinGecko + Binance — токен AAVE.
7. Cross-source check — цена AAVE из 4 источников.
8. Public Dune dashboard (extra task).
9. Выводы.

---

## 2. Setup: ключи и адреса

**User:** Какие нужны API-ключи и какие адреса контрактов Aave V3 на
Ethereum?

**Assistant:** Бесплатных ключей нужно три (Etherscan, The Graph gateway,
Dune); RPC можно публичный.

```python
# .env
ETH_HTTP_NODE=https://ethereum.publicnode.com   # public fallback
ETHERSCAN_API_KEY=<your>
THEGRAPH_API_KEY=<your>     # https://thegraph.com/studio/apikeys/
DUNE_API_KEY=<your>          # https://dune.com/settings/api
```

Регистрация Etherscan и Dune — через email. The Graph требует
кошелёк-extension для подписи (MetaMask или Rabby — оба работают в РФ;
Coinbase Wallet геоблокирует РФ).

```python
# Aave V3 Ethereum (mainnet)
AAVE_V3_POOL   = '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'
AAVE_V3_ORACLE = '0x54586bE62E3c3580375aE3723C145253060Ca0C2'
AAVE_TOKEN     = '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'

# Watch reserves
USDC = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
USDT = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
DAI  = '0x6B175474E89094C44Da98b954EedeAC495271d0F'
WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
WBTC = '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
```

Секции, требующие ключи: Etherscan (#2), The Graph (#3), Dune (#4).
Без ключей работают: web3.py (через public RPC), DeFiLlama, GeckoTerminal,
CoinGecko, Binance — этого уже 5 из 6 инструментов, формальное требование
закрывается.

---

## 3. Web3.py — Aave V3 Pool snapshot

**User:** Покажи код для снимка Aave V3 Pool: для 5 главных резервов получить
supplied/borrowed, utilization, supply/borrow APY, цену через Oracle.

**Assistant:** Aave хранит ставки в **ray** (1e27): APY = rate / 1e27.
Используем `getReserveData(asset)`, `aToken.totalSupply()` для supplied,
`variableDebtToken.totalSupply()` для borrowed. Public RPC может выдать 429
на серии запросов — оборачиваем в retry.

```python
from web3 import Web3
import time

w3 = Web3(Web3.HTTPProvider(ETH_HTTP_NODE))
assert w3.is_connected()

POOL_ABI = [
    {"inputs":[],"name":"getReservesList","outputs":[{"type":"address[]"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[{"type":"address"}],"name":"getReserveData","outputs":[
        {"components":[{"name":"data","type":"uint256"}],
         "name":"configuration","type":"tuple"},
        {"name":"liquidityIndex","type":"uint128"},
        {"name":"currentLiquidityRate","type":"uint128"},
        {"name":"variableBorrowIndex","type":"uint128"},
        {"name":"currentVariableBorrowRate","type":"uint128"},
        {"name":"currentStableBorrowRate","type":"uint128"},
        {"name":"lastUpdateTimestamp","type":"uint40"},
        {"name":"id","type":"uint16"},
        {"name":"aTokenAddress","type":"address"},
        {"name":"stableDebtTokenAddress","type":"address"},
        {"name":"variableDebtTokenAddress","type":"address"},
        {"name":"interestRateStrategyAddress","type":"address"},
        {"name":"accruedToTreasury","type":"uint128"},
        {"name":"unbacked","type":"uint128"},
        {"name":"isolationModeTotalDebt","type":"uint128"}],
     "stateMutability":"view","type":"function"},
]
ORACLE_ABI = [
    {"inputs":[{"type":"address"}],"name":"getAssetPrice",
     "outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"BASE_CURRENCY_UNIT",
     "outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
]
ERC20_ABI = [
    {"inputs":[],"name":"decimals","outputs":[{"type":"uint8"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"type":"uint256"}],
     "stateMutability":"view","type":"function"},
]

pool   = w3.eth.contract(address=Web3.to_checksum_address(AAVE_V3_POOL),
                          abi=POOL_ABI)
oracle = w3.eth.contract(address=Web3.to_checksum_address(AAVE_V3_ORACLE),
                          abi=ORACLE_ABI)

RAY = 10**27
BASE_UNIT = oracle.functions.BASE_CURRENCY_UNIT().call()  # 1e8

def safe_call(fn, retries=4, base_sleep=1.5):
    for attempt in range(retries):
        try:
            return fn()
        except Exception:
            if attempt == retries - 1: raise
            time.sleep(base_sleep * (2 ** attempt))

watch = {'USDC': USDC, 'USDT': USDT, 'DAI': DAI, 'WETH': WETH, 'WBTC': WBTC}
rows = []
for sym, addr in watch.items():
    rd = safe_call(pool.functions.getReserveData(
        Web3.to_checksum_address(addr)).call)
    liq_rate, var_borrow_rate = rd[2], rd[4]
    a_t = w3.eth.contract(address=Web3.to_checksum_address(rd[8]),
                           abi=ERC20_ABI)
    v_d = w3.eth.contract(address=Web3.to_checksum_address(rd[10]),
                           abi=ERC20_ABI)
    erc = w3.eth.contract(address=Web3.to_checksum_address(addr),
                           abi=ERC20_ABI)
    dec = safe_call(erc.functions.decimals().call)

    a_supply = safe_call(a_t.functions.totalSupply().call) / 10**dec
    var_debt = safe_call(v_d.functions.totalSupply().call) / 10**dec
    price    = safe_call(lambda a=addr: oracle.functions.getAssetPrice(
                        Web3.to_checksum_address(a)).call()) / BASE_UNIT
    time.sleep(0.3)  # be polite to public RPC

    rows.append({
        'asset': sym,
        'supplied_usd':  a_supply * price,
        'borrowed_usd':  var_debt * price,
        'supply_apy_%':  liq_rate / RAY * 100,
        'borrow_apy_%':  var_borrow_rate / RAY * 100,
        'utilization_%': (var_debt / a_supply * 100) if a_supply else 0,
    })
import pandas as pd
snap = pd.DataFrame(rows)
print(snap)
```

Что показывает: USDC и USDT идут с высоким utilization (60–90%) —
стейблы работающие, классический pattern; WETH/WBTC низкий utilization
(20–50%) — collateral.

---

## 4. Etherscan — AAVE token activity

**User:** Тянем 10k последних транзакций AAVE-токена через Etherscan.
Какие распределения и временные паттерны интересны для ДЗ?

**Assistant:** Etherscan API V2 (V1 выпилили 15.08.2025) — единый endpoint
с параметром `chainid`. Для governance-токена смотрим распределение
размеров переводов в логе (типичный clip), и дневную активность —
у AAVE она кустистая (governance proposals + клейм rewards).

```python
import requests, pandas as pd
BASE = 'https://api.etherscan.io/v2/api'
def etherscan(**params):
    params['chainid'] = 1
    params['apikey'] = ETHERSCAN_API_KEY
    return requests.get(BASE, params=params, timeout=20).json()

resp = etherscan(module='account', action='tokentx',
                 contractaddress=AAVE_TOKEN, page=1, offset=10_000, sort='desc')
df = pd.DataFrame(resp['result'])
df['timeStamp'] = pd.to_datetime(df['timeStamp'].astype(int), unit='s')
df['value_aave'] = df['value'].astype(float) / 1e18

# Гистограмма размеров (log)
import matplotlib.pyplot as plt
df[df['value_aave'] > 0]['value_aave'].hist(bins=60, log=True)
plt.xscale('log'); plt.show()
print(f"Median transfer: {df['value_aave'].median():.4f} AAVE")
```

---

## 5. The Graph — Aave V3 historical

**User:** Как взять 365 дней истории топ-рынка Aave V3 через TheGraph?

**Assistant:** Используем **Messari standardized lending subgraph** —
его schema даёт `markets` и `marketDailySnapshots`. Это субграф на
decentralized network (gateway требует ключ).

```python
import requests, pandas as pd
SUBGRAPH_ID = 'JCNWRypm7FYwV8fx5HhzZPSFaMxgkPuw4TnR3Gpi81zk'  # Aave V3 Eth
URL = f'https://gateway.thegraph.com/api/{THEGRAPH_API_KEY}/subgraphs/id/{SUBGRAPH_ID}'

# 1. Топ-15 рынков сейчас
q = """{
  markets(first: 15, orderBy: totalValueLockedUSD, orderDirection: desc) {
    id name inputToken { symbol }
    totalValueLockedUSD totalDepositBalanceUSD totalBorrowBalanceUSD
  }
}"""
mk = pd.json_normalize(
    requests.post(URL, json={'query': q}, timeout=30).json()['data']['markets'])
for c in ['totalValueLockedUSD','totalDepositBalanceUSD',
          'totalBorrowBalanceUSD']:
    mk[c] = mk[c].astype(float)

# 2. 365 daily snapshots для топ-рынка
top_id = mk.iloc[0]['id']
q = f"""{{
  marketDailySnapshots(first: 365, orderBy: timestamp, orderDirection: desc,
                       where: {{ market: "{top_id}" }}) {{
    timestamp
    totalDepositBalanceUSD totalBorrowBalanceUSD
    dailyDepositUSD dailyBorrowUSD dailyWithdrawUSD dailyRepayUSD
  }}
}}"""
snaps = pd.json_normalize(
    requests.post(URL, json={'query': q}, timeout=30).json()['data']
    ['marketDailySnapshots'])
for c in ['totalDepositBalanceUSD','totalBorrowBalanceUSD',
          'dailyDepositUSD','dailyBorrowUSD','dailyWithdrawUSD','dailyRepayUSD']:
    snaps[c] = snaps[c].astype(float)
snaps['date'] = pd.to_datetime(snaps['timestamp'].astype(int), unit='s')
snaps = snaps.sort_values('date').reset_index(drop=True)
```

На полученных данных строим: supplied vs borrowed time-series,
utilization-line, дневной flow (deposit+borrow vs withdraw+repay) с 7d MA.

Топ-3 рынка V3 на Ethereum: WETH ~$4.76B, weETH ~$3.19B, WBTC ~$2.22B.

---

## 6. Dune — leaderboard через get_latest_result

**User:** На Free Dune `create_query` падает с 402. Как тогда подключить
Dune к ноутбуку?

**Assistant:** На Free плане API позволяет только **читать** уже
существующие запросы через `get_latest_result(QUERY_ID)` — это бесплатно.
Создавать запросы нужно через UI на dune.com, потом копировать
`query_id` из URL и подставлять в SDK.

```python
from dune_client.client import DuneClient
dune = DuneClient(DUNE_API_KEY)

# Public query 4319 — топ DEX по weekly volume (известно из семинара)
res = dune.get_latest_result(4319)
dex_df = pd.DataFrame(res.result.rows)
print(dex_df.head())
```

Для Aave-специфичных метрик (борроу-объёмы по протоколам, ликвидации) —
публикуем свои запросы в UI и плагаем `query_id` сюда же. SQL для них —
в секции 9 ноутбука.

---

## 7. DeFiLlama — TVL по версиям и dominance

**User:** Покажи как через DeFiLlama посчитать долю Aave в lending-секторе.
Учти что у разных протоколов могут быть разные timestamp в daily snapshots.

**Assistant:** `/protocol/{slug}` отдаёт TVL-серию. Чтобы корректно
просуммировать топ-10 по дням:
1. Floor дат до дня (`dt.floor('D')`).
2. Outer-merge серий, **forward-fill** по столбцам (если протокол в день
   N не репортнул — берём предыдущее значение, не 0).
3. Sum по строке = sector_tvl.
4. Фильтр `sector_tvl > 1e10` отбрасывает раннюю эпоху, когда большинство
   протоколов ещё не существовали (иначе dominance > 100% — мусор).

```python
import requests, pandas as pd

def llama_tvl(slug):
    d = requests.get(f'https://api.llama.fi/protocol/{slug}', timeout=20).json()
    df = pd.DataFrame(d['tvl'])
    df['date'] = pd.to_datetime(df['date'], unit='s').dt.floor('D')
    return df, d

tvl_v1, _ = llama_tvl('aave-v1')
tvl_v2, _ = llama_tvl('aave-v2')
tvl_v3, _ = llama_tvl('aave-v3')

# Топ-N lending-протоколов
all_proto = requests.get('https://api.llama.fi/protocols', timeout=30).json()
lending = pd.DataFrame([p for p in all_proto if p.get('category')=='Lending'])
lending = lending.sort_values('tvl', ascending=False).reset_index(drop=True)
top_slugs = lending.head(10)[['name','slug']].values.tolist()

# Сумма серий
series = []
for name, slug in top_slugs:
    try:
        s = pd.DataFrame(
            requests.get(f'https://api.llama.fi/protocol/{slug}',
                         timeout=20).json()['tvl'])
        s['date'] = pd.to_datetime(s['date'], unit='s').dt.floor('D')
        s = s.drop_duplicates('date', keep='last')
        s = s[['date','totalLiquidityUSD']].rename(
            columns={'totalLiquidityUSD': name})
        series.append(s)
    except: continue

sec = series[0]
for s in series[1:]:
    sec = sec.merge(s, on='date', how='outer')
sec = sec.sort_values('date').reset_index(drop=True)
proto_cols = [c for c in sec.columns if c != 'date']
sec[proto_cols] = sec[proto_cols].ffill().fillna(0)
sec['sector_tvl'] = sec[proto_cols].sum(axis=1)

# Aave total
aave = (tvl_v1[['date','totalLiquidityUSD']].rename(columns={'totalLiquidityUSD':'v1'})
        .merge(tvl_v2[['date','totalLiquidityUSD']].rename(columns={'totalLiquidityUSD':'v2'}), on='date', how='outer')
        .merge(tvl_v3[['date','totalLiquidityUSD']].rename(columns={'totalLiquidityUSD':'v3'}), on='date', how='outer')
        .fillna(0).sort_values('date'))
aave['aave_total'] = aave[['v1','v2','v3']].sum(axis=1)

merged = pd.merge_asof(aave.sort_values('date'),
                       sec[['date','sector_tvl']].sort_values('date'),
                       on='date', direction='nearest')
merged = merged[merged['sector_tvl'] > 1e10].copy()
merged['dominance_%'] = merged['aave_total'] / merged['sector_tvl'] * 100

print(f"Latest Aave TVL: ${merged['aave_total'].iloc[-1]/1e9:.2f}B")
print(f"Sector TVL: ${merged['sector_tvl'].iloc[-1]/1e9:.2f}B")
print(f"Dominance: {merged['dominance_%'].iloc[-1]:.1f}%")
```

Получаем: Aave $13.94B / sector $35.10B = **39.6%**, пик 59.8% в
сентябре 2025.

---

## 8. GeckoTerminal + CoinGecko + Binance — токен AAVE

**User:** Покажи минимальный код для каждого из трёх источников по AAVE.

**Assistant:**

```python
# GeckoTerminal — топ-пулы AAVE на Ethereum
url = f'https://api.geckoterminal.com/api/v2/networks/eth/tokens/{AAVE_TOKEN}/pools'
pools = requests.get(url, timeout=20).json()['data']
pools_df = pd.DataFrame([{
    'pool': p['attributes']['name'],
    'address': p['id'].replace('eth_', ''),
    'volume_24h':  float(p['attributes']['volume_usd']['h24'] or 0),
    'reserve_usd': float(p['attributes']['reserve_in_usd'] or 0),
} for p in pools]).sort_values('volume_24h', ascending=False)

# CoinGecko — 360 дней цены / volume / mcap
cg = requests.get('https://api.coingecko.com/api/v3/coins/aave/market_chart',
                  params={'vs_currency':'usd','days':360}, timeout=20).json()
cg_df = pd.DataFrame(cg['prices'], columns=['ts','price'])
cg_df['datetime'] = pd.to_datetime(cg_df['ts'], unit='ms')
cg_df['volume'] = [v[1] for v in cg['total_volumes']]
cg_df['mcap']   = [v[1] for v in cg['market_caps']]

# Binance — daily klines
kl = requests.get('https://api.binance.com/api/v3/klines',
                  params={'symbol':'AAVEUSDT','interval':'1d','limit':360},
                  timeout=20).json()
bn_df = pd.DataFrame(kl, columns=['open_time','open','high','low','close',
                                   'volume','close_time','qav','trades',
                                   'tbbav','tbqav','ignore'])
bn_df['datetime'] = pd.to_datetime(bn_df['open_time'], unit='ms')
for c in ['open','high','low','close','volume']:
    bn_df[c] = bn_df[c].astype(float)
```

---

## 9. Cross-source price sanity check

**User:** Сравни цену AAVE из 4 источников: Aave Oracle (web3), CoinGecko,
Binance, GeckoTerminal (DEX-weighted).

**Assistant:**

```python
aave_oracle = oracle.functions.getAssetPrice(
    Web3.to_checksum_address(AAVE_TOKEN)).call() / BASE_UNIT
cg_now = float(cg_df['price'].iloc[-1])
bn_now = float(bn_df['close'].iloc[-1])

top_pool = pools_df.iloc[0]
gp = requests.get(
    f'https://api.geckoterminal.com/api/v2/networks/eth/pools/{top_pool["address"]}',
    timeout=15).json()
gecko_price = float(gp['data']['attributes']['base_token_price_usd'])

cmp = pd.DataFrame({
    'source': ['Aave Oracle', 'CoinGecko', 'Binance',
               f'GeckoTerminal ({top_pool["pool"]})'],
    'price_usd': [aave_oracle, cg_now, bn_now, gecko_price],
})
cmp['dev_bps'] = (cmp['price_usd'] - bn_now) / bn_now * 10000
print(cmp)
```

Все 4 источника сходятся в пределах ±10 bps — арбитраж работает,
ноутбук готов как ценовой источник для TWAP.

Также строим hourly spread CoinGecko vs Binance за 14 дней через
`pd.merge_asof(..., tolerance='1h')`. Mean spread ≈ +6.7 bps,
std ≈ 100 bps (низколиквидный токен → больше шума на часовых барах).

---

## 10. Public Dune dashboard (extra)

**User:** SQL для 4 запросов под публичный Dune-дашборд по Aave V3
Ethereum.

**Assistant:** Используем decoded event-таблицы (`Pool_evt_Borrow`,
`Pool_evt_LiquidationCall`). Колонка `"user"` в кавычках — она
зарезервирована в DuneSQL. `amount` хранится в native decimals; для
mixed-decimals резервов точное USD-значение требует джойна с oracle-
таблицей, поэтому даём `approx_amount = amount / 1e18` как proxy.

```sql
-- Q1: Daily borrow events (90d) → Line chart
SELECT date_trunc('day', evt_block_time) AS day,
       COUNT(*) AS borrow_events,
       SUM(amount / POW(10, 18)) AS approx_amount
FROM aave_v3_ethereum.Pool_evt_Borrow
WHERE evt_block_time > NOW() - INTERVAL '90' day
GROUP BY 1 ORDER BY 1;
```

```sql
-- Q2: Top borrowed reserves (30d) → Bar chart
SELECT reserve,
       COUNT(*) AS n_borrows,
       SUM(amount / POW(10, 18)) AS approx_volume
FROM aave_v3_ethereum.Pool_evt_Borrow
WHERE evt_block_time > NOW() - INTERVAL '30' day
GROUP BY 1 ORDER BY n_borrows DESC LIMIT 15;
```

```sql
-- Q3: Daily liquidations (90d) → Bar chart
SELECT date_trunc('day', evt_block_time) AS day,
       COUNT(*) AS n_liquidations
FROM aave_v3_ethereum.Pool_evt_LiquidationCall
WHERE evt_block_time > NOW() - INTERVAL '90' day
GROUP BY 1 ORDER BY 1;
```

```sql
-- Q4: Daily unique borrowers (60d) → Line chart
SELECT date_trunc('day', evt_block_time) AS day,
       COUNT(DISTINCT "user") AS unique_borrowers
FROM aave_v3_ethereum.Pool_evt_Borrow
WHERE evt_block_time > NOW() - INTERVAL '60' day
GROUP BY 1 ORDER BY 1;
```

Шаги публикации: dune.com → New Query → вставить SQL → Run → Save →
+ New visualization → выбрать тип графика → ··· → Add to dashboard →
New Dashboard "HW8 - Aave EDA" (по умолчанию public). Повторить для
4 запросов в один дашборд.

---

## 11. Выводы

**User:** Соберём итоговые выводы по результатам?

**Assistant:**

**Version dynamics.** V3 доминирует ($13.7B), V2 держится остаточно
($132M — sticky LPs не мигрируют), V1 практически мёртв ($7M).
Multichain V3 — 21 чейн, но Ethereum держит ~50% TVL (глубокая
ликвидность стейблов и ETH).

**Sector position.** Aave стабильно ~40% lending-сектора (топ-1).
Конкуренция: Morpho Blue ($6.95B, растёт), Compound ($3B, медленно
проседает), Spark, JustLend. В кризис доля Aave растёт — лендинг
ведёт себя как инфраструктура, не как мода.

**Asset patterns.** Стейблы (USDC/USDT/DAI) идут с utilization 60–90%,
WETH/WBTC 20–50% — классическая risk-tier структура. Borrow APY на
стейблах быстро реагирует на спайки utilization (interest rate model
работает).

**Token AAVE.** Глубокая CEX-ликвидность (Binance), активные
on-chain переводы. Cross-source price agreement в пределах нескольких
bps → эффективный арбитраж.

**Pipeline integrity.** Aave Oracle, CG-aggregated, Binance spot и
DEX-weighted GeckoTerminal сходятся в одном ±10 bps окне. Стэйл-фидов
не вижу.

---

## Артефакты

| Что | Где |
|---|---|
| Ноутбук со всеми outputs | `Aave_HW.ipynb` |
| GitHub repo | https://github.com/SergeySolovyev/DeFi-EDA |
| Dune dashboard | https://dune.com/sssolovjov/hw8-aave-eda |
| Этот транскрипт | `Chat_Transcript.pdf` |
