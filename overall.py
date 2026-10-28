import csv
import glob
import os
import math

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
download_folder = "/sdcard/Download"
all_files = glob.glob(os.path.join(download_folder, "BhavCopyCommodiyWise_*.csv"))

if not all_files:
    all_files = glob.glob("BhavCopyCommodiyWise_*.csv")

# Contract Lot Sizes (Grams) and Purity (per thousand)
UNITS = {"GOLDM": 10.0, "GOLDTEN": 10.0, "GOLDGUINEA": 8.0, "GOLDPETAL": 1.0}
PURITY = {"GOLDM": 995.0, "GOLDTEN": 999.0, "GOLDGUINEA": 999.0, "GOLDPETAL": 999.0}

# Transaction Friction: 5 bps (0.05%) deducted per position change
TRANSACTION_COST_BPS = 0.0005  

print(f"Found {len(all_files)} raw settlement files.")

# ==============================================================================
# TOPIC 1: DATA NORMALIZATION & MULTI-CONTRACT PIVOTING
# ==============================================================================
date_records = {}
raw_normalized_list = []

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
                    expiry = row.get('Expiry Date', 'N/A').strip()
                    volume = row.get('Volume(Lots)', 'N/A')
                    
                    unit = UNITS[symbol]
                    purity = PURITY[symbol]
                    
                    # Exact Normalization Formula: (Close / Lot_Size) * (1000 / Purity)
                    norm_price = round((close_price / unit) * (1000.0 / purity), 2)
                    
                    # Detailed Unpivoted Dataset
                    raw_normalized_list.append([
                        date, symbol, expiry, close_price, unit, purity, norm_price, volume
                    ])
                    
                    # Pivoted Storage by Date
                    if date not in date_records:
                        date_records[date] = {}
                    date_records[date][symbol] = norm_price
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")

sorted_dates = sorted(date_records.keys())

# Save Output 1: Standardized Granular Records
output1_path = os.path.join(download_folder, "Normalized_Output_Mobile.csv")
with open(output1_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "Symbol", "Expiry", "Close", "Unit", "Purity", "Normalized_Price", "Volume"])
    writer.writerows(raw_normalized_list)

# Save Output 2: Side-by-Side Pivoted Comparison
pivoted_rows = []
for date in sorted_dates:
    prices = date_records[date]
    pivoted_rows.append([
        date,
        prices.get("GOLDM", "N/A"),
        prices.get("GOLDTEN", "N/A"),
        prices.get("GOLDGUINEA", "N/A"),
        prices.get("GOLDPETAL", "N/A")
    ])

output2_path = os.path.join(download_folder, "Normalized_All_Gold_Types.csv")
with open(output2_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "GOLDM_1g", "GOLDTEN_1g", "GOLDGUINEA_1g", "GOLDPETAL_1g"])
    writer.writerows(pivoted_rows)

print("\n" + "="*70)
print("TOPIC 1 OUTPUT: SIDE-BY-SIDE NORMALIZED PRICES (₹/g)")
print("="*70)
print(f"{'Date':<12} | {'GOLDM':<10} | {'GOLDTEN':<10} | {'GOLDGUINEA':<10} | {'GOLDPETAL':<10}")
print("-" * 70)
for row in pivoted_rows[-8:]:
    print(f"{row[0]:<12} | {str(row[1]):<10} | {str(row[2]):<10} | {str(row[3]):<10} | {str(row[4]):<10}")


# ==============================================================================
# TOPIC 2: SPREAD MODELING & ROLLING Z-SCORE SIGNALS
# ==============================================================================
spread_records = []
for row in pivoted_rows:
    date, goldm, goldten, goldguinea, goldpetal = row
    if isinstance(goldm, (int, float)) and isinstance(goldten, (int, float)):
        spread = round(goldten - goldm, 2)
        spread_records.append({
            "Date": date, "GOLDM": goldm, "GOLDTEN": goldten, "Spread": spread
        })

window_size = 5
for i in range(len(spread_records)):
    if i < window_size - 1:
        spread_records[i]["Mean"] = "N/A"
        spread_records[i]["Std"] = "N/A"
        spread_records[i]["Z_Score"] = "N/A"
        spread_records[i]["Signal"] = "NEUTRAL / HOLD"
    else:
        window_spreads = [spread_records[j]["Spread"] for j in range(i - window_size + 1, i + 1)]
        mean = sum(window_spreads) / window_size
        variance = sum((x - mean) ** 2 for x in window_spreads) / window_size
        std = math.sqrt(variance) if variance > 0 else 0.0001
        
        z_score = round((spread_records[i]["Spread"] - mean) / std, 2)
        
        # Signal Generation Rules
        if z_score > 1.5:
            signal = "SELL GOLDTEN / BUY GOLDM"
        elif z_score < -1.5:
            signal = "BUY GOLDTEN / SELL GOLDM"
        else:
            signal = "NEUTRAL / HOLD"
            
        spread_records[i]["Mean"] = round(mean, 2)
        spread_records[i]["Std"] = round(std, 2)
        spread_records[i]["Z_Score"] = z_score
        spread_records[i]["Signal"] = signal

# Save Output 3: Trading Signals CSV
output3_path = os.path.join(download_folder, "Gold_Spread_Trading_Signals.csv")
with open(output3_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "GOLDM", "GOLDTEN", "Spread", "Mean", "Std", "Z_Score", "Signal"])
    for r in spread_records:
        writer.writerow([r["Date"], r["GOLDM"], r["GOLDTEN"], r["Spread"], r["Mean"], r["Std"], r["Z_Score"], r["Signal"]])

