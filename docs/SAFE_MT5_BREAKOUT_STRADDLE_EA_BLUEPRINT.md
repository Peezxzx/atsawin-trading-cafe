# Safe MT5 Breakout-Straddle EA Blueprint

Status: design blueprint only; not a claim that the Facebook Reel's EA has been identified.

Source reviewed: Facebook Reel preview image only. The Reel itself was not accessible without Facebook authentication.

## Evidence and limits

### Confirmed from the preview

- Platform is strongly indicated as MetaTrader 5 by the visible MetaTrader interface, Tester menu, and Data Window.
- Symbol: `XAUUSD-STDC`.
- Timeframe: `M1`.
- Chart style: candlesticks.
- Visible pending orders:
  - `BUY STOP 0.01 at 4330.07`
  - `SELL STOP 0.01 at 4329.29`
- No EA name, TP, SL, dashboard, indicator name, account information, or complete order lifecycle is readable.

### Interpretation, not confirmation

The visible two-sided pending-order arrangement resembles a breakout straddle. The preview does not prove whether orders are automatically cancelled after one side triggers, whether this is an EA or manual trading, or whether the system uses scalping, trend-following, grid, martingale, averaging, or hedging logic.

This blueprint intentionally does not use martingale, grid expansion, averaging down, or loss-recovery sizing.

## EA concept

`SafeMT5BreakoutStraddle` is a conservative MT5 pending-breakout EA:

1. During a configured session, calculate a recent high/low range.
2. Place one Buy Stop above the range and one Sell Stop below it.
3. Apply fixed-lot or risk-percent sizing.
4. When one side triggers, cancel the opposite pending order.
5. Allow only limited trades and one active cycle per symbol/magic number.
6. Enforce spread, daily-loss, drawdown, session, and broker-volume protections.

## Entry rules

1. Trading must be enabled and inside the configured session.
2. Spread must be at or below `MaxSpreadPoints`.
3. Daily loss, drawdown, trade-count, and cooldown protections must allow a new cycle.
4. There must be no existing EA position or pending orders for the symbol and magic number.
5. Calculate the high and low of the previous `RangeBars` completed candles on `RangeTimeframe`.
6. Reject the range if it is smaller than `MinRangePoints` or larger than `MaxRangePoints`.
7. Place:
   - Buy Stop at `RangeHigh + EntryBufferPoints`.
   - Sell Stop at `RangeLow - EntryBufferPoints`.
8. Pending orders must have an expiration time.
9. Each order must include the configured SL and TP at placement time when broker constraints permit.

Optional future filters: ATR range filter, minimum candle quality, news blackout, and breakout-close confirmation. These should be added only after baseline testing.

## Exit and order-management rules

- Fixed stop loss in points, enabled by default.
- Fixed take profit in points, enabled by default.
- Optional break-even after a configured profit threshold.
- Optional trailing stop after a configured profit threshold.
- Cancel the opposite pending order after one side becomes a market position.
- Delete untriggered pending orders at session end when enabled.
- Delete expired pending orders.
- Optionally close EA positions at session end.
- If daily-loss or maximum-drawdown protection triggers, delete pending orders and optionally close EA positions.
- Never increase lot size after a loss.
- Never add positions to a losing trade.

## Input parameters

```mql5
// General
input ulong  InpMagicNumber          = 250601;
input bool   InpEnableTrading        = true;
input ENUM_TIMEFRAMES InpRangeTF     = PERIOD_M1;

// Position sizing
input bool   InpUseRiskPercent       = false;
input double InpFixedLot             = 0.01;
input double InpRiskPercent           = 0.50;

// Range and entry
input int    InpRangeBars            = 10;
input int    InpEntryBufferPoints    = 50;
input int    InpMinRangePoints       = 100;
input int    InpMaxRangePoints       = 3000;

// Execution limits
input int    InpMaxSpreadPoints      = 100;
input int    InpMaxTradesPerDay      = 2;
input int    InpMaxOpenPositions     = 1;
input int    InpPendingExpiryMinutes = 30;
input int    InpCooldownMinutes      = 15;

// Stops and targets
input bool   InpUseStopLoss           = true;
input int    InpStopLossPoints        = 500;
input bool   InpUseTakeProfit         = true;
input int    InpTakeProfitPoints      = 750;

// Trade management
input bool   InpUseTrailingStop       = true;
input int    InpTrailingStartPoints   = 400;
input int    InpTrailingStopPoints    = 250;
input int    InpTrailingStepPoints    = 50;
input bool   InpUseBreakEven          = true;
input int    InpBreakEvenTriggerPts   = 300;
input int    InpBreakEvenOffsetPoints = 20;

// Trading session, in broker server time
input bool   InpUseTradingSession     = true;
input int    InpSessionStartHour      = 7;
input int    InpSessionStartMinute    = 0;
input int    InpSessionEndHour        = 17;
input int    InpSessionEndMinute      = 0;

// Equity protection
input double InpDailyLossLimitMoney   = 100.0;
input double InpDailyLossLimitPercent = 2.0;
input double InpMaxDrawdownPercent    = 5.0;
input bool   InpCloseOnProtection     = true;

// Behavior
input bool   InpCancelOppositeOnFill  = true;
input bool   InpDeleteAtSessionEnd    = true;
input bool   InpOneCyclePerDay        = false;
```

Lot sizing must use the broker's actual `SYMBOL_TRADE_TICK_SIZE`, `SYMBOL_TRADE_TICK_VALUE`, volume minimum, maximum, and volume step. Do not assume a universal gold pip value.

## Dashboard design

