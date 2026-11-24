================================================================================
                                 CryptoChain
               Bitcoin and Ether options on Delta Exchange India
================================================================================

WHAT IS CRYPTOCHAIN?
--------------------
CryptoChain is a browser dashboard for the Bitcoin (BTC) and Ether (ETH)
options listed on Delta Exchange India. For one expiry at a time it shows:
- the option chain as a table: calls on the left, puts on the right, one row
  per strike, with open interest, volume, the six-hour change in open
  interest, implied volatility, last traded price and the put/call ratio;
- or a page of charts built from the same figures, including Delta's own
  Greeks (delta, gamma, vega, theta) by strike.

All data comes from Delta Exchange India's public market data
(https://api.india.delta.exchange). No account and no key are needed. The app
runs in Docker and is reachable only from your own computer.

Calls are shown in red and puts in green, in the table and in every chart.

Please read DATA LIMITATIONS below before relying on any of its figures.


SYSTEM REQUIREMENTS
-------------------
- Docker Desktop: https://www.docker.com/products/docker-desktop
  (Windows 10/11, macOS, or Linux with Docker). Python does not need to be
  installed on your computer.
- An internet connection.


STARTING AND STOPPING
---------------------
1. Install Docker Desktop, start it, and wait until it is running.
2. Start:  double-click crypto.command (macOS) or crypto.bat (Windows).
   If macOS will not open it, right-click it and choose Open.
   On Linux, run  docker compose up -d --build  in this folder (or
   docker-compose up -d --build  on older installs) and open
   http://localhost:8501 yourself.
   The script builds the app (only what changed is rebuilt), starts it,
   waits 6 seconds and opens http://localhost:8501. The first start downloads
   and installs everything and can take a few minutes -- refresh the page
   once it has finished.
3. Stop:   double-click STOP-crypto.command or STOP-crypto.bat.

The dashboard is published on this computer only (127.0.0.1:8501), not to
other devices on your network. It stores nothing: every figure is fetched
from Delta when you ask for it.


USING THE DASHBOARD
-------------------
The sidebar, top to bottom:

Crypto Asset   Bitcoin (BTC) or Ethereum (ETH). Choosing one fetches the list
               of expiries from Delta afresh, every time.
Expiry         The expiry dates Delta lists for that asset, nearest first.
Strike Range   How many strikes to show either side of the strike nearest the
               current price: +-8, +-10 (the default), +-12, +-16, +-32, or
               All Strikes.
View           Chain (the table) or Charts.
Auto Refresh   Chain view only: Off, 1s, 5s, 30s, 1m, 5m or 30m. While it is
               on, the table is fetched again at that interval. The page
               checks once a second, so "1s" refreshes about every 2 seconds.
Run            Fetches the option chain for the chosen asset and expiry.
               A new strike range takes effect on the next Run; switching
               View shows the data already fetched straight away.


THE TABLE (CHAIN VIEW)
----------------------
Column headers end in (CE) for calls and (PE) for puts. From left to right:
PCR (OI/Vol), then the call columns IV, OI Change (6h), OI, Volume, LTP, then
STRIKE, then the same five columns for puts in mirror order.

How every figure is arrived at:

OI (open interest)
   Top line: a DOLLAR figure, not a number of contracts:
      open interest in coins x strike price
   shown as $X.XM (millions), $X.XK (thousands) or $X.
   Bracketed below: the open interest itself, in coins (BTC or ETH), to two
   decimals -- exactly as Delta reports it.
   Example, Bitcoin 66,000 call, 26 Nov 2026 expiry, 24 Nov 2026: Delta
   reported open interest of 39.952 BTC. The cell shows
      $2.6M   (39.95)
   because 39.952 x 66,000 = $2,636,832.
   The dollar figure is valued at the STRIKE price, not at the current price
   of Bitcoin, so it differs from a value at the current price (Delta's own
   figure for this contract, at a Bitcoin price of 60,287.50, was
   $2,392,857). One Delta Bitcoin option contract is 0.001 BTC and one Ether
   contract is 0.01 ETH, so 39.952 BTC is 39,952 contracts.

Volume
   Worked out the same way: the volume traded, in coins, x the strike price,
   as a dollar figure; the volume in coins (two decimals) in brackets below.
   Example: 0.56 BTC traded in the 67,200 put shows $37.6K (0.56).

OI Change (6h)
   Delta's own figure for the change in open interest over the last six
   hours, in US DOLLARS (Delta names it oi_change_usd_6h). It is not a number
   of contracts and not a number of coins. Shown with K or M, green when open
   interest grew, red when it fell.

IV
   Delta's mark implied volatility for the contract, as an annual percentage.
   Delta sends it as a decimal (0.62); the table shows 62.00.

LTP
   The option's last traded price, in US dollars ("-" if it has not traded).

PCR (OI/Vol)
   The put/call ratio at that strike: put open interest / call open interest
   (three decimals), and below it in brackets put volume / call volume.
   "-" when either side is zero.

STRIKE
   The strike price, in US dollars.

The highlighted row between two strikes is the current price of Bitcoin or
Ether, as Delta attaches it to the options (its spot price).

The TOTALS row adds up open interest and volume (dollar figure and coins) and
the six-hour change in open interest, for calls and for puts separately.

Highlights, on each side (calls and puts) separately:
- OI and Volume: the strike with the largest dollar figure has a dark green
  background, the second largest a dark yellow background, the third a blue
  border.
- OI Change (6h): the largest increase has a green border, the largest
  decrease a red border.


THE CHARTS (CHARTS VIEW)
------------------------
- IV Smile Curve: implied volatility (%) by strike, calls and puts.
- Open Interest Distribution: open interest in coins by strike (square-root
  scale, so small bars stay visible).
- OI Change (6h) Distribution: the six-hour change in open interest, in US
  dollars, by strike.
- Volume Distribution: volume in coins by strike (square-root scale).
- Support & Resistance Levels: the three call strikes with the most open
  interest (resistance) and the three put strikes with the most (support),
  as horizontal bars of open interest in coins. The two largest of each are
  marked "Strong", the third "Moderate".
- Delta, Gamma, Vega and Theta Distribution: Delta's own Greeks for every
  contract, by strike, as Delta publishes them. The app does not calculate
  Greeks.

The dashed orange line on the IV, open-interest, OI-change, volume and
support/resistance charts is the current price. On the bar charts each call
bar sits just left of its strike and each put bar just right of it, on a
numeric strike axis; as many strike labels are shown as fit the chart's
width. The same applies to the support/resistance chart: when levels sit
close together (60,000, 60,200 and 60,400, for example), only the labels that
fit are shown -- hover over a bar to see its strike. Hovering over a bar or
point shows its figures; on every chart except
support/resistance it also shows whether the option is in the money (ITM),
at the money (ATM, within 2% of the current price) or out of the money (OTM)
-- a call is in the money below the current price, a put above it. Chart
text follows Streamlit's light or dark page.


DATA LIMITATIONS -- READ THIS
-----------------------------
- Every figure is Delta Exchange India's, as its public market data reports
  it at the moment you press Run. The app does not store or check them.
- Many strikes, especially far from the current price, trade little or not
  at all: expect empty cells, "-" and very small figures there.
- The dollar figures for open interest and volume are valued at the strike
  price (see THE TABLE), not at the current price and not at the option's
  premium.
- "OI Change (6h)" is Delta's own measure, over Delta's six-hour window.
- Implied volatility and the Greeks are Delta's own model figures; for
  contracts that have not traded they are not the result of any trade.
- Delta can change, delay or withdraw its public data at any time, and its
  own terms govern the use of that data. CryptoChain is not affiliated with
  Delta Exchange.


TROUBLESHOOTING
---------------
"Docker Desktop is not running"
   Start Docker Desktop, wait until it is running, then start the app again.

"Port 8501 already in use"
   Another program is using port 8501 (another dashboard, for example).
   Stop it, or run STOP-crypto first.

The page does not load
   Wait a minute -- the first start installs everything -- then refresh.
   Check in Docker Desktop that the cryptochain container is running.

"No expiry dates available", "No data received ...", "Failed to ..."
   Delta could not be reached, or listed nothing for that choice. Check your
   internet connection and try again; each request to Delta is retried three
   times before the message appears.


TECHNICAL DETAILS
-----------------
- Python 3.11 (in the container), Streamlit, Altair, pandas, NumPy, requests.
- Container name: cryptochain. Port: 8501, on this computer only.
- Requests to Delta are spaced at least 1 second apart and retried three
  times, waiting longer after each failure.
- Files:
     app.py              the page, the sidebar and the table
     integrated.py       fetches from Delta and works out the totals
     visualization.py    the charts
     styles.css          the table's colours and layout
     .streamlit/config.toml   Streamlit settings
     Dockerfile, docker-compose.yml, .dockerignore
     crypto.* / STOP-crypto.*   double-click start and stop scripts


LICENCE
-------
MIT - see LICENSE. Streamlit, Altair, pandas, NumPy and requests are
installed by pip from requirements.txt and keep their own licences. The
market data is Delta Exchange India's; Delta's own terms govern its use.


================================================================================
                    From ChorBazaar - https://chorbazaar.co.in
================================================================================
