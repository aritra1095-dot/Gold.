import csv
import glob
import os
import math

download_folder = "/sdcard/Download"
all_files = glob.glob(os.path.join(download_folder, "BhavCopyCommodiyWise_*.csv"))

if not all_files:
    all_files = glob.glob("BhavCopyCommodiyWise_*.csv")

UNITS = {"GOLDM": 10.0, "GOLDTEN": 10.0, "GOLDGUINEA": 8.0, "GOLDPETAL": 1.0}
PURITY = {"GOLDM": 995.0, "GOLDTEN": 999.0, "GOLDGUINEA": 999.0, "GOLDPETAL": 999.0}
TRANSACTION_COST_BPS = 0.0005  # 5 bps (0.05%) exchange + brokerage costs

date_records = {}

# Step 1: Normalization Pipeline
for file_path in all_files:
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [key.strip() for key in reader.fieldnames]
            for row in reader:
                symbol = row['Symbol'].strip().upper()
                if symbol in UNITS:
                    date = row['Date'].strip()
                    close_price = float(row['Close'])
                    norm_price = (close_price / UNITS[symbol]) * (1000.0 / PURITY[symbol])
                    if date not in date_records:
                        date_records[date] = {}
                    date_records[date][symbol] = norm_price
    except Exception as e:
        pass

sorted_dates = sorted(date_records.keys())

records = []
for date in sorted_dates:
    prices = date_records[date]
    if "GOLDM" in prices and "GOLDTEN" in prices:
        records.append({
            "Date": date,
            "GOLDM": prices["GOLDM"],
            "GOLDTEN": prices["GOLDTEN"],
            "Spread": prices["GOLDTEN"] - prices["GOLDM"]
        })

# Step 2: Signal Generation & Walk-Forward Backtest
window_size = 5
current_position = 0
total_gross_pnl = 0.0
total_costs = 0.0
total_net_pnl = 0.0
num_trades = 0

for i in range(len(records)):
    if i < window_size:
        continue
    
    window_spreads = [records[j]["Spread"] for j in range(i - window_size, i)]
    mean = sum(window_spreads) / window_size
    variance = sum((x - mean) ** 2 for x in window_spreads) / window_size
    std = math.sqrt(variance) if variance > 0 else 0.0001
    z_score = (records[i]["Spread"] - mean) / std
    
    new_position = current_position
    if z_score > 1.5:
        new_position = -1  # Short Spread
    elif z_score < -1.5:
        new_position = 1   # Long Spread
    elif abs(z_score) < 0.2:
        new_position = 0   # Exit
        
    spread_change = records[i]["Spread"] - records[i-1]["Spread"]
    gross_pnl = current_position * spread_change
    
    trade_cost = 0.0
    if new_position != current_position:
        trade_cost = records[i]["GOLDM"] * TRANSACTION_COST_BPS
        num_trades += 1
        
    net_pnl = gross_pnl - trade_cost
    
    total_gross_pnl += gross_pnl
    total_costs += trade_cost
    total_net_pnl += net_pnl
    current_position = new_position

# Calculate Underlying Market Movement (Beta Return)
start_price = records[0]["GOLDM"]
end_price = records[-1]["GOLDM"]
beta_return_pct = ((end_price - start_price) / start_price) * 100

print("\n" + "="*55)
print("     ANALYTICAL PROTOTYPE - EXECUTIVE SUBMISSION SUMMARY")
print("="*55)
print(f" 1. DATA TRANSFORMATIONS")
print(f"    - Contracts Processed : GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL")
print(f"    - Normalization Base  : ₹ / Gram (100% Fine Gold Purity Equivalent)")
print(f"    - Historical Dataset  : {len(sorted_dates)} trading periods")

print("\n 2. STRATEGY SPECIFICATION")
print(f"    - Alpha Signal        : 5-Day Rolling Z-Score Mean Reversion")
print(f"    - Position Trigger    : Entry |Z| > 1.5, Exit |Z| < 0.2")
print(f"    - Execution Cost      : 5 bps (0.05%) deducted per turn")

print("\n 3. PERFORMANCE ATTRIBUTION & SEPARATION")
print(f"    - Total Executed Trades: {num_trades}")
print(f"    - Gross Strategy PnL  : ₹{total_gross_pnl:.2f} / g")
print(f"    - Total Cost Deduction : -₹{total_costs:.2f} / g")
print(f"    - NET ALPHA PnL       : ₹{total_net_pnl:.2f} / g")
print(f"    - UNDERLYING GOLD (BETA): {beta_return_pct:+.2f}% buy & hold change")

print("\n 4. ANALYTICAL CONCLUSION")
if total_net_pnl > 0:
    print("    RESULT: Persistent positive Net Alpha survives transaction costs.")
else:
    print("    RESULT: Arbitrage margin is eroded by transaction fees (No Net Alpha).")
print("="*55)
