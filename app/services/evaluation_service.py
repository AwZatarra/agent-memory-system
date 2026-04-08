import json
import os

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.memory import RetrievalWeights
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService


class EvaluationService:
    def __init__(self):
        self.dataset_file = settings.evaluation_dataset_file
        self.report_file = settings.evaluation_report_file

    def _read_dataset(self) -> list[dict]:
        if not os.path.exists(self.dataset_file):
            raise FileNotFoundError(
                f"Evaluation dataset file not found: {self.dataset_file}"
            )

        with open(self.dataset_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Evaluation dataset must be a JSON array")

        return data

    def _write_report(self, report: dict) -> None:
        os.makedirs(os.path.dirname(self.report_file), exist_ok=True)

        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def read_report(self) -> dict:
        if not os.path.exists(self.report_file):
            return {
                "status": "not_run",
                "total_queries": 0,
                "passed_queries": 0,
                "failed_queries": 0,
                "hit_at_k": 0.0,
                "hit_at_1": 0.0,
                "avg_top_score": 0.0,
                "results": [],
            }

        with open(self.report_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def run(self, db: Session) -> dict:
        dataset = self._read_dataset()
        memory_service = MemoryService(db)
        retrieval_service = RetrievalService()

        results: list[dict] = []
        hits_at_k = 0
        hits_at_1 = 0
        top_scores: list[float] = []

        for item in dataset:
            name = item["name"]
            agent_id = item["agent_id"]
            tenant_id = item.get("tenant_id")
            query = item["query"]
            top_k = item.get("top_k", 5)

            expected_titles = set(item.get("expected_titles", []))
            expected_memory_types = set(item.get("expected_memory_types", []))
            expect_no_relevant_results = item.get("expect_no_relevant_results", False)
            max_allowed_top_score = float(item.get("max_allowed_top_score", 0.60))

            weights = RetrievalWeights(
                **item.get(
                    "weights",
                    {
                        "semantic": 0.55,
                        "recency": 0.20,
                        "confidence": 0.15,
                        "importance": 0.10,
                    },
                )
            )

            candidates = memory_service.semantic_search_accessible_candidates(
                requesting_agent_id=agent_id,
                requesting_tenant_id=tenant_id,
                query_text=query,
                memory_type=item.get("memory_type"),
                user_id=item.get("user_id"),
                session_id=item.get("session_id"),
                tag=item.get("tag"),
                limit=top_k,
            )

            active_memory_ids = {str(memory.memory_id) for memory, _ in candidates}
            scored_items: list[dict] = []

            for memory, semantic_similarity in candidates:
                semantic_similarity = float(semantic_similarity)
                recency_score = retrieval_service.calculate_recency_score(
                    memory.created_at
                )
                confidence_score = float(memory.confidence_score)
                importance_score = float(memory.importance_score)

                feedback_summary = memory_service.get_feedback_summary(memory.memory_id)
                feedback_score = retrieval_service.calculate_feedback_score(feedback_summary)

                contradiction_count = memory_service.get_contradiction_count(
                    memory.memory_id,
                    active_memory_ids=active_memory_ids,
                )
                contradiction_penalty = retrieval_service.calculate_contradiction_penalty(
                    contradiction_count
                )

                final_score = retrieval_service.calculate_final_score(
                    semantic_similarity=semantic_similarity,
                    recency_score=recency_score,
                    confidence_score=confidence_score,
                    importance_score=importance_score,
                    feedback_score=feedback_score,
                    contradiction_penalty=contradiction_penalty,
                    weights=weights,
                )

                scored_items.append(
                    {
                        "memory_id": str(memory.memory_id),
                        "title": memory.title,
                        "memory_type": memory.memory_type,
                        "scope": memory.scope,
                        "tenant_id": memory.tenant_id,
                        "agent_id": memory.agent_id,
                        "semantic_similarity": semantic_similarity,
                        "recency_score": recency_score,
                        "confidence_score": confidence_score,
                        "importance_score": importance_score,
                        "feedback_score": feedback_score,
                        "contradiction_penalty": contradiction_penalty,
                        "final_score": final_score,
                    }
                )

            scored_items.sort(key=lambda x: x["final_score"], reverse=True)
            selected = scored_items[:top_k]

            returned_titles = [x["title"] for x in selected]
            returned_memory_types = [x["memory_type"] for x in selected]

            top_item = selected[0] if selected else None
            top_score = float(top_item["final_score"]) if top_item else 0.0

            top_scores.append(top_score)

            if expect_no_relevant_results:
                match_in_k = top_score <= max_allowed_top_score
                match_in_1 = top_score <= max_allowed_top_score
                evaluation_mode = "negative"
            else:
                match_in_k = (
                    any(title in expected_titles for title in returned_titles)
                    or any(mem_type in expected_memory_types for mem_type in returned_memory_types)
                )
                match_in_1 = False
                if top_item:
                    match_in_1 = (
                        top_item["title"] in expected_titles
                        or top_item["memory_type"] in expected_memory_types
                    )
                evaluation_mode = "positive"

            if match_in_k:
                hits_at_k += 1

            if match_in_1:
                hits_at_1 += 1

            results.append(
                {
                    "name": name,
                    "query": query,
                    "agent_id": agent_id,
                    "tenant_id": tenant_id,
                    "evaluation_mode": evaluation_mode,
                    "expected_titles": list(expected_titles),
                    "expected_memory_types": list(expected_memory_types),
                    "expect_no_relevant_results": expect_no_relevant_results,
                    "max_allowed_top_score": max_allowed_top_score if expect_no_relevant_results else None,
                    "returned_titles": returned_titles,
                    "returned_memory_types": returned_memory_types,
                    "top_score": top_score,
                    "hit_at_k": match_in_k,
                    "hit_at_1": match_in_1,
                    "selected": selected,
                }
            )

        total_queries = len(dataset)
        passed_queries = sum(1 for r in results if r["hit_at_k"])
        failed_queries = total_queries - passed_queries
        avg_top_score = sum(top_scores) / len(top_scores) if top_scores else 0.0

        report = {
            "status": "completed",
            "total_queries": total_queries,
            "passed_queries": passed_queries,
            "failed_queries": failed_queries,
            "hit_at_k": hits_at_k / total_queries if total_queries else 0.0,
            "hit_at_1": hits_at_1 / total_queries if total_queries else 0.0,
            "avg_top_score": avg_top_score,
            "results": results,
        }

        self._write_report(report)
        return report