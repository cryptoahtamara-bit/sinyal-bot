import requests

# =========================================================
# FINAL MEXC FUTURES PATCH
# =========================================================

contract_cache = {}

# =========================================================
# SYMBOL FORMATTER
# =========================================================

def mexc_format_symbol(symbol: str):
    symbol = symbol.upper()

    # BTCUSDT.P -> BTCUSDT
    symbol = symbol.replace(".P", "")

    # BTCUSDT -> BTC_USDT
    if symbol.endswith("USDT") and "_USDT" not in symbol:
        symbol = symbol.replace("USDT", "_USDT")

    return symbol

# =========================================================
# CONTRACT DETAIL FETCHER
# =========================================================

def get_contract_detail(symbol, base_url):
    global contract_cache

    if symbol in contract_cache:
        return contract_cache[symbol]

    url = f"{base_url}/api/v1/contract/detail"

    r = requests.get(url, timeout=10)
    data = r.json()

    if not data.get("success"):
        raise Exception(f"Contract detail alınamadı: {data}")

    for item in data.get("data", []):
        if item["symbol"] == symbol:
            contract_cache[symbol] = item
            return item

    raise Exception(f"Contract bulunamadı: {symbol}")

# =========================================================
# REAL CONTRACT VOLUME CALCULATION
# =========================================================

def calculate_contract_volume(
    symbol,
    price,
    leverage,
    margin_usdt,
    base_url
):
    detail = get_contract_detail(symbol, base_url)

    contract_size = float(detail.get("contractSize", 0.0001))
    min_vol = float(detail.get("minVol", 1))
    vol_scale = int(detail.get("volScale", 0))

    notional = margin_usdt * leverage

    raw_contracts = notional / (price * contract_size)

    volume = round(raw_contracts, vol_scale)

    if volume < min_vol:
        volume = min_vol

    return volume

# =========================================================
# LEVERAGE FIX
# =========================================================

def parse_max_leverage(data, default_leverage=20):
    d = data.get("data")

    if isinstance(d, list):
        d = d[0]

    return int(d.get("maxLeverage", default_leverage))

# =========================================================
# SIDE MAPPING
# =========================================================

def get_mexc_side(signal):
    if signal in ["LONG", "STRONG BUY"]:
        return 1  # Open Long
    else:
        return 2  # Open Short

# =========================================================
# ORDER BODY CREATOR
# =========================================================

def create_market_order_body(
    symbol,
    volume,
    side,
    leverage
):
    return {
        "symbol": symbol,
        "price": 0,
        "vol": volume,
        "side": side,
        "type": 5,
        "openType": 2,
        "leverage": leverage,
    }

# =========================================================
# EXAMPLE USAGE
# =========================================================

if __name__ == "__main__":

    MEXC_BASE_URL = "https://contract.mexc.com"

    MEXC_MARGIN_USDT = 0.25

    raw_symbol = "BTCUSDT.P"

    formatted_symbol = mexc_format_symbol(raw_symbol)

    mark_price = 100000

    leverage = 125

    volume = calculate_contract_volume(
        formatted_symbol,
        mark_price,
        leverage,
        MEXC_MARGIN_USDT,
        MEXC_BASE_URL
    )

    side = get_mexc_side("LONG")

    order_body = create_market_order_body(
        formatted_symbol,
        volume,
        side,
        leverage
    )

    print("[MEXC] Symbol:", formatted_symbol)
    print("[MEXC] Volume:", volume)
    print("[MEXC] Order Body:", order_body)
