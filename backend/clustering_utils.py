import pandas as pd

def cluster_by_threshold(pairs_df: pd.DataFrame, threshold: float) -> list[list[str]]:
    """Groups documents into clusters based on a similarity score threshold."""
    if pairs_df.empty:
        return []

    docs = pd.unique(pairs_df[["doc_1", "doc_2"]].values.ravel("K")).tolist()
    adj = {d: set() for d in docs}

    for _, row in pairs_df.iterrows():
        if row["final_score"] >= threshold:
            adj[row["doc_1"]].add(row["doc_2"])
            adj[row["doc_2"]].add(row["doc_1"])

    visited, clusters = set(), []
    for d in docs:
        if d in visited:
            continue

        stack, component = [d], []
        visited.add(d)

        while stack:
            u = stack.pop()
            component.append(u)
            for v in adj[u]:
                if v not in visited:
                    visited.add(v)
                    stack.append(v)

        if len(component) > 1:          # เอาเฉพาะกลุ่มที่มีมากกว่า 1 เอกสาร
            clusters.append(sorted(component))

    return clusters