print("\n" + "="*70)
print("TOPIC 2 OUTPUT: SPREAD & Z-SCORE TRADING SIGNALS")
print("="*70)
print(f"{'Date':<12} | {'Spread (₹)':<10} | {'Z-Score':<8} | {'Signal':<25}")
print("-" * 70)
for r in spread_records[-8:]:
    print(f"{r['Date']:<12} | {str(r['Spread']):<10} | {str(r['Z_Score']):<8} | {r['Signal']:<25}")


# ==============================================================================
# TOPIC 3: WALK-FORWARD BACKTEST, TRANSACTION COSTS & BETA SEPARATION
# ==============================================================================
current_position = 0
total_gross_pnl = 0.0
total_costs = 0.0
total_net_pnl = 0.0
num_trades = 0

print("\n" + "="*75)
print("TOPIC 3 OUTPUT: WALK-FORWARD BACKTEST EXECUTION TABLE")
print("="*75)
print(f"{'Date':<12} | {'Pos':<4} | {'Spread Change':<14} | {'Gross PnL':<10} | {'Cost':<6} | {'Net PnL':<10}")
print("-" * 75)

for i in range(len(spread_records)):
    if i < window_size:
        spread_records[i]["Position"] = 0
        spread_records[i]["Gross_PnL"] = 0.0
        spread_records[i]["Cost"] = 0.0
        spread_records[i]["Net_PnL"] = 0.0
        continue
    
    # Calculate Z-Score for position decision
    window_spreads = [spread_records[j]["Spread"] for j in range(i - window_size, i)]
    mean = sum(window_spreads) / window_size
    variance = sum((x - mean) ** 2 for x in window_spreads) / window_size
    std = math.sqrt(variance) if variance > 0 else 0.0001
    z_score = (spread_records[i]["Spread"] - mean) / std
    
    # Target Position Mapping
    if z_score > 1.5:
        new_position = -1  # Short Spread
    elif z_score < -1.5:
        new_position = 1   # Long Spread
    elif abs(z_score) < 0.2:
        new_position = 0   # Exit
    else:
        new_position = current_position
        
    spread_change = spread_records[i]["Spread"] - spread_records[i-1]["Spread"]
    gross_pnl = current_position * spread_change
    
    trade_cost = 0.0
    if new_position != current_position:
        trade_cost = spread_records[i]["GOLDM"] * TRANSACTION_COST_BPS
        num_trades += 1
        
    net_pnl = gross_pnl - trade_cost
    
    total_gross_pnl += gross_pnl
    total_costs += trade_cost
    total_net_pnl += net_pnl
    
    spread_records[i]["Position"] = new_position
    spread_records[i]["Gross_PnL"] = round(gross_pnl, 2)
    spread_records[i]["Cost"] = round(trade_cost, 2)
    spread_records[i]["Net_PnL"] = round(net_pnl, 2)
    
    current_position = new_position
    
    if i >= len(spread_records) - 8:
        print(f"{spread_records[i]['Date']:<12} | {new_position:<4} | {spread_change:<14.2f} | {gross_pnl:<10.2f} | {trade_cost:<6.2f} | {net_pnl:<10.2f}")

# Underlying Gold Market Direction (Beta Return)
start_gold_m = spread_records[0]["GOLDM"]
end_gold_m = spread_records[-1]["GOLDM"]
beta_return_pct = ((end_gold_m - start_gold_m) / start_gold_m) * 100

# Save Output 4: Complete Master Backtest CSV
output4_path = os.path.join(download_folder, "Final_Backtest_Performance.csv")
with open(output4_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "GOLDM", "GOLDTEN", "Spread", "Mean", "Std", "Z_Score", "Signal", "Position", "Gross_PnL", "Cost", "Net_PnL"])
    for r in spread_records:
        writer.writerow([
            r["Date"], r["GOLDM"], r["GOLDTEN"], r["Spread"],
            r["Mean"], r["Std"], r["Z_Score"], r["Signal"],
            r.get("Position", 0), r.get("Gross_PnL", 0.0), r.get("Cost", 0.0), r.get("Net_PnL", 0.0)
        ])

# ==============================================================================
# COMPREHENSIVE CHALLENGE SUBMISSION SUMMARY
# ==============================================================================
print("\n" + "="*75)
print("             MASTER EXECUTIVE PERFORMANCE SUMMARY")
print("="*75)
print(f" 1. Total Settlement Files Processed : {len(all_files)}")
print(f" 2. Valid Dual-Contract Spread Days  : {len(spread_records)} trading days")
print(f" 3. Total Rebalance Executions      : {num_trades} trades")
print(f" 4. Gross Strategy Alpha PnL        : ₹{total_gross_pnl:.2f} / gram")
print(f" 5. Total Transaction Friction Drag  : -₹{total_costs:.2f} / gram (5 bps per trade)")
print(f" 6. NET STRATEGY ALPHA (After Costs) : ₹{total_net_pnl:.2f} / gram")
print(f" 7. UNDERLYING GOLD RETURN (Beta)   : {beta_return_pct:+.2f}% buy & hold change")
print("="*75)
print(" All 4 CSV output reports have been updated in your Downloads folder.")
print("="*75)
