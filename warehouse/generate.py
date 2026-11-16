"""Generate the fictional sales data warehouse (SQLite, star schema).

Everything here is invented and produced from a seed: no real company data is
used. The same seed always yields the same database, byte for byte in content.

    python warehouse/generate.py                 # writes warehouse/warehouse.db
    python warehouse/generate.py --seed 7 --out /tmp/other.db

Schema
    dim_customer(customer_id, name, city, segment, signup_date)
    dim_product(product_id, name, category, unit_price)
    dim_date(date_id, date, year, quarter, month, month_name, day_of_week, is_weekend)
    fact_sales(sale_id, customer_id, product_id, date_id, quantity, discount, amount)
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import random
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE dim_customer (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    segment     TEXT NOT NULL,
    signup_date TEXT NOT NULL
);
CREATE TABLE dim_product (
    product_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    category   TEXT NOT NULL,
    unit_price REAL NOT NULL
);
CREATE TABLE dim_date (
    date_id     INTEGER PRIMARY KEY,   -- yyyymmdd
    date        TEXT NOT NULL,         -- yyyy-mm-dd
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_name  TEXT NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend  INTEGER NOT NULL
);
CREATE TABLE fact_sales (
    sale_id     INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES dim_customer(customer_id),
    product_id  INTEGER NOT NULL REFERENCES dim_product(product_id),
    date_id     INTEGER NOT NULL REFERENCES dim_date(date_id),
    quantity    INTEGER NOT NULL,
    discount    REAL NOT NULL,         -- fraction, 0.0 to 0.3
    amount      REAL NOT NULL          -- quantity * unit_price * (1 - discount)
);
CREATE INDEX idx_sales_customer ON fact_sales(customer_id);
CREATE INDEX idx_sales_product  ON fact_sales(product_id);
CREATE INDEX idx_sales_date     ON fact_sales(date_id);
"""

CITIES = [
    ("Casablanca", 5), ("Rabat", 3), ("Marrakech", 3), ("Tangier", 2.5), ("Fes", 2.5),
    ("Agadir", 2), ("Meknes", 1.5), ("Oujda", 1.2), ("Tetouan", 1.2), ("Kenitra", 1.2),
    ("El Jadida", 1), ("Safi", 0.8),
]
SEGMENTS = [("Retail", 0.6), ("SME", 0.3), ("Corporate", 0.1)]
FIRST = ["Amine", "Sara", "Youssef", "Salma", "Omar", "Lina", "Hamza", "Imane", "Karim", "Nadia",
         "Reda", "Hajar", "Anas", "Meryem", "Ayoub", "Zineb", "Adam", "Ghita", "Walid", "Rim",
         "Yassine", "Aya", "Ilyas", "Sofia", "Bilal", "Khadija", "Mehdi", "Chaima", "Tarik", "Lamia"]
LAST = ["Alaoui", "Benali", "Chraibi", "Daoudi", "El Idrissi", "Fassi", "Guerrouj", "Haddad", "Idrissi",
        "Jabri", "Kettani", "Lahlou", "Mansouri", "Naciri", "Ouazzani", "Qadiri", "Rahmani", "Saidi",
        "Tazi", "Zniber", "Berrada", "Bennis", "Cherkaoui", "Slaoui", "Amrani", "Benjelloun"]
