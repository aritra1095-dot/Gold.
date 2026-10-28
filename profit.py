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
TRANSACTION_COST_BPS = 0.0005  # 5 bps per trade execution

date_records = {}

# 1. Parse and Normalize Data
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
                    norm_price = round((close_price / UNITS[symbol]) * (1000.0 / PURITY[symbol]), 2)
                    if date not in date_records:
                        date_records[date] = {}
                    date_records[date][symbol] = norm_price
    except Exception as e:
        pass

# Sort dates chronologically
sorted_dates = sorted(date_records.keys())

# 2. Build Strategy Performance Series
records = []
for date in sorted_dates:
    prices = date_records[date]
    if "GOLDM" in prices and "GOLDTEN" in prices:
        records.append({
            "Date": date,
            "GOLDM": prices["GOLDM"],
            "GOLDTEN": prices["GOLDTEN"],
            "Spread": round(prices["GOLDTEN"] - prices["GOLDM"], 2)
        })

# 3. Walk-Forward Backtest
window_size = 5
current_position = 0  # 0: Flat, +1: Long Spread, -1: Short Spread
total_gross_pnl = 0.0
total_costs = 0.0
total_net_pnl = 0.0

print("\n" + f"{'Date':<12} | {'Pos':<4} | {'Spread Change':<14} | {'Gross PnL':<10} | {'Cost':<6} | {'Net PnL':<10}")
print("-" * 75)

for i in range(len(records)):
    if i < window_size:
        records[i]["Position"] = 0
        records[i]["Net_PnL"] = 0.0
        continue
    
    # Calculate Z-Score
    window_spreads = [records[j]["Spread"] for j in range(i - window_size, i)]
    mean = sum(window_spreads) / window_size
    variance = sum((x - mean) ** 2 for x in window_spreads) / window_size
    std = math.sqrt(variance) if variance > 0 else 0.0001
    z_score = (records[i]["Spread"] - mean) / std
    
    # Determine New Position
    new_position = current_position
    if z_score > 1.5:
        new_position = -1  # Short Spread
    elif z_score < -1.5:
        new_position = 1   # Long Spread
    elif abs(z_score) < 0.2:
        new_position = 0   # Close Position
        
    # Calculate Daily PnL
    spread_change = records[i]["Spread"] - records[i-1]["Spread"]
    gross_pnl = current_position * spread_change
    
    # Transaction cost if position changed
    trade_cost = 0.0
    if new_position != current_position:
        trade_cost = records[i]["GOLDM"] * TRANSACTION_COST_BPS
        
    net_pnl = gross_pnl - trade_cost
    
    # Update Totals
    total_gross_pnl += gross_pnl
    total_costs += trade_cost
    total_net_pnl += net_pnl
    
    records[i]["Position"] = new_position
    records[i]["Gross_PnL"] = round(gross_pnl, 2)
    records[i]["Cost"] = round(trade_cost, 2)
    records[i]["Net_PnL"] = round(net_pnl, 2)
    
    current_position = new_position
    
    if i >= len(records) - 15:  # Display last 15 days
        print(f"{records[i]['Date']:<12} | {new_position:<4} | {spread_change:<14.2f} | {gross_pnl:<10.2f} | {trade_cost:<6.2f} | {net_pnl:<10.2f}")

# 4. Print Executive Backtest Summary
print("\n" + "=" * 45)
print("       FINAL BACKTEST PERFORMANCE SUMMARY       ")
print("=" * 45)
print(f"Total Trading Days Backtested : {len(records) - window_size}")
print(f"Total Gross Alpha PnL        : ₹{total_gross_pnl:.2f} / gram")
print(f"Total Transaction Costs Deducted: ₹{total_costs:.2f} / gram")
print(f"NET ALPHA PnL (After Costs)  : ₹{total_net_pnl:.2f} / gram")
print("=" * 45)

# Save Final Backtest Results
output_path = os.path.join(download_folder, "Final_Backtest_Performance.csv")
with open(output_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "GOLDM", "GOLDTEN", "Spread", "Position", "Gross_PnL", "Cost", "Net_PnL"])
    for r in records:
        writer.writerow([r.get("Date"), r.get("GOLDM"), r.get("GOLDTEN"), r.get("Spread"), r.get("Position", 0), r.get("Gross_PnL", 0.0), r.get("Cost", 0.0), r.get("Net_PnL", 0.0)])

print(f"\nFinal backtest report saved to '{output_path}'")
