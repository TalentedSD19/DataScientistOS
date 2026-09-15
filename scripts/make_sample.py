from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer


# ============================================================
# Setup
# ============================================================

OUTPUT_DIR = Path("samples")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)


# ============================================================
# 0. Original breast cancer dataset
# ============================================================

data = load_breast_cancer(as_frame=True)

df = data.frame.iloc[:, :8].copy()  # keep it small and readable
df["Outcome"] = data.target

df.to_csv(OUTPUT_DIR / "data.csv", index=False)

print("Created:", OUTPUT_DIR / "data.csv")
print("Shape:", df.shape)
print("Columns:", list(df.columns))


# ============================================================
# 1. Sales EDA Dataset
# ============================================================

n_orders = 3000

dates = pd.date_range("2023-01-01", "2025-12-31", freq="D")

regions = ["North", "South", "East", "West"]
categories = ["Furniture", "Technology", "Office Supplies"]
products = [
    "Laptop",
    "Monitor",
    "Keyboard",
    "Desk",
    "Chair",
    "Printer",
    "Phone",
    "Notebook",
    "Desk Lamp",
    "Headphones",
]
customers = [f"CUST_{i:04d}" for i in range(1, 501)]

sales_df = pd.DataFrame({
    "Order_ID": [f"ORD_{i:05d}" for i in range(1, n_orders + 1)],
    "Order_Date": rng.choice(dates, n_orders),
    "Region": rng.choice(regions, n_orders),
    "Category": rng.choice(categories, n_orders),
    "Product": rng.choice(products, n_orders),
    "Customer": rng.choice(customers, n_orders),
})

sales_df["Quantity"] = rng.integers(1, 10, n_orders)

base_price = {
    "Laptop": 1000,
    "Monitor": 300,
    "Keyboard": 80,
    "Desk": 250,
    "Chair": 180,
    "Printer": 220,
    "Phone": 700,
    "Notebook": 15,
    "Desk Lamp": 45,
    "Headphones": 120,
}

sales_df["Unit_Price"] = sales_df["Product"].map(base_price)

sales_df["Discount"] = np.round(
    rng.uniform(0.00, 0.35, n_orders), 2
)

sales_df["Sales"] = np.round(
    sales_df["Quantity"]
    * sales_df["Unit_Price"]
    * (1 - sales_df["Discount"]),
    2,
)

# Profit deliberately decreases as discount increases
sales_df["Profit"] = np.round(
    sales_df["Sales"] * (
        rng.uniform(0.10, 0.30, n_orders)
        - sales_df["Discount"] * 0.45
    ),
    2,
)

sales_df.to_csv(OUTPUT_DIR / "sales.csv", index=False)

print("\nCreated:", OUTPUT_DIR / "sales.csv")
print("Shape:", sales_df.shape)
print("Columns:", list(sales_df.columns))


# ============================================================
# 2. Customer Churn Dataset
# ============================================================

n_customers = 2500

churn_df = pd.DataFrame({
    "Customer_ID": [f"CUST_{i:05d}" for i in range(1, n_customers + 1)],
    "Age": rng.integers(18, 75, n_customers),
    "Gender": rng.choice(["Male", "Female"], n_customers),
    "Tenure_Months": rng.integers(1, 73, n_customers),
    "Monthly_Charges": np.round(rng.uniform(20, 150, n_customers), 2),
    "Contract": rng.choice(
        ["Month-to-month", "One year", "Two year"],
        n_customers,
        p=[0.55, 0.25, 0.20],
    ),
    "Internet_Service": rng.choice(
        ["DSL", "Fiber", "No"],
        n_customers,
        p=[0.35, 0.50, 0.15],
    ),
    "Tech_Support": rng.choice(["Yes", "No"], n_customers),
    "Payment_Method": rng.choice(
        ["Credit Card", "Bank Transfer", "Electronic Check"],
        n_customers,
    ),
})