# category -> (base price range, product name stems)
CATALOG = {
    "Electronics": ((120, 1800), ["Laptop", "Monitor", "Keyboard", "Headset", "Webcam", "Router", "Tablet", "Speaker"]),
    "Office":      ((8, 220),    ["Notebook", "Desk Lamp", "Chair Mat", "Stapler", "Whiteboard", "Organizer", "Planner"]),
    "Home":        ((15, 650),   ["Kettle", "Blender", "Vacuum", "Air Fryer", "Rug", "Curtains", "Cookware Set"]),
    "Sports":      ((10, 400),   ["Yoga Mat", "Dumbbells", "Running Shoes", "Backpack", "Water Bottle", "Bike Light"]),
    "Beauty":      ((5, 150),    ["Face Cream", "Shampoo", "Perfume", "Hair Dryer", "Lip Balm", "Sunscreen"]),
    "Grocery":     ((2, 45),     ["Olive Oil", "Coffee Beans", "Green Tea", "Honey", "Dates", "Almonds", "Couscous"]),
}
VARIANTS = ["Basic", "Plus", "Pro", "Mini", "Max", "Eco", "Classic"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def weighted(rng: random.Random, pairs):
    total = sum(w for _, w in pairs)
    x = rng.random() * total
    for item, w in pairs:
        x -= w
        if x <= 0:
            return item
    return pairs[-1][0]


def build(db_path: Path, seed: int, n_customers: int, n_products: int, n_sales: int,
          start: dt.date, end: dt.date) -> None:
    rng = random.Random(seed)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)

    # dates
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    con.executemany(
        "INSERT INTO dim_date VALUES (?,?,?,?,?,?,?,?)",
        [(int(x.strftime("%Y%m%d")), x.isoformat(), x.year, (x.month - 1) // 3 + 1, x.month,
          MONTHS[x.month - 1], DAYS[x.weekday()], int(x.weekday() >= 5)) for x in days],
    )

    # customers: signup dates spread over the first two thirds of the period
    span = (end - start).days
    customers = []
    used = set()
    for cid in range(1, n_customers + 1):
        while True:
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            if name not in used or len(used) > len(FIRST) * len(LAST) - 5:
                used.add(name)
                break
        signup = start + dt.timedelta(days=int(rng.random() ** 1.4 * span * 0.66))
        customers.append((cid, name, weighted(rng, CITIES), weighted(rng, SEGMENTS), signup.isoformat()))
    con.executemany("INSERT INTO dim_customer VALUES (?,?,?,?,?)", customers)

    # products
    products = []
    pid = 1
    cats = list(CATALOG)
    while len(products) < n_products:
        cat = cats[(pid - 1) % len(cats)]
        (lo, hi), stems = CATALOG[cat]
        stem = rng.choice(stems)
        name = f"{stem} {rng.choice(VARIANTS)}"
        if any(p[1] == name for p in products):
            pid += 1
            continue
        price = round(math.exp(rng.uniform(math.log(lo), math.log(hi))), 2)
        products.append((len(products) + 1, name, cat, price))
        pid += 1
    con.executemany("INSERT INTO dim_product VALUES (?,?,?,?)", products)
    price_of = {p[0]: p[3] for p in products}

    # customer activity follows a heavy tail: a few customers buy a lot
    activity = [rng.paretovariate(1.6) for _ in customers]
    signup_of = {c[0]: dt.date.fromisoformat(c[4]) for c in customers}
    segment_of = {c[0]: c[3] for c in customers}
    cust_ids = [c[0] for c in customers]
    cust_weights = activity
    # product popularity also heavy-tailed, cheaper items sell more often
    pop = [rng.paretovariate(2.2) / (1 + math.log1p(p[3])) for p in products]
    prod_ids = [p[0] for p in products]

    # day weights: yearly growth, mild weekly rhythm, Nov-Dec and Jun peaks
    def day_weight(x: dt.date) -> float:
        t = (x - start).days / max(span, 1)
        w = 1.0 + 0.9 * t
        w *= 1.25 if x.weekday() < 5 else 0.8
        w *= {11: 1.45, 12: 1.6, 6: 1.15, 1: 0.85, 2: 0.9}.get(x.month, 1.0)
        return w

    day_w = [day_weight(x) for x in days]
    sales = []
    sid = 1
    while len(sales) < n_sales:
        day = rng.choices(days, weights=day_w, k=1)[0]
        cid = rng.choices(cust_ids, weights=cust_weights, k=1)[0]
        if day < signup_of[cid]:
            continue  # nobody buys before signing up
        product = rng.choices(prod_ids, weights=pop, k=1)[0]
        seg = segment_of[cid]
        qty = max(1, int(rng.expovariate(1 / {"Retail": 1.6, "SME": 4.0, "Corporate": 9.0}[seg])) + 1)
        disc = 0.0
        if seg != "Retail" and rng.random() < 0.5:
            disc = rng.choice([0.05, 0.1, 0.15, 0.2, 0.3] if seg == "Corporate" else [0.05, 0.1])
        elif rng.random() < 0.08:
            disc = rng.choice([0.05, 0.1])
        amount = round(qty * price_of[product] * (1 - disc), 2)
        sales.append((sid, cid, product, int(day.strftime("%Y%m%d")), qty, disc, amount))
        sid += 1
    sales.sort(key=lambda r: (r[3], r[0]))
    sales = [(i + 1, *r[1:]) for i, r in enumerate(sales)]
    con.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?)", sales)

    con.commit()
    con.execute("VACUUM")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("warehouse.db"))
    ap.add_argument("--customers", type=int, default=1200)
    ap.add_argument("--products", type=int, default=72)
    ap.add_argument("--sales", type=int, default=30000)
    args = ap.parse_args()
    build(args.out, args.seed, args.customers, args.products, args.sales,
          dt.date(2023, 1, 1), dt.date(2025, 12, 31))
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
