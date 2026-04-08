class SavePolicyService:
    LONG_TERM_TAG_HINTS = {
        "playbook",
        "incident",
        "pattern",
        "policy",
        "preference",
        "approved",
        "knowledge",
        "timeout",
        "inventory",
        "root-cause",
        "fix",
        "strategy",
    }

    SHORT_TERM_HINTS = {
        "in_progress",
        "temporary",
        "current step",
        "working on",
        "debugging now",
        "right now",
        "current state",
        "session only",
    }

    GENERIC_SKIP_HINTS = {
        "ok",
        "done",
        "test",
        "hello",
        "thanks",
        "noted",
    }

    def _normalize_text(self, title: str, content: str) -> str:
        return f"{title} {content}".strip().lower()

    def _has_long_term_signal(self, text: str, tags: list[str], importance_score: float, memory_type: str | None) -> tuple[bool, list[str]]:
        reasons = []

        if importance_score >= 0.7:
            reasons.append("high importance score")

        if memory_type in {"semantic", "procedural", "episodic"}:
            reasons.append(f"useful long-term memory type: {memory_type}")

        if any(tag.lower() in self.LONG_TERM_TAG_HINTS for tag in tags):
            reasons.append("reusable knowledge tags detected")

        if len(text) >= 80:
            reasons.append("content is sufficiently informative")

        return (len(reasons) >= 2, reasons)

    def _has_short_term_signal(self, text: str, session_id: str | None, structured_payload: dict | None) -> tuple[bool, list[str]]:
        reasons = []

        if any(hint in text for hint in self.SHORT_TERM_HINTS):
            reasons.append("ephemeral or in-progress wording detected")

        if session_id:
            reasons.append("session-bound context detected")

        if structured_payload and isinstance(structured_payload, dict):
            state_keys = {"step", "status", "current_goal", "execution_state"}
            if any(key in structured_payload for key in state_keys):
                reasons.append("execution-state style payload detected")

        return (len(reasons) >= 1, reasons)

    def _has_skip_signal(self, text: str, title: str, content: str) -> tuple[bool, list[str]]:
        reasons = []

        if len(content.strip()) < 20:
            reasons.append("content too short")

        if len(title.strip()) < 4:
            reasons.append("title too short")

        if text.strip() in self.GENERIC_SKIP_HINTS:
            reasons.append("content too generic")

        generic_phrases = ["just testing", "test memory", "hello world", "temporary note"]
        if any(phrase in text for phrase in generic_phrases):
            reasons.append("test or placeholder content detected")

        return (len(reasons) >= 1, reasons)

    def decide(
        self,
        title: str,
        content: str,
        memory_type: str | None,
        scope: str | None,
        importance_score: float,
        confidence_score: float,
        tags: list[str],
        agent_id: str | None,
        tenant_id: str | None,
        session_id: str | None,
        structured_payload: dict | None,
    ) -> dict:
        text = self._normalize_text(title, content)

        skip_match, skip_reasons = self._has_skip_signal(text, title, content)
        if skip_match and importance_score < 0.6:
            return {
                "decision": "skip",
                "reasons": skip_reasons,
                "recommended_memory_type": None,
                "suggested_scope": None,
            }

        long_term_match, long_term_reasons = self._has_long_term_signal(
            text=text,
            tags=tags,
            importance_score=importance_score,
            memory_type=memory_type,
        )

        short_term_match, short_term_reasons = self._has_short_term_signal(
            text=text,
            session_id=session_id,
            structured_payload=structured_payload,
        )

        if long_term_match:
            recommended_type = memory_type or "semantic"
            suggested_scope = scope or ("shared" if tenant_id else "private")

            return {
                "decision": "save_long_term",
                "reasons": long_term_reasons,
                "recommended_memory_type": recommended_type,
                "suggested_scope": suggested_scope,
            }

        if short_term_match:
            return {
                "decision": "save_short_term_only",
                "reasons": short_term_reasons,
                "recommended_memory_type": None,
                "suggested_scope": None,
            }

        if confidence_score >= 0.8 and importance_score >= 0.6:
            return {
                "decision": "save_long_term",
                "reasons": [
                    "high confidence and moderate importance",
                ],
                "recommended_memory_type": memory_type or "semantic",
                "suggested_scope": scope or ("shared" if tenant_id else "private"),
            }

        return {
            "decision": "skip",
            "reasons": [
                "insufficient long-term signal",
                "not clearly useful for short-term memory only",
            ],
            "recommended_memory_type": None,
            "suggested_scope": None,
        }