# Create churn probability with meaningful relationships
logit = (
    -1.8
    + 0.015 * churn_df["Monthly_Charges"]
    - 0.025 * churn_df["Tenure_Months"]
    + (churn_df["Contract"] == "Month-to-month") * 1.3
    + (churn_df["Internet_Service"] == "Fiber") * 0.35
    + (churn_df["Tech_Support"] == "No") * 0.55
)

probability = 1 / (1 + np.exp(-logit))

churn_df["Churn"] = rng.binomial(1, probability)

# Add a small amount of missing data
for column in ["Monthly_Charges", "Tech_Support"]:
    missing_idx = rng.choice(
        churn_df.index,
        size=int(0.03 * n_customers),
        replace=False,
    )
    churn_df.loc[missing_idx, column] = np.nan

churn_df.to_csv(OUTPUT_DIR / "customer_churn.csv", index=False)

print("\nCreated:", OUTPUT_DIR / "customer_churn.csv")
print("Shape:", churn_df.shape)
print("Columns:", list(churn_df.columns))


# ============================================================
# 3. Time-Series Sales Dataset
# ============================================================

dates = pd.date_range("2021-01-01", "2025-12-31", freq="D")

time_df = pd.DataFrame({
    "Date": dates
})

t = np.arange(len(time_df))

# Trend + yearly seasonality + noise
trend = 1000 + t * 0.8
seasonality = 250 * np.sin(2 * np.pi * t / 365.25)
noise = rng.normal(0, 100, len(time_df))

time_df["Sales"] = np.round(
    np.maximum(trend + seasonality + noise, 100),
    2,
)

# Additional useful variables
time_df["Orders"] = rng.poisson(
    np.maximum(time_df["Sales"] / 120, 1)
)

time_df["Customers"] = rng.poisson(
    np.maximum(time_df["Orders"] * 0.75, 1)
)

time_df.to_csv(OUTPUT_DIR / "time_series_sales.csv", index=False)

print("\nCreated:", OUTPUT_DIR / "time_series_sales.csv")
print("Shape:", time_df.shape)
print("Columns:", list(time_df.columns))


# ============================================================
# 4. A/B Testing Dataset
# ============================================================

n_users = 5000

ab_df = pd.DataFrame({
    "User_ID": [f"USER_{i:05d}" for i in range(1, n_users + 1)],
    "Group": rng.choice(
        ["Control", "Treatment"],
        n_users,
        p=[0.50, 0.50],
    ),
})

ab_df["Device"] = rng.choice(
    ["Mobile", "Desktop", "Tablet"],
    n_users,
    p=[0.60, 0.30, 0.10],
)

ab_df["Age"] = rng.integers(18, 70, n_users)

# Treatment has a slightly higher conversion probability
base_conversion = np.where(
    ab_df["Group"] == "Treatment",
    0.16,
    0.12,
)

device_adjustment = np.where(
    ab_df["Device"] == "Mobile",
    -0.015,
    np.where(ab_df["Device"] == "Desktop", 0.015, 0),
)

conversion_probability = np.clip(
    base_conversion + device_adjustment,
    0.01,
    0.95,
)

ab_df["Conversion"] = rng.binomial(
    1,
    conversion_probability,
)

# Revenue is mostly zero when there is no conversion
ab_df["Revenue"] = np.where(
    ab_df["Conversion"] == 1,
    np.round(rng.gamma(shape=5, scale=25, size=n_users), 2),
    0.0,
)

ab_df.to_csv(OUTPUT_DIR / "ab_test.csv", index=False)

print("\nCreated:", OUTPUT_DIR / "ab_test.csv")
print("Shape:", ab_df.shape)
print("Columns:", list(ab_df.columns))


# ============================================================
# 5. Multi-file Business Analysis Dataset
# ============================================================

# ----------------------------
# Customers
# ----------------------------

n_business_customers = 1000

