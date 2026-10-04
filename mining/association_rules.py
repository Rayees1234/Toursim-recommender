"""
Data Mining Module: Association Rule Mining (Apriori / FP-Growth)
Extracts frequent itemsets across destination trip types, accommodation options,
activities, and seasons from warehouse bridge tables.
Generates human-readable rule narratives and persists high-lift rules.
"""

import os
import sys
import logging
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_association_rules(min_support=0.08, min_confidence=0.5, min_lift=1.1, algorithm="fpgrowth"):
    logger.info(f"Extracting transaction baskets from warehouse bridge tables (min_support={min_support})...")

    # 1. Fetch trip types per destination
    q_trips = """
        SELECT b.destination_key, CONCAT('Type: ', t.trip_type_name) AS item
        FROM bridge_destination_trip_type b
        JOIN dim_trip_type t ON b.trip_type_key = t.trip_type_key
    """ if db.engine_type == "mysql" else """
        SELECT b.destination_key, ('Type: ' || t.trip_type_name) AS item
        FROM bridge_destination_trip_type b
        JOIN dim_trip_type t ON b.trip_type_key = t.trip_type_key
    """

    # 2. Fetch accommodations per destination
    q_accom = """
        SELECT b.destination_key, CONCAT('Stay: ', a.accommodation_name) AS item
        FROM bridge_destination_accommodation b
        JOIN dim_accommodation a ON b.accommodation_key = a.accommodation_key
    """ if db.engine_type == "mysql" else """
        SELECT b.destination_key, ('Stay: ' || a.accommodation_name) AS item
        FROM bridge_destination_accommodation b
        JOIN dim_accommodation a ON b.accommodation_key = a.accommodation_key
    """

    # 3. Fetch seasons per destination
    q_seasons = """
        SELECT b.destination_key, CONCAT('Season: ', s.season_name) AS item
        FROM bridge_destination_season b
        JOIN dim_season s ON b.season_key = s.season_key
        WHERE b.season_type = 'best'
    """ if db.engine_type == "mysql" else """
        SELECT b.destination_key, ('Season: ' || s.season_name) AS item
        FROM bridge_destination_season b
        JOIN dim_season s ON b.season_key = s.season_key
        WHERE b.season_type = 'best'
    """

    # 4. Fetch top activities per destination
    q_acts = """
        SELECT b.destination_key, CONCAT('Activity: ', a.activity_name) AS item
        FROM bridge_destination_activity b
        JOIN dim_activity a ON b.activity_key = a.activity_key
    """ if db.engine_type == "mysql" else """
        SELECT b.destination_key, ('Activity: ' || a.activity_name) AS item
        FROM bridge_destination_activity b
        JOIN dim_activity a ON b.activity_key = a.activity_key
    """

    trips = db.fetch_all(q_trips)
    accoms = db.fetch_all(q_accom)
    seasons = db.fetch_all(q_seasons)
    acts = db.fetch_all(q_acts)

    # Combine items per destination
    baskets = {}
    for r in trips + accoms + seasons + acts:
        dk = r["destination_key"]
        item = r["item"]
        if dk not in baskets:
            baskets[dk] = set()
        baskets[dk].add(item)

    transactions = [list(items) for items in baskets.values()]
    logger.info(f"Formed {len(transactions)} transaction baskets across {sum(len(b) for b in transactions)} total items.")

    if not transactions or len(transactions) < 5:
        return {"rules": [], "message": "Not enough transaction data in warehouse."}

    # One-hot encode transactions
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df_trans = pd.DataFrame(te_ary, columns=te.columns_)

    # Mine frequent itemsets
    mining_func = fpgrowth if algorithm.lower() == "fpgrowth" else apriori
    try:
        frequent_itemsets = mining_func(df_trans, min_support=min_support, use_colnames=True)
    except Exception as e:
        logger.warning(f"FP-growth failed with {e}, falling back to apriori")
        frequent_itemsets = apriori(df_trans, min_support=min_support, use_colnames=True)

    if frequent_itemsets.empty:
        return {"rules": [], "message": f"No frequent itemsets found at min_support={min_support}."}

    # Generate association rules
    rules_df = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    # Filter trivial rules (lift <= 1.0) and apply confidence threshold
    rules_df = rules_df[(rules_df["lift"] > 1.0) & (rules_df["confidence"] >= min_confidence)]
    rules_df = rules_df.sort_values(by=["lift", "confidence"], ascending=[False, False])

    # Convert to structured output with natural English explanations
    formatted_rules = []
    rule_rows_to_persist = []
    
    for idx, (_, row) in enumerate(rules_df.iterrows(), start=1):
        ant = sorted(list(row["antecedents"]))
        con = sorted(list(row["consequents"]))
        sup = float(row["support"])
        conf = float(row["confidence"])
        lift = float(row["lift"])

        ant_str = ", ".join(ant)
        con_str = ", ".join(con)

        narrative = (
            f"Tourists and destinations featuring [{ant_str}] also select [{con_str}] "
            f"in {conf * 100:.1f}% of cases, which is {lift:.2f}× more frequent than average."
        )

        formatted_rules.append({
            "rule_id": idx,
            "antecedents": ant,
            "consequents": con,
            "support": round(sup, 4),
            "confidence": round(conf, 4),
            "lift": round(lift, 4),
            "plain_english_rule": narrative
        })

        rule_rows_to_persist.append((
            idx,
            ant_str[:255],
            con_str[:255],
            round(sup, 4),
            round(conf, 4),
            round(lift, 4),
            narrative
        ))

    # Persist up to top 50 rules
    db.execute("DELETE FROM mining_rules;")
    if rule_rows_to_persist:
        db.executemany(
            """
            INSERT INTO mining_rules (
                rule_id, antecedents, consequents, support, confidence, lift, plain_english_rule
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            rule_rows_to_persist[:50]
        )
    logger.info(f"Discovered {len(formatted_rules)} association rules. Persisted top {min(len(formatted_rules), 50)}.")

    return {
        "total_rules": len(formatted_rules),
        "min_support": min_support,
        "min_confidence": min_confidence,
        "min_lift": min_lift,
        "rules": formatted_rules[:50]
    }


if __name__ == "__main__":
    res = run_association_rules(min_support=0.08, min_confidence=0.5, min_lift=1.2)
    print(f"Discovered {res['total_rules']} association rules.")
    for r in res["rules"][:5]:
        print(f"Rule #{r['rule_id']} (Lift: {r['lift']}): {r['plain_english_rule']}")
