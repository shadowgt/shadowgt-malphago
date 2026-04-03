"""ML 모델 학습 CLI

사용법:
    python -m app.ml.train_cli --action dataset    # 데이터셋 생성
    python -m app.ml.train_cli --action train       # 모델 학습
    python -m app.ml.train_cli --action evaluate    # 교차검증
    python -m app.ml.train_cli --action compare     # 모델 비교
    python -m app.ml.train_cli --action all         # 전체 파이프라인
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "ml_data"


async def run_dataset():
    """DB에서 학습 데이터셋을 추출하여 CSV로 저장한다."""
    from app.db.session import async_session
    from app.ml.feature_extractor import build_dataset

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with async_session() as session:
        df = await build_dataset(session)

    output_path = DATA_DIR / "dataset.csv"
    df.to_csv(output_path, index=False)
    logger.info(f"Dataset saved: {output_path} ({len(df)} rows)")

    # Print summary
    print(f"\n=== Dataset Summary ===")
    print(f"Total samples: {len(df)}")
    print(f"Unique races: {df['race_id'].nunique()}")
    print(f"Unique dates: {df['race_date'].nunique()}")
    print(f"Target distribution (is_top3):")
    print(df["is_top3"].value_counts().to_string())
    print(f"\nFeature stats:")
    feature_cols = [c for c in df.columns if c not in [
        "race_id", "entry_id", "race_date", "track_id", "ranking", "is_top3", "is_win"
    ]]
    print(df[feature_cols].describe().to_string())

    return df


def run_train(model_name: str = "lightgbm"):
    """저장된 데이터셋으로 모델을 학습한다."""
    from app.ml.trainer import train_final_model
    from app.ml.feature_extractor import FEATURE_COLUMNS

    dataset_path = DATA_DIR / "dataset.csv"
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}. Run --action dataset first.")
        sys.exit(1)

    df = pd.read_csv(dataset_path)
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]

    model, path, importance = train_final_model(df, feature_cols, model_name=model_name)

    print(f"\n=== Model Trained: {model_name} ===")
    print(f"Saved to: {path}")
    print(f"Samples: {len(df)}")
    print(f"\nFeature Importance (top 10):")
    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for name, imp in sorted_imp[:10]:
        print(f"  {name:30s} {imp:.4f}")

    return model


def run_evaluate(model_name: str = "lightgbm"):
    """시계열 교차검증으로 모델을 평가한다."""
    from app.ml.trainer import time_series_cv
    from app.ml.feature_extractor import FEATURE_COLUMNS

    dataset_path = DATA_DIR / "dataset.csv"
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}. Run --action dataset first.")
        sys.exit(1)

    df = pd.read_csv(dataset_path)
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]

    result = time_series_cv(df, feature_cols, model_name=model_name)

    print(f"\n=== Time-Series CV: {model_name} ===")
    print(f"Folds: {result['n_folds']}")
    for metric, vals in result["metrics"].items():
        print(f"  {metric:12s}: {vals['mean']:.4f} ± {vals['std']:.4f}")

    # Save result
    result_path = DATA_DIR / f"cv_{model_name}.json"
    # Convert per_date results for JSON serialization
    serializable = {k: v for k, v in result.items() if k != "per_date"}
    serializable["per_date_count"] = len(result.get("per_date", []))
    with open(result_path, "w") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    logger.info(f"CV results saved: {result_path}")

    return result


def run_compare():
    """LightGBM과 XGBoost를 비교한다."""
    from app.ml.trainer import compare_models
    from app.ml.feature_extractor import FEATURE_COLUMNS

    dataset_path = DATA_DIR / "dataset.csv"
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}. Run --action dataset first.")
        sys.exit(1)

    df = pd.read_csv(dataset_path)
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]

    results = compare_models(df, feature_cols)

    print(f"\n=== Model Comparison ===")
    for name in ["lightgbm", "xgboost"]:
        r = results[name]
        m = r["metrics"]
        print(f"\n{name}:")
        print(f"  Accuracy: {m['accuracy']['mean']:.4f} ± {m['accuracy']['std']:.4f}")
        print(f"  F1:       {m['f1']['mean']:.4f} ± {m['f1']['std']:.4f}")
        print(f"  AUC:      {m['auc']['mean']:.4f} ± {m['auc']['std']:.4f}")

    print(f"\nBest model: {results['best']}")

    # Save comparison
    result_path = DATA_DIR / "model_comparison.json"
    serializable = {}
    for name in ["lightgbm", "xgboost"]:
        r = results[name]
        serializable[name] = {k: v for k, v in r.items() if k != "per_date"}
    serializable["best"] = results["best"]
    with open(result_path, "w") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)

    return results


async def run_all(model_name: str = "lightgbm"):
    """전체 파이프라인: 데이터셋 → 교차검증 → 학습"""
    print("=" * 60)
    print("Step 1: Building dataset...")
    print("=" * 60)
    await run_dataset()

    print("\n" + "=" * 60)
    print("Step 2: Model comparison (LightGBM vs XGBoost)")
    print("=" * 60)
    comparison = run_compare()

    best = comparison["best"]
    print(f"\n" + "=" * 60)
    print(f"Step 3: Training final model ({best})")
    print("=" * 60)
    run_train(model_name=best)

    print(f"\n{'=' * 60}")
    print(f"Pipeline complete! Best model: {best}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="MalPhaGo ML Training CLI")
    parser.add_argument(
        "--action",
        choices=["dataset", "train", "evaluate", "compare", "all"],
        default="all",
        help="Action to perform",
    )
    parser.add_argument(
        "--model",
        choices=["lightgbm", "xgboost"],
        default="lightgbm",
        help="Model to use",
    )
    args = parser.parse_args()

    if args.action == "dataset":
        asyncio.run(run_dataset())
    elif args.action == "train":
        run_train(args.model)
    elif args.action == "evaluate":
        run_evaluate(args.model)
    elif args.action == "compare":
        run_compare()
    elif args.action == "all":
        asyncio.run(run_all(args.model))


if __name__ == "__main__":
    main()
