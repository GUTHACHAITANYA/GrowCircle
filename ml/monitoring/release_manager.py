"""
GrowCircle Safe Model Release Manager (ML-7).

Provides:
1. Shadow Mode: Candidate runs in parallel on live requests without user exposure.
2. Canary Deployments: Progressive deterministic traffic allocation (e.g. 5% -> 10% -> 25%).
3. Automatic Rollback Engine: Instant fallback to verified baseline upon metric regression.
4. MLflow Experiment & Model Registry Tracking: Data hash, parameters, and benchmark logging.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import mlflow

logger = logging.getLogger(__name__)


class ReleaseStage(StrEnum):
    BASELINE = "BASELINE"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    PROMOTED = "PROMOTED"
    ROLLEDBACK = "ROLLEDBACK"


@dataclass
class ModelVersionMetadata:
    """Metadata tracking a specific model version."""

    model_name: str
    version: str
    data_hash: str
    stage: ReleaseStage
    created_at: str
    metrics: dict[str, float]
    git_commit: str = "HEAD"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["stage"] = self.stage.value
        return d


class ModelReleaseManager:
    """
    Manages safe multi-phase rollouts, shadow traffic evaluation,
    deterministic canary splitting, and automated rollbacks to baseline.
    """

    def __init__(
        self,
        model_name: str = "price_forecaster",
        baseline_version: str = "v1.0-baseline",
        mlflow_tracking_dir: str = "mlruns",
    ) -> None:
        self.model_name = model_name
        self.baseline_version = baseline_version
        self.candidate_version: str | None = None
        self.stage: ReleaseStage = ReleaseStage.BASELINE
        self.canary_percentage: int = 10  # 10% by default

        self.baseline_metadata = ModelVersionMetadata(
            model_name=model_name,
            version=baseline_version,
            data_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90",
            stage=ReleaseStage.BASELINE,
            created_at="2026-10-13T00:00:00Z",
            metrics={"smape_pct": 14.2, "mae": 2.45, "latency_ms": 12.0, "error_rate": 0.0},
        )
        self.candidate_metadata: ModelVersionMetadata | None = None

        self.last_rollback_reason: str | None = None
        self.traffic_log: list[dict[str, Any]] = []
        self.mlflow_tracking_dir = Path(mlflow_tracking_dir)

    def deploy_shadow(
        self,
        candidate_version: str,
        data_hash: str,
        initial_metrics: dict[str, float],
    ) -> dict[str, Any]:
        """
        Deploys candidate in shadow mode. Candidate runs in parallel on live traffic
        to record inferences and performance, but outputs are not served to users.
        """
        self.candidate_version = candidate_version
        self.stage = ReleaseStage.SHADOW
        self.last_rollback_reason = None

        self.candidate_metadata = ModelVersionMetadata(
            model_name=self.model_name,
            version=candidate_version,
            data_hash=data_hash,
            stage=ReleaseStage.SHADOW,
            created_at="2026-10-13T12:00:00Z",
            metrics=initial_metrics,
        )

        self._record_mlflow_run(
            run_name=f"{self.model_name}_shadow_{candidate_version}",
            stage=ReleaseStage.SHADOW,
        )

        logger.info(
            "Candidate model %s deployed in SHADOW mode for %s",
            candidate_version,
            self.model_name,
        )
        return {
            "status": "success",
            "stage": self.stage.value,
            "candidate_version": candidate_version,
            "message": "Candidate running in shadow mode alongside baseline. Zero user exposure.",
        }

    def deploy_canary(
        self,
        candidate_version: str,
        canary_pct: int = 10,
        data_hash: str | None = None,
        initial_metrics: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Deploys candidate to a small percentage of user traffic (e.g. 5%, 10%, 25%).
        """
        if canary_pct <= 0 or canary_pct > 50:
            raise ValueError("Canary percentage must be between 1% and 50%")

        self.candidate_version = candidate_version
        self.canary_percentage = canary_pct
        self.stage = ReleaseStage.CANARY
        self.last_rollback_reason = None

        if not self.candidate_metadata or self.candidate_metadata.version != candidate_version:
            self.candidate_metadata = ModelVersionMetadata(
                model_name=self.model_name,
                version=candidate_version,
                data_hash=data_hash or "e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
                stage=ReleaseStage.CANARY,
                created_at="2026-10-13T12:00:00Z",
                metrics=initial_metrics or {"smape_pct": 13.8, "mae": 2.30, "latency_ms": 14.0, "error_rate": 0.0},
            )
        else:
            self.candidate_metadata.stage = ReleaseStage.CANARY

        self._record_mlflow_run(
            run_name=f"{self.model_name}_canary_{candidate_version}_{canary_pct}pct",
            stage=ReleaseStage.CANARY,
        )

        logger.info(
            "Candidate model %s deployed in CANARY (%d%% traffic) for %s",
            candidate_version,
            canary_pct,
            self.model_name,
        )
        return {
            "status": "success",
            "stage": self.stage.value,
            "candidate_version": candidate_version,
            "canary_percentage": canary_pct,
            "message": f"Canary active. {canary_pct}% of traffic routed to {candidate_version}.",
        }

    def promote_candidate(self) -> dict[str, Any]:
        """
        Promotes verified candidate to active baseline after passing canary evaluation.
        """
        if self.stage != ReleaseStage.CANARY or not self.candidate_version:
            raise ValueError("Only an active canary model can be promoted to baseline.")

        promoted_version = self.candidate_version
        self.baseline_version = promoted_version
        self.stage = ReleaseStage.PROMOTED

        if self.candidate_metadata:
            self.candidate_metadata.stage = ReleaseStage.PROMOTED
            self.baseline_metadata = self.candidate_metadata

        self._record_mlflow_run(
            run_name=f"{self.model_name}_promoted_{promoted_version}",
            stage=ReleaseStage.PROMOTED,
        )

        logger.info(
            "Candidate model %s successfully PROMOTED to baseline for %s",
            promoted_version,
            self.model_name,
        )
        return {
            "status": "promoted",
            "active_baseline": promoted_version,
            "stage": self.stage.value,
            "message": f"Candidate {promoted_version} promoted to 100% production baseline.",
        }

    def trigger_rollback(self, reason: str) -> dict[str, Any]:
        """
        Executes immediate automated rollback to verified baseline.
        """
        failed_candidate = self.candidate_version
        self.stage = ReleaseStage.ROLLEDBACK
        self.last_rollback_reason = reason

        if self.candidate_metadata:
            self.candidate_metadata.stage = ReleaseStage.ROLLEDBACK

        self._record_mlflow_run(
            run_name=f"{self.model_name}_rollback_from_{failed_candidate}",
            stage=ReleaseStage.ROLLEDBACK,
            notes=reason,
        )

        logger.warning(
            "AUTOMATIC ROLLBACK TRIGGERED for %s (Candidate: %s -> Restored: %s). Reason: %s",
            self.model_name,
            failed_candidate,
            self.baseline_version,
            reason,
        )

        return {
            "status": "rolled_back",
            "stage": self.stage.value,
            "active_version": self.baseline_version,
            "rolled_back_candidate": failed_candidate,
            "reason": reason,
        }

    def evaluate_canary_guardrails(
        self,
        canary_metrics: dict[str, float],
        max_smape_degradation_pct: float = 15.0,  # e.g., candidate cannot be >15% worse
        max_latency_ms: float = 250.0,
        max_error_rate: float = 0.01,  # 1% error rate
    ) -> bool:
        """
        Monitors canary guardrails in real time.
        If canary breaches error limits, instantly executes automatic rollback.
        Returns True if healthy; False if rollback occurred.
        """
        if self.stage != ReleaseStage.CANARY:
            return True

        base_smape = self.baseline_metadata.metrics.get("smape_pct", 15.0)
        curr_smape = canary_metrics.get("smape_pct", base_smape)
        curr_latency = canary_metrics.get("latency_ms", 10.0)
        curr_err_rate = canary_metrics.get("error_rate", 0.0)

        # 1. Error regression check
        if curr_smape > base_smape * (1.0 + max_smape_degradation_pct / 100.0):
            reason = (
                f"Canary sMAPE ({curr_smape:.1f}%) exceeded baseline "
                f"({base_smape:.1f}%) by more than {max_smape_degradation_pct}%."
            )
            self.trigger_rollback(reason)
            return False

        # 2. Latency check
        if curr_latency > max_latency_ms:
            reason = f"Canary inference latency ({curr_latency:.1f}ms) breached SLA limit ({max_latency_ms}ms)."
            self.trigger_rollback(reason)
            return False

        # 3. Crash / Error rate check
        if curr_err_rate > max_error_rate:
            reason = f"Canary failure rate ({curr_err_rate*100:.1f}%) exceeded maximum allowable 1.0%."
            self.trigger_rollback(reason)
            return False

        return True

    def route_request(
        self,
        user_id: int | str,
        baseline_fn: Callable[..., Any],
        candidate_fn: Callable[..., Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Executes request through appropriate model version based on active release stage:
        - BASELINE / ROLLEDBACK: runs baseline model only.
        - SHADOW: runs baseline for user; runs candidate in background.
        - CANARY: deterministic hash of user_id directs canary_percentage to candidate.
        """
        # Baseline execution
        if self.stage in (ReleaseStage.BASELINE, ReleaseStage.ROLLEDBACK, ReleaseStage.PROMOTED) or not candidate_fn:
            res = baseline_fn(*args, **kwargs)
            return {
                "result": res,
                "served_by": self.baseline_version,
                "stage": self.stage.value,
                "is_shadow": False,
            }

        # Shadow execution
        if self.stage == ReleaseStage.SHADOW:
            base_res = baseline_fn(*args, **kwargs)
            shadow_res = None
            try:
                shadow_res = candidate_fn(*args, **kwargs)
            except Exception as e:
                logger.error("Shadow model execution exception: %s", e)

            return {
                "result": base_res,
                "served_by": self.baseline_version,
                "shadow_result": shadow_res,
                "shadow_model": self.candidate_version,
                "stage": self.stage.value,
                "is_shadow": True,
            }

        # Canary execution: deterministic hash allocation
        user_hash = int(hashlib.md5(f"{user_id}_{self.model_name}".encode()).hexdigest(), 16) % 100
        is_canary_user = user_hash < self.canary_percentage

        if is_canary_user:
            try:
                canary_res = candidate_fn(*args, **kwargs)
                return {
                    "result": canary_res,
                    "served_by": self.candidate_version,
                    "stage": self.stage.value,
                    "is_canary": True,
                }
            except Exception as e:
                logger.warning("Canary execution failed (%s), rolling back immediately", e)
                self.trigger_rollback(f"Runtime exception in canary execution: {e}")
                # Fallback to baseline
                base_res = baseline_fn(*args, **kwargs)
                return {
                    "result": base_res,
                    "served_by": self.baseline_version,
                    "stage": self.stage.value,
                    "is_canary": False,
                }
        else:
            base_res = baseline_fn(*args, **kwargs)
            return {
                "result": base_res,
                "served_by": self.baseline_version,
                "stage": self.stage.value,
                "is_canary": False,
            }

    def _record_mlflow_run(
        self,
        run_name: str,
        stage: ReleaseStage,
        notes: str | None = None,
    ) -> None:
        """Records release transition and model version metadata in local MLflow."""
        try:
            self.mlflow_tracking_dir.mkdir(parents=True, exist_ok=True)
            db_path = self.mlflow_tracking_dir / "mlflow.db"
            mlflow.set_tracking_uri(f"sqlite:///{db_path.resolve()}")
            mlflow.set_experiment("growcircle_safe_releases")

            with mlflow.start_run(run_name=run_name):
                mlflow.log_params({
                    "model_name": self.model_name,
                    "baseline_version": self.baseline_version,
                    "candidate_version": self.candidate_version or "none",
                    "stage": stage.value,
                    "canary_percentage": self.canary_percentage,
                })
                if self.candidate_metadata:
                    mlflow.log_params({"data_hash": self.candidate_metadata.data_hash})
                    mlflow.log_metrics(self.candidate_metadata.metrics)
                if notes:
                    mlflow.set_tag("notes", notes)
        except Exception as e:
            logger.debug("Local MLflow logging skipped in test/mock environment: %s", e)

    def get_status(self) -> dict[str, Any]:
        """Returns current model deployment status."""
        return {
            "model_name": self.model_name,
            "stage": self.stage.value,
            "active_baseline_version": self.baseline_version,
            "candidate_version": self.candidate_version,
            "canary_percentage": self.canary_percentage if self.stage == ReleaseStage.CANARY else 0,
            "last_rollback_reason": self.last_rollback_reason,
            "baseline_metadata": self.baseline_metadata.to_dict(),
            "candidate_metadata": self.candidate_metadata.to_dict() if self.candidate_metadata else None,
        }


# Global Release Manager Singleton
_GLOBAL_RELEASE_MANAGER = ModelReleaseManager()


def get_release_manager() -> ModelReleaseManager:
    return _GLOBAL_RELEASE_MANAGER