```text
SAFE BREAKOUT EA
-----------------------------
Symbol:           XAUUSD-STDC
Timeframe:        M1
EA Status:        ACTIVE / BLOCKED
Session:          OPEN / CLOSED
Spread:           42 pts / Max 100
Range:            4328.50 - 4329.80
Buy Stop:         4330.07
Sell Stop:        4329.29
Open Positions:   0 / 1
Trades Today:     0 / 2
Daily P/L:        $0.00
Daily Loss Limit: $100.00
Drawdown:         0.00% / 5.00%
Risk Mode:        FIXED LOT / RISK %
Protection:       OK
```

Use green for allowed trading, yellow for inactive/session states, and red for protection blocks or execution failures.

## Pseudocode

```text
OnInit:
    validate inputs and broker symbol constraints
    initialize daily baseline equity and date
    create dashboard

OnTick:
    reset daily counters when date changes
    update dashboard

    if disabled: return
    if daily loss or drawdown limit reached:
        delete pending orders
        optionally close EA positions
        block new trading
        return

    manage open positions using break-even and trailing stop

    if outside session:
        optionally delete pending orders
        return
    if spread too high: return
    if daily trade limit reached: return
    if an EA position or pending order exists: return
    if cooldown is active: return

    calculate previous completed-candle range
    if range invalid: return

    calculate fixed or risk-based lot size
    place Buy Stop above range
    place Sell Stop below range

OnTradeTransaction:
    if an EA pending order becomes a market position:
        increment daily trade count
        cancel the opposite pending order

OnDeinit:
    remove dashboard objects
```

## MQL5 code structure

```mql5
#include <Trade/Trade.mqh>

CTrade trade;
datetime g_dayStart;
double   g_dayStartEquity;
int      g_tradesToday = 0;
bool     g_protectionTriggered = false;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   if(!ValidateInputs()) return INIT_PARAMETERS_INCORRECT;
   InitializeDailyState();
   CreateDashboard();
   return INIT_SUCCEEDED;
}

void OnTick()
{
   UpdateDailyState();
   UpdateDashboard();
   if(!InpEnableTrading) return;

   if(IsProtectionTriggered())
   {
      HandleProtection();
      return;
   }

   ManageOpenPositions();

   if(!IsTradingSession())
   {
      if(InpDeleteAtSessionEnd) DeletePendingOrders();
      return;
   }

   if(!IsSpreadAcceptable()) return;
   if(g_tradesToday >= InpMaxTradesPerDay) return;
   if(HasOpenPosition() || HasPendingOrders()) return;
   if(IsCooldownActive()) return;

   double rangeHigh = 0.0, rangeLow = 0.0;
   if(!CalculateRange(rangeHigh, rangeLow)) return;
   if(!IsRangeValid(rangeHigh, rangeLow)) return;

   double lot = CalculateLotSize(rangeHigh, rangeLow);
   PlaceBreakoutOrders(rangeHigh, rangeLow, lot);
}

void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(!IsOurTransaction(trans)) return;
   if(IsPositionOpenedFromPendingOrder(trans))
   {
      g_tradesToday++;
      if(InpCancelOppositeOnFill)
         DeleteOppositePendingOrder(trans);
   }
}

void OnDeinit(const int reason)
{
   DeleteDashboard();
}
```

Recommended helper functions:

```mql5
bool ValidateInputs();
void InitializeDailyState();
void UpdateDailyState();
bool IsProtectionTriggered();
void HandleProtection();
bool IsTradingSession();
bool IsSpreadAcceptable();
bool IsCooldownActive();
bool CalculateRange(double &high, double &low);
bool IsRangeValid(double high, double low);
double CalculateLotSize(double high, double low);
double CalculateRiskBasedLot(double stopDistancePoints);
double NormalizeVolume(double volume);
bool PlaceBreakoutOrders(double high, double low, double lot);
bool HasOpenPosition();
bool HasPendingOrders();
void DeletePendingOrders();
void DeleteOppositePendingOrder(const MqlTradeTransaction &trans);
void ManageOpenPositions();
void ApplyBreakEven(ulong ticket);
void ApplyTrailingStop(ulong ticket);
double GetDailyLoss();
double GetCurrentDrawdownPercent();
void CreateDashboard();
void UpdateDashboard();
void DeleteDashboard();
```

## Backtest and forward-test plan

1. Validate exact broker symbol properties: tick size, tick value, contract size, minimum/maximum/step volume, stop level, freeze level, spread, and server time.
2. Backtest on high-quality tick data for `XAUUSD-STDC` and M1 data.
3. Begin with `0.01` fixed lot and all protections enabled.
4. Measure net profit, profit factor, maximum drawdown, recovery factor, win rate, trade count, consecutive losses, slippage, spread sensitivity, and performance by session/day.
5. Test variable spread, commission, and randomized slippage.
6. Perform parameter perturbation, walk-forward, out-of-sample, and Monte Carlo trade-order tests.
7. Run on demo for multiple weeks and log order rejection, pending-order cancellation, actual spread, slippage, protection events, and session handling.
8. Only after stable demo and out-of-sample results, consider a minimum-size live test. Never disable daily loss and drawdown protections.

## Evidence still required for EA identification

To identify the original EA rather than only its visible pattern, obtain:

- Full screen recording of the Reel, or high-resolution frames before and after entries.
- Full chart header and upper-right EA label.
- Navigator panel showing the EA filename.
- EA Inputs window.
- Experts and Journal tabs.
- Positions, Orders, and Account History tabs.
- Any readable dashboard or watermark.

No original EA name should be inferred from the available preview.
