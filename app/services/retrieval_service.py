from datetime import datetime, timezone

from app.schemas.memory import RetrievalWeights


class RetrievalService:
    def calculate_recency_score(self, created_at: datetime | None) -> float:
        if not created_at:
            return 0.5

        now = datetime.now(timezone.utc)

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age_hours = (now - created_at).total_seconds() / 3600

        if age_hours <= 24:
            return 1.0
        if age_hours <= 24 * 7:
            return 0.85
        if age_hours <= 24 * 30:
            return 0.65
        if age_hours <= 24 * 90:
            return 0.45

        return 0.25

    def calculate_feedback_score(self, feedback_summary: dict | None) -> float:
        if not feedback_summary:
            return 0.5

        total_feedback = feedback_summary.get("total_feedback", 0)
        counts = feedback_summary.get("counts", {})

        if total_feedback == 0:
            return 0.5

        useful = counts.get("useful", 0)
        partially_useful = counts.get("partially_useful", 0)
        not_useful = counts.get("not_useful", 0)

        raw_total = (useful * 1.0) + (partially_useful * 0.5) + (not_useful * -1.0)
        raw_average = raw_total / total_feedback

        normalized = (raw_average + 1.0) / 2.0
        return max(0.0, min(1.0, normalized))

    def calculate_contradiction_penalty(self, contradiction_count: int) -> float:
        if contradiction_count <= 0:
            return 0.0
        if contradiction_count == 1:
            return 0.10
        if contradiction_count == 2:
            return 0.20
        return 0.30

    def calculate_final_score(
        self,
        semantic_similarity: float,
        recency_score: float,
        confidence_score: float,
        importance_score: float,
        feedback_score: float,
        contradiction_penalty: float,
        weights: RetrievalWeights,
    ) -> float:
        score = (
            semantic_similarity * weights.semantic
            + recency_score * weights.recency
            + confidence_score * weights.confidence
            + importance_score * weights.importance
            + feedback_score * weights.feedback
        ) - contradiction_penalty

        return max(0.0, score)

    def build_context_summary(self, selected_items: list[dict]) -> str:
        if not selected_items:
            return "No relevant memory context found."

        lines = ["Relevant memory context retrieved for the agent:"]

        for idx, item in enumerate(selected_items, start=1):
            memory = item["memory"]
            lines.append(
                f"{idx}. [{memory.memory_type}] {memory.title} "
                f"(score={item['final_score']:.3f}, feedback={item['feedback_score']:.3f}, contradiction_penalty={item['contradiction_penalty']:.3f})"
            )

        return "\n".join(lines)

    def extract_facts(self, selected_items: list[dict]) -> list[str]:
        facts = []

        for item in selected_items:
            memory = item["memory"]
            if memory.memory_type == "semantic":
                facts.append(memory.summary or memory.content)

        return facts[:5]

    def extract_episodes(self, selected_items: list[dict]) -> list[str]:
        episodes = []

        for item in selected_items:
            memory = item["memory"]
            if memory.memory_type == "episodic":
                episodes.append(memory.summary or memory.content)

        return episodes[:5]

    def extract_procedures(self, selected_items: list[dict]) -> list[str]:
        procedures = []

        for item in selected_items:
            memory = item["memory"]
            if memory.memory_type == "procedural":
                procedures.append(memory.summary or memory.content)

        return procedures[:5]