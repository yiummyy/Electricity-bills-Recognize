from decimal import Decimal, ROUND_HALF_UP

def calculate():
    # Values provided by user
    # "0.825341+0.0689+0.0274+0.0301+0+0.02766875"
    
    values = [
        "0.825341", # 电能电费(峰)
        "0.0689",   # 输配电费(峰)
        "0.0274",   # 上网环节线损电费(峰)
        "0.0301",   # 系统运行费用(总) -> Shared
        "0",        # 市场化分摊 -> Shared
        "0.02766875" # 基金及附加 -> Shared
    ]
    
    print("--- Simulating Calculation with Decimal ---")
    
    # 1. Accumulate Base (Peak/Shoulder specific)
    # Assuming the first 3 are specific to the period
    base_price = Decimal("0.0")
    base_price += Decimal(values[0])
    base_price += Decimal(values[1])
    base_price += Decimal(values[2])
    
    print(f"Base Price (Energy + Trans + Loss): {base_price}")
    
    # 2. Accumulate Shared
    shared_price = Decimal("0.0")
    shared_price += Decimal(values[3])
    shared_price += Decimal(values[4])
    shared_price += Decimal(values[5])
    
    print(f"Shared Price (System + Market + Fund): {shared_price}")
    
    # 3. Final Sum
    final_price = base_price + shared_price
    print(f"Total Sum: {final_price}")
    
    # 4. Rounding
    final_rounded = final_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    print(f"Rounded Result (ROUND_HALF_UP): {final_rounded}")

if __name__ == "__main__":
    calculate()
