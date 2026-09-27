"""Apply the approved portfolio roster through the existing audited routing store."""

import argparse
import json

from backend import config  # noqa: F401 - load the app's environment before routing.
from backend import model_routing


PRIMARY_MODEL = "openai/gpt-6-sol"
EVIDENCE_MODEL = "openai/gpt-6-luna-pro"
FINANCIAL_REVIEW_MODEL = PRIMARY_MODEL
REVIEW_MODEL = "anthropic/claude-opus-5.5"
RETRIEVAL_PROFILE = {
    "portfolio.macro-news": "ultra2x",
    "portfolio.source-retrieval": "ultra2x",
}
PORTFOLIO_MODEL_PROFILE = {
    **RETRIEVAL_PROFILE,
    "portfolio.deep-summary": EVIDENCE_MODEL,
    "portfolio.allocator-macro-prior": {"model": PRIMARY_MODEL},
    "portfolio.allocator-portfolio-aware": {"model": PRIMARY_MODEL},
    "portfolio.allocator-exposure-equivalence": {"model": FINANCIAL_REVIEW_MODEL},
    "portfolio.allocator-defensive-review": {"model": FINANCIAL_REVIEW_MODEL},
    "portfolio.deep-chairman": REVIEW_MODEL,
    "portfolio.deep-commentary": REVIEW_MODEL,
    "portfolio.synthesis": REVIEW_MODEL,
}


def configure(*, apply=False, retrieval_only=False):
    profile = RETRIEVAL_PROFILE if retrieval_only else PORTFOLIO_MODEL_PROFILE
    routes = {row["id"]: row for row in model_routing.list_model_routes()["routes"]}
    changes = [{"route_id": key, "before": routes[key]["effective_value"], "after": value}
               for key, value in profile.items()
               if routes[key]["effective_value"] != value or routes[key]["source"] != "runtime_override"]
    if apply:
        for change in changes:
            model_routing.update_model_route(change["route_id"], change["after"],
                                             actor="operator:portfolio-parallel-ultra2x" if retrieval_only else "operator:portfolio-research-direction-profile")
        actual = {row["id"]: row["effective_value"] for row in model_routing.list_model_routes()["routes"]}
        assert all(actual[key] == value for key, value in profile.items())
    return {"applied": apply, "store": str(model_routing._STORE_PATH.resolve()), "changes": changes,
            "profile": profile}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Save changes; without this flag only show the proposed roster.")
    parser.add_argument("--retrieval-only", action="store_true", help="Apply Parallel Ultra2x for deep research without changing analysis models.")
    args = parser.parse_args()
    print(json.dumps(configure(apply=args.apply, retrieval_only=args.retrieval_only), indent=2))
