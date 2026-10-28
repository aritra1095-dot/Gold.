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

date_records = {}

# 1. Parse and Normalize
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
                    unit = UNITS[symbol]
                    purity = PURITY[symbol]
                    norm_price = round((close_price / unit) * (1000.0 / purity), 2)
                    
                    if date not in date_records:
                        date_records[date] = {}
                    date_records[date][symbol] = norm_price
    except Exception as e:
        pass

# Sort dates chronologically
sorted_dates = sorted(date_records.keys())

# 2. Compute Spread (GOLDTEN vs GOLDM)
spread_data = []
for date in sorted_dates:
    prices = date_records[date]
    goldm = prices.get("GOLDM")
    goldten = prices.get("GOLDTEN")
    
    if goldm is not None and goldten is not None:
        spread = round(goldten - goldm, 2)
        spread_data.append({"Date": date, "GOLDM": goldm, "GOLDTEN": goldten, "Spread": spread})

# 3. Calculate Rolling Z-Score and Signals
window_size = 5  # Small window for sample dataset
for i in range(len(spread_data)):
    if i < window_size - 1:
        spread_data[i]["Mean"] = "N/A"
        spread_data[i]["Std"] = "N/A"
        spread_data[i]["Z_Score"] = "N/A"
        spread_data[i]["Signal"] = "HOLD"
    else:
        window_spreads = [spread_data[j]["Spread"] for j in range(i - window_size + 1, i + 1)]
        mean = sum(window_spreads) / window_size
        variance = sum((x - mean) ** 2 for x in window_spreads) / window_size
        std = math.sqrt(variance) if variance > 0 else 0.0001
        
        z_score = round((spread_data[i]["Spread"] - mean) / std, 2)
        
        # Signal Rules
        if z_score > 1.5:
            signal = "SELL GOLDTEN / BUY GOLDM"
        elif z_score < -1.5:
            signal = "BUY GOLDTEN / SELL GOLDM"
        else:
            signal = "NEUTRAL / HOLD"
            
        spread_data[i]["Mean"] = round(mean, 2)
        spread_data[i]["Std"] = round(std, 2)
        spread_data[i]["Z_Score"] = z_score
        spread_data[i]["Signal"] = signal

# 4. Display Results
print("\n" + f"{'Date':<12} | {'Spread (₹)':<10} | {'Z-Score':<8} | {'Signal':<25}")
print("-" * 65)

for row in spread_data[-15:]:  # Display last 15 days
    print(f"{row['Date']:<12} | {str(row['Spread']):<10} | {str(row['Z_Score']):<8} | {row['Signal']:<25}")

# 5. Save Signal Results
output_path = os.path.join(download_folder, "Gold_Spread_Trading_Signals.csv")
with open(output_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "GOLDM", "GOLDTEN", "Spread", "Mean", "Std", "Z_Score", "Signal"])
    for row in spread_data:
        writer.writerow([row["Date"], row["GOLDM"], row["GOLDTEN"], row["Spread"], row["Mean"], row["Std"], row["Z_Score"], row["Signal"]])

print(f"\nSaved signals to '{output_path}'")