customers_df = pd.DataFrame({
    "Customer_ID": [
        f"CUST_{i:04d}"
        for i in range(1, n_business_customers + 1)
    ],
    "Customer_Name": [
        f"Customer_{i:04d}"
        for i in range(1, n_business_customers + 1)
    ],
    "Segment": rng.choice(
        ["Consumer", "Corporate", "Home Office"],
        n_business_customers,
        p=[0.55, 0.30, 0.15],
    ),
    "Region": rng.choice(
        regions,
        n_business_customers,
    ),
})

customers_df.to_csv(
    OUTPUT_DIR / "customers.csv",
    index=False,
)


# ----------------------------
# Products
# ----------------------------

product_names = [
    "Laptop",
    "Monitor",
    "Keyboard",
    "Desk",
    "Chair",
    "Printer",
    "Phone",
    "Notebook",
    "Desk Lamp",
    "Headphones",
]

products_df = pd.DataFrame({
    "Product_ID": [
        f"P{i:03d}"
        for i in range(1, len(product_names) + 1)
    ],
    "Product": product_names,
    "Category": [
        "Technology",
        "Technology",
        "Technology",
        "Furniture",
        "Furniture",
        "Technology",
        "Technology",
        "Office Supplies",
        "Office Supplies",
        "Technology",
    ],
    "Base_Price": [
        base_price[p]
        for p in product_names
    ],
})

products_df.to_csv(
    OUTPUT_DIR / "products.csv",
    index=False,
)


# ----------------------------
# Orders
# ----------------------------

n_business_orders = 6000

orders_df = pd.DataFrame({
    "Order_ID": [
        f"ORDER_{i:06d}"
        for i in range(1, n_business_orders + 1)
    ],
    "Customer_ID": rng.choice(
        customers_df["Customer_ID"],
        n_business_orders,
    ),
    "Product_ID": rng.choice(
        products_df["Product_ID"],
        n_business_orders,
    ),
    "Order_Date": rng.choice(
        pd.date_range(
            "2024-01-01",
            "2025-12-31",
            freq="D",
        ),
        n_business_orders,
    ),
})

orders_df["Quantity"] = rng.integers(
    1,
    8,
    n_business_orders,
)

orders_df["Discount"] = np.round(
    rng.uniform(0.00, 0.30, n_business_orders),
    2,
)

orders_df.to_csv(
    OUTPUT_DIR / "orders.csv",
    index=False,
)


# ----------------------------
# Returns
# ----------------------------

return_probability = np.clip(
    0.04
    + orders_df["Discount"] * 0.08
    + (orders_df["Quantity"] >= 5) * 0.04,
    0,
    0.50,
)

returns_mask = rng.random(n_business_orders) < return_probability

returns_df = orders_df.loc[
    returns_mask,
    ["Order_ID"]
].copy()

returns_df["Return_Date"] = pd.to_datetime(
    orders_df.loc[returns_mask, "Order_Date"]
) + pd.to_timedelta(
    rng.integers(
        1,
        30,
        len(returns_df),
    ),
    unit="D",
)

returns_df["Return_Reason"] = rng.choice(
    [
        "Damaged",
        "Wrong Item",
        "Customer Changed Mind",
        "Defective",
    ],
    len(returns_df),
)

returns_df.to_csv(
    OUTPUT_DIR / "returns.csv",
    index=False,
)


# ----------------------------
# Regions
# ----------------------------

regions_df = pd.DataFrame({
    "Region": regions,
    "Manager": [
        "Manager North",
        "Manager South",
        "Manager East",
        "Manager West",
    ],
})

regions_df.to_csv(
    OUTPUT_DIR / "regions.csv",
    index=False,
)


# ============================================================
# Summary
# ============================================================

print("\n" + "=" * 60)
print("ALL DATASETS CREATED")
print("=" * 60)

for file in sorted(OUTPUT_DIR.glob("*.csv")):
    temp = pd.read_csv(file)
    print(
        f"{file.name:25s} | "
        f"rows={len(temp):6d} | "
        f"columns={len(temp.columns):2d}"
    )