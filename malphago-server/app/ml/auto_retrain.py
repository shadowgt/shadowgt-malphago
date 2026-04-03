"""모델 자동 재학습 파이프라인

경주 결과 수집 후 자동으로:
1. 학습 데이터셋 갱신
2. 시계열 교차검증 실행
3. 모델 학습
4. 성능 비교 후 우수 모델 자동 배포

APScheduler에서 주기적으로 호출하거나, 경주 결과 수집 직후 트리거한다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_extractor import build_dataset, FEATURE_COLUMNS
from app.ml.trainer import (
    time_series_cv,
    train_final_model,
    load_model,
    compare_models,
    MODEL_DIR,
)

logger = logging.getLogger(__name__)

REPORT_DIR = Path(__file__).parent.parent.parent / "ml_reports"
DATA_DIR = Path(__file__).parent.parent.parent / "ml_data"


async def retrain_pipeline(
    session: AsyncSession,
    min_improvement: float = 0.005,
) -> dict:
    """전체 재학습 파이프라인을 실행한다.

    Args:
        session: DB session
        min_improvement: 배포 기준 최소 AUC 향상폭

    Returns:
        파이프라인 실행 결과
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        "timestamp": timestamp,
        "status": "started",
        "steps": {},
    }

    # Step 1: 데이터셋 구축
    logger.info("Retrain Step 1: Building dataset...")
    try:
        df = await build_dataset(session)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(DATA_DIR / "dataset.csv", index=False)
        result["steps"]["dataset"] = {
            "samples": len(df),
            "races": int(df["race_id"].nunique()),
            "dates": int(df["race_date"].nunique()),
        }
    except Exception as e:
        logger.error(f"Dataset build failed: {e}")
        result["status"] = "failed"
        result["error"] = f"Dataset build: {e}"
        _save_report(result, timestamp)
        return result

    if len(df) < 100:
        logger.warning(f"Insufficient data for training: {len(df)} samples")
        result["status"] = "skipped"
        result["reason"] = "insufficient_data"
        _save_report(result, timestamp)
        return result

    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]

    # Step 2: 모델 비교 (시계열 교차검증)
    logger.info("Retrain Step 2: Cross-validation comparison...")
    try:
        comparison = compare_models(df, feature_cols)
        best_name = comparison["best"]
        best_auc = comparison[best_name]["metrics"]["auc"]["mean"]
        result["steps"]["comparison"] = {
            "best_model": best_name,
            "lightgbm_auc": comparison["lightgbm"]["metrics"]["auc"]["mean"],
            "xgboost_auc": comparison["xgboost"]["metrics"]["auc"]["mean"],
        }
    except Exception as e:
        logger.error(f"Cross-validation failed: {e}")
        result["status"] = "failed"
        result["error"] = f"CV failed: {e}"
        _save_report(result, timestamp)
        return result

    # Step 3: 기존 모델과 성능 비교
    should_deploy = True
    current_model, current_meta = load_model(best_name)
    if current_model is not None and current_meta:
        # 기존 모델의 AUC와 비교
        old_auc = current_meta.get("cv_auc", 0)
        improvement = best_auc - old_auc
        result["steps"]["improvement"] = {
            "old_auc": old_auc,
            "new_auc": best_auc,
            "improvement": improvement,
        }
        if improvement < min_improvement:
            should_deploy = False
            logger.info(
                f"New model AUC {best_auc:.4f} vs old {old_auc:.4f}, "
                f"improvement {improvement:.4f} < threshold {min_improvement}"
            )

    # Step 4: 학습 + 배포
    if should_deploy:
        logger.info(f"Retrain Step 4: Training and deploying {best_name}...")
        try:
            model, path, importance = train_final_model(
                df, feature_cols, model_name=best_name
            )
            # Save CV AUC in metadata for future comparison
            import joblib
            meta_path = Path(path).with_name(
                Path(path).stem + "_meta.joblib"
            )
            if meta_path.exists():
                meta = joblib.load(meta_path)
                meta["cv_auc"] = best_auc
                joblib.dump(meta, meta_path)
                # Also update latest_meta
                latest_meta = MODEL_DIR / f"{best_name}_latest_meta.joblib"
                if latest_meta.exists():
                    import shutil
                    shutil.copy2(meta_path, latest_meta)

            # Reload cached model
            from app.ml.predictor import reload_model
            reload_model(best_name)

            result["steps"]["deploy"] = {
                "model": best_name,
                "path": str(path),
                "feature_importance_top5": dict(
                    sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
                ),
            }
            result["status"] = "deployed"
            logger.info(f"Model deployed: {best_name} (AUC={best_auc:.4f})")
        except Exception as e:
            logger.error(f"Training failed: {e}")
            result["status"] = "failed"
            result["error"] = f"Training: {e}"
    else:
        result["status"] = "skipped"
        result["reason"] = "no_significant_improvement"

    _save_report(result, timestamp)
    return result


def _save_report(result: dict, timestamp: str):
    """파이프라인 실행 보고서를 저장한다."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"retrain_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Report saved: {report_path}")